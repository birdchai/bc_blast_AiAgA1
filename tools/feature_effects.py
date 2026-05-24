from __future__ import annotations

import glob
import os
import re
from pathlib import Path

import pandas as pd


POV_ID_COLUMNS = ["date", "address", "latitude", "longitude"]


def _point_biserial_corr(feature: pd.Series, target: pd.Series) -> float | None:
    corr = feature.corr(target)
    return float(corr) if pd.notna(corr) else None


def numeric_feature_effects(
    df: pd.DataFrame,
    target_col: str = "blast_any",
    feature_cols: list[str] | None = None,
) -> pd.DataFrame:
    """
    Estimate interpretable univariate associations against a binary target.

    This is not causal importance. It reports how each numeric feature differs
    between disease and non-disease weeks.
    """
    if target_col not in df.columns:
        raise ValueError(f"Missing target column: {target_col}")

    out = df.copy()
    out[target_col] = (pd.to_numeric(out[target_col], errors="coerce").fillna(0) > 0).astype(int)

    if feature_cols is None:
        ignored = {
            target_col,
            "blast_days",
            "observed_days",
            "predicted_positive",
            "actual_positive",
        }
        feature_cols = [
            col
            for col in out.select_dtypes(include="number").columns
            if col not in ignored
        ]

    rows = []
    for col in feature_cols:
        values = pd.to_numeric(out[col], errors="coerce")
        mask = values.notna() & out[target_col].notna()
        if not mask.any():
            continue

        target = out.loc[mask, target_col]
        values = values.loc[mask]
        disease = values[target == 1]
        no_disease = values[target == 0]

        rows.append(
            {
                "feature": col,
                "rows": int(mask.sum()),
                "disease_rows": int((target == 1).sum()),
                "mean_disease": float(disease.mean()) if len(disease) else None,
                "mean_no_disease": float(no_disease.mean()) if len(no_disease) else None,
                "effect_diff": (
                    float(disease.mean() - no_disease.mean())
                    if len(disease) and len(no_disease)
                    else None
                ),
                "effect_ratio": (
                    float(disease.mean() / no_disease.mean())
                    if len(disease) and len(no_disease) and no_disease.mean() != 0
                    else None
                ),
                "correlation": _point_biserial_corr(values, target),
            }
        )

    effects = pd.DataFrame(rows)
    if effects.empty:
        return effects

    effects["correlation"] = pd.to_numeric(effects["correlation"], errors="coerce")
    effects["abs_correlation"] = effects["correlation"].abs()
    return effects.sort_values(
        ["abs_correlation", "effect_diff"],
        ascending=[False, False],
        na_position="last",
    )


def _infer_pov_year(file_path: str) -> int | None:
    match = re.search(r"(20\d{2})", file_path)
    return int(match.group(1)) if match else None


def _infer_pov_season(file_path: str) -> str:
    normalized = file_path.replace("\\", "/").lower()
    if "offseason" in normalized or "pov-rice-off" in normalized:
        return "offseason"
    if "inseason" in normalized or "pov-rice-in" in normalized:
        return "inseason"
    return "unknown"


def load_pov_long(folder_path: str) -> pd.DataFrame:
    """Load rice POV CSV files into long variety-ratio format."""
    files = glob.glob(os.path.join(folder_path, "**", "*.csv"), recursive=True)

    dfs = []
    for file_path in files:
        try:
            df = pd.read_csv(file_path, encoding="cp874", low_memory=False)
            missing = [col for col in POV_ID_COLUMNS if col not in df.columns]
            if missing:
                raise ValueError(f"Missing required POV columns: {missing}")

            value_cols = [col for col in df.columns if col not in POV_ID_COLUMNS]
            long = df.melt(
                id_vars=POV_ID_COLUMNS,
                value_vars=value_cols,
                var_name="variety",
                value_name="area",
            )
            long["area"] = pd.to_numeric(long["area"], errors="coerce").fillna(0)
            long = long[long["area"] > 0].copy()
            if long.empty:
                continue

            total = long.groupby(["date", "address"])["area"].transform("sum")
            long["ratio"] = long["area"] / total
            long = long.rename(columns={"date": "datetime", "address": "province"})
            long["datetime"] = pd.to_datetime(long["datetime"], errors="coerce")
            long["year"] = _infer_pov_year(file_path)
            long["season"] = _infer_pov_season(file_path)
            long["source_file"] = os.path.basename(file_path)
            long = long.dropna(subset=["province", "datetime", "variety"])
            dfs.append(long[["province", "datetime", "year", "season", "variety", "area", "ratio", "source_file"]])
        except Exception as exc:
            print(f"Failed to read {file_path}: {exc}")

    if not dfs:
        raise ValueError("No POV CSV files could be loaded.")

    return pd.concat(dfs, ignore_index=True)


