from __future__ import annotations

import pandas as pd


def add_future_blast_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Add province-level future weekly blast labels."""
    required = ["province", "datetime", "blast_any"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing future-label columns: {missing}")

    out = df.copy().sort_values(["province", "datetime"])
    out["blast_t_plus_1"] = out.groupby("province")["blast_any"].shift(-1)
    out["blast_t_plus_2"] = out.groupby("province")["blast_any"].shift(-2)
    return out


def add_region_aware_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create explainable region-aware temporal epidemiology features."""
    required = [
        "region",
        "datetime",
        "neighbor_prevweek_blast",
        "leaf_wet_hours",
        "susceptibility_score",
        "wind_aligned_neighbor_blast",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing region-aware feature columns: {missing}")

    out = df.copy()
    out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce")

    regional_week = (
        out.groupby(["region", "datetime"])
        .agg(
            regional_neighbor_pressure=("neighbor_prevweek_blast", "mean"),
            regional_leaf_wet_mean=("leaf_wet_hours", "mean"),
            regional_host_pressure=("susceptibility_score", "mean"),
            regional_wind_alignment_frequency=("wind_aligned_neighbor_blast", "mean"),
        )
        .reset_index()
        .sort_values(["region", "datetime"])
    )

    grouped = regional_week.groupby("region", group_keys=False)
    regional_week["regional_neighbor_pressure_2w"] = grouped[
        "regional_neighbor_pressure"
    ].transform(lambda s: s.rolling(2, min_periods=1).mean())
    regional_week["regional_neighbor_pressure_3w"] = grouped[
        "regional_neighbor_pressure"
    ].transform(lambda s: s.rolling(3, min_periods=1).mean())
    regional_week["regional_leaf_wet_accumulation"] = grouped[
        "regional_leaf_wet_mean"
    ].transform(lambda s: s.rolling(3, min_periods=1).sum())

    out = out.merge(
        regional_week[
            [
                "region",
                "datetime",
                "regional_neighbor_pressure_2w",
                "regional_neighbor_pressure_3w",
                "regional_leaf_wet_accumulation",
                "regional_host_pressure",
                "regional_wind_alignment_frequency",
            ]
        ],
        on=["region", "datetime"],
        how="left",
    )

    return out


def add_week_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Add year and ISO week columns for sequence-ready exports."""
    out = df.copy()
    out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce")
    iso = out["datetime"].dt.isocalendar()
    out["year"] = iso["year"].astype("Int64")
    out["week"] = iso["week"].astype("Int64")
    return out


def sequence_feature_effects(
    df: pd.DataFrame,
    feature_cols: list[str],
    target_cols: list[str],
) -> pd.DataFrame:
    """Compute simple correlation of sequence features against future labels."""
    rows = []
    for target_col in target_cols:
        if target_col not in df.columns:
            continue
        target = pd.to_numeric(df[target_col], errors="coerce")
        for feature_col in feature_cols:
            if feature_col not in df.columns:
                continue
            feature = pd.to_numeric(df[feature_col], errors="coerce")
            mask = feature.notna() & target.notna()
            if not mask.any():
                continue

            disease = feature[mask & (target == 1)]
            no_disease = feature[mask & (target == 0)]
            corr = feature[mask].corr(target[mask])
            rows.append(
                {
                    "target": target_col,
                    "feature": feature_col,
                    "rows": int(mask.sum()),
                    "positive_rows": int((target[mask] == 1).sum()),
                    "mean_future_disease": float(disease.mean()) if len(disease) else None,
                    "mean_future_no_disease": float(no_disease.mean()) if len(no_disease) else None,
                    "effect_diff": (
                        float(disease.mean() - no_disease.mean())
                        if len(disease) and len(no_disease)
                        else None
                    ),
                    "correlation": float(corr) if pd.notna(corr) else None,
                }
            )

    effects = pd.DataFrame(rows)
    if effects.empty:
        return effects
    effects["correlation"] = pd.to_numeric(effects["correlation"], errors="coerce")
    effects["abs_correlation"] = effects["correlation"].abs()
    return effects.sort_values(["target", "abs_correlation"], ascending=[True, False])


def temporal_consistency_summary(
    effects: pd.DataFrame,
    group_cols: list[str],
) -> pd.DataFrame:
    """Summarize sign consistency of future-label associations across years/regions."""
    required = ["year", "effect_diff"] + group_cols
    missing = [col for col in required if col not in effects.columns]
    if missing:
        raise ValueError(f"Missing temporal consistency columns: {missing}")

    rows = []
    for keys, group in effects.groupby(group_cols):
        if not isinstance(keys, tuple):
            keys = (keys,)
        usable = group.dropna(subset=["effect_diff"])
        years_observed = int(usable["year"].nunique())
        positive_years = int((usable["effect_diff"] > 0).sum())
        negative_years = int((usable["effect_diff"] < 0).sum())

        row = {col: value for col, value in zip(group_cols, keys)}
        row.update(
            {
                "years_observed": years_observed,
                "positive_years": positive_years,
                "negative_years": negative_years,
                "direction_stability": (
                    max(positive_years, negative_years) / years_observed
                    if years_observed
                    else 0.0
                ),
                "mean_effect_diff": float(usable["effect_diff"].mean()) if len(usable) else None,
                "mean_correlation": (
                    float(usable["correlation"].mean())
                    if usable["correlation"].notna().any()
                    else None
                ),
                "mean_abs_correlation": (
                    float(usable["correlation"].abs().mean())
                    if usable["correlation"].notna().any()
                    else None
                ),
            }
        )
        rows.append(row)

    summary = pd.DataFrame(rows)
    if summary.empty:
        return summary
    return summary.sort_values(
        ["target", "direction_stability", "mean_abs_correlation"],
        ascending=[True, False, False],
        na_position="last",
    )