def pov_to_weekly_variety_ratio(df_long: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily variety ratios into province-week-variety features."""
    required = ["province", "datetime", "season", "variety", "area", "ratio"]
    missing = [col for col in required if col not in df_long.columns]
    if missing:
        raise ValueError(f"Missing required POV long columns: {missing}")

    out = df_long.copy()
    out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce")
    out["area"] = pd.to_numeric(out["area"], errors="coerce").fillna(0)
    out["ratio"] = pd.to_numeric(out["ratio"], errors="coerce").fillna(0)
    out = out.dropna(subset=["province", "datetime", "season", "variety"])
    out = out.set_index("datetime")

    weekly = (
        out.groupby(["province", "season", "variety"])
        .resample("W")
        .agg({"area": "mean", "ratio": "mean"})
        .reset_index()
    )
    weekly = weekly.rename(columns={"area": "variety_area_mean", "ratio": "variety_ratio_mean"})

    return weekly


def variety_effects(
    weekly_pov: pd.DataFrame,
    weekly_blast: pd.DataFrame,
    min_presence_weeks: int = 20,
) -> pd.DataFrame:
    """Estimate variety-level association with weekly blast occurrence."""
    blast = weekly_blast[["province", "datetime", "blast_any"]].copy()
    joined = weekly_pov.merge(blast, on=["province", "datetime"], how="inner")
    if joined.empty:
        raise ValueError("POV/blast joined dataset is empty.")

    rows = []
    for (season, variety), group in joined.groupby(["season", "variety"]):
        present = group[group["variety_ratio_mean"] > 0].copy()
        if len(present) < min_presence_weeks:
            continue

        target = (present["blast_any"] > 0).astype(int)
        ratio = pd.to_numeric(present["variety_ratio_mean"], errors="coerce")
        disease = ratio[target == 1]
        no_disease = ratio[target == 0]

        rows.append(
            {
                "season": season,
                "variety": variety,
                "presence_weeks": int(len(present)),
                "disease_weeks": int(target.sum()),
                "mean_ratio_disease": float(disease.mean()) if len(disease) else None,
                "mean_ratio_no_disease": float(no_disease.mean()) if len(no_disease) else None,
                "effect_diff": (
                    float(disease.mean() - no_disease.mean())
                    if len(disease) and len(no_disease)
                    else None
                ),
                "correlation": _point_biserial_corr(ratio, target),
            }
        )

    effects = pd.DataFrame(rows)
    if effects.empty:
        return effects

    effects["correlation"] = pd.to_numeric(effects["correlation"], errors="coerce")
    effects["abs_correlation"] = effects["correlation"].abs()
    return effects.sort_values(
        ["abs_correlation", "effect_diff"],
        ascending=[False, False],
        na_position="last",
    )


def summarize_effect_stability(
    effects: pd.DataFrame,
    group_cols: list[str],
    effect_col: str = "effect_diff",
    correlation_col: str = "correlation",
) -> pd.DataFrame:
    """Summarize whether feature-effect direction is stable across years."""
    required = ["year", effect_col, correlation_col] + group_cols
    missing = [col for col in required if col not in effects.columns]
    if missing:
        raise ValueError(f"Missing required stability columns: {missing}")

    rows = []
    for keys, group in effects.groupby(group_cols):
        if not isinstance(keys, tuple):
            keys = (keys,)

        usable = group.dropna(subset=[effect_col])
        years_observed = int(usable["year"].nunique())
        positive_years = int((usable[effect_col] > 0).sum())
        negative_years = int((usable[effect_col] < 0).sum())
        zero_years = int((usable[effect_col] == 0).sum())

        stable_positive_share = positive_years / years_observed if years_observed else 0.0
        stable_negative_share = negative_years / years_observed if years_observed else 0.0

        row = {
            col: value for col, value in zip(group_cols, keys)
        }
        row.update(
            {
                "years_observed": years_observed,
                "positive_years": positive_years,
                "negative_years": negative_years,
                "zero_years": zero_years,
                "stable_positive_share": stable_positive_share,
                "stable_negative_share": stable_negative_share,
                "mean_effect_diff": float(usable[effect_col].mean()) if len(usable) else None,
                "median_effect_diff": float(usable[effect_col].median()) if len(usable) else None,
                "mean_correlation": (
                    float(usable[correlation_col].mean())
                    if usable[correlation_col].notna().any()
                    else None
                ),
                "mean_abs_correlation": (
                    float(usable[correlation_col].abs().mean())
                    if usable[correlation_col].notna().any()
                    else None
                ),
            }
        )
        rows.append(row)

    stability = pd.DataFrame(rows)
    if stability.empty:
        return stability

    stability["direction_stability"] = stability[
        ["stable_positive_share", "stable_negative_share"]
    ].max(axis=1)

    return stability.sort_values(
        ["direction_stability", "mean_abs_correlation", "years_observed"],
        ascending=[False, False, False],
        na_position="last",
    )
