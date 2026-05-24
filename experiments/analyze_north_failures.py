from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from experiments.analyze_province_similarity import (  # noqa: E402
    OUTPUT_DIR,
    TRAIN_YEARS,
    build_analog_features,
    prepare_dataset,
)


DATASET_PATH = OUTPUT_DIR / "region_temporal_sequence_dataset_updated_labels_2015_2022.csv"
ANALOG_PREDICTIONS_PATH = OUTPUT_DIR / "analog_ablation_test_predictions.csv"
TEMPORAL_PREDICTIONS_PATH = OUTPUT_DIR / "temporal_model_forward_predictions.csv"
TOP_ANALOGS_PATH = OUTPUT_DIR / "province_top_analog_neighbors.csv"
TERRAIN_TEMPLATE_PATH = OUTPUT_DIR / "province_terrain_table_template.csv"

TEST_YEAR = 2022
VALIDATION_YEAR = 2021
TARGET = "blast_t_plus_1"

WEATHER_FEATURES = [
    "humidity_mean",
    "temperature_mean",
    "rainfall_sum",
    "leaf_wet_hours",
    "leaf_wet_ratio",
    "risk_score",
    "rolling_2w_risk",
    "rolling_3w_risk",
    "rolling_2w_leaf_wet_hours",
    "rolling_3w_leaf_wet_hours",
    "spore_window_leaf_wet_hours",
]

HOST_FEATURES = [
    "susceptibility_score",
    "host_weighted_risk",
    "host_weighted_rolling_2w",
    "host_weighted_rolling_3w",
    "total_pov_area",
    "pov_variety_count",
]

SPATIAL_FEATURES = [
    "neighbor_prevweek_blast",
    "neighbor_prevweek_risk",
    "regional_neighbor_pressure_2w",
    "regional_neighbor_pressure_3w",
    "regional_host_pressure",
    "regional_wind_alignment_frequency",
    "wind_aligned_neighbor_blast",
]

ANALOG_FEATURES = [
    "analog_prevweek_blast",
    "analog_outbreak_frequency_train",
    "analog_prevweek_risk",
    "analog_2w_pressure",
    "analog_leaf_wet_pressure",
    "analog_regional_leaf_wet_pressure",
    "analog_host_pressure",
]

MODEL_SCORE_COLUMNS = [
    "score_dnn_core",
    "score_dnn_analog_history",
    "score_rf_all_analog",
    "score_rf_analog_history",
    "score_hybrid_tcn_2w",
]


def existing(df: pd.DataFrame, columns: list[str]) -> list[str]:
    return [col for col in columns if col in df.columns]


def load_augmented_dataset() -> pd.DataFrame:
    df = prepare_dataset()
    df["month"] = pd.to_datetime(df["datetime"], errors="coerce").dt.month
    top = pd.read_csv(TOP_ANALOGS_PATH)
    train = df[df["year"].isin(TRAIN_YEARS)].copy()
    analog = build_analog_features(df, top, train)
    analog_cols = ["province", "datetime", "year", "week"] + ANALOG_FEATURES
    out = df.merge(
        analog[existing(analog, analog_cols)],
        on=["province", "datetime", "year", "week"],
        how="left",
    )
    for col in WEATHER_FEATURES + HOST_FEATURES + SPATIAL_FEATURES + ANALOG_FEATURES + [TARGET]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def load_model_scores() -> pd.DataFrame:
    frames = []
    analog = pd.read_csv(ANALOG_PREDICTIONS_PATH, low_memory=False)
    analog["datetime"] = pd.to_datetime(analog["datetime"], errors="coerce")

    candidates = {
        ("dnn_no_class_weight", "core_no_BUS"): ("score_dnn_core", "pred_dnn_core"),
        ("dnn_no_class_weight", "core_plus_analog_history"): (
            "score_dnn_analog_history",
            "pred_dnn_analog_history",
        ),
        ("random_forest", "core_plus_all_analog"): ("score_rf_all_analog", "pred_rf_all_analog"),
        ("random_forest", "core_plus_analog_history"): (
            "score_rf_analog_history",
            "pred_rf_analog_history",
        ),
    }
    for (model, feature_set), (score_col, pred_col) in candidates.items():
        subset = analog[(analog["model"] == model) & (analog["feature_set"] == feature_set)].copy()
        subset = subset.rename(columns={"y_score": score_col, "y_pred": pred_col})
        frames.append(
            subset[
                [
                    "province",
                    "datetime",
                    "year",
                    "week",
                    score_col,
                    pred_col,
                ]
            ]
        )

    merged = None
    for frame in frames:
        merged = frame if merged is None else merged.merge(
            frame, on=["province", "datetime", "year", "week"], how="outer"
        )

    if TEMPORAL_PREDICTIONS_PATH.exists():
        temporal = pd.read_csv(TEMPORAL_PREDICTIONS_PATH, low_memory=False)
        temporal = temporal[
            (temporal["model"] == "hybrid_dnn_tcn")
            & (pd.to_numeric(temporal["sequence_length"], errors="coerce") == 2)
            & (temporal["split"] == "test")
        ].copy()
        temporal["datetime"] = pd.to_datetime(temporal["end_datetime"], errors="coerce")
        temporal["week"] = temporal["end_week"]
        temporal = temporal.rename(
            columns={"y_score": "score_hybrid_tcn_2w", "y_pred": "pred_hybrid_tcn_2w"}
        )
        merged = merged.merge(
            temporal[
                [
                    "province",
                    "datetime",
                    "year",
                    "week",
                    "score_hybrid_tcn_2w",
                    "pred_hybrid_tcn_2w",
                ]
            ],
            on=["province", "datetime", "year", "week"],
            how="left",
        )

    return merged


def north_positive_case_table(df: pd.DataFrame) -> pd.DataFrame:
    scores = load_model_scores()
    test = df[(df["year"] == TEST_YEAR) & (df["region"] == "North")].copy()
    positives = test[pd.to_numeric(test[TARGET], errors="coerce") == 1].copy()
    out = positives.merge(scores, on=["province", "datetime", "year", "week"], how="left")

    pred_cols = [col for col in out.columns if col.startswith("pred_")]
    for col in pred_cols:
        out[f"missed_by_{col.replace('pred_', '')}"] = pd.to_numeric(out[col], errors="coerce").fillna(0).astype(int) == 0
    out["missed_by_all_available_models"] = out[[col for col in out.columns if col.startswith("missed_by_")]].all(axis=1)

    feature_cols = existing(out, WEATHER_FEATURES + HOST_FEATURES + SPATIAL_FEATURES + ANALOG_FEATURES)
    score_cols = existing(out, MODEL_SCORE_COLUMNS)
    keep = [
        "province",
        "datetime",
        "year",
        "week",
        "month",
        TARGET,
        "label_observed",
    ] + score_cols + pred_cols + [col for col in out.columns if col.startswith("missed_by_")] + feature_cols
    return out[keep].sort_values(["province", "datetime"])


def feature_summary(df: pd.DataFrame, region: str) -> pd.DataFrame:
    test = df[(df["year"] == TEST_YEAR) & (df["region"] == region)].copy()
    y = pd.to_numeric(test[TARGET], errors="coerce")
    rows = []
    for group_name, features in [
        ("weather_moisture", WEATHER_FEATURES),
        ("host_pov", HOST_FEATURES),
        ("spatial_regional", SPATIAL_FEATURES),
        ("analog", ANALOG_FEATURES),
    ]:
        for feature in existing(test, features):
            values = pd.to_numeric(test[feature], errors="coerce")
            pos = values[y == 1]
            neg = values[y == 0]
            rows.append(
                {
                    "region": region,
                    "feature_group": group_name,
                    "feature": feature,
                    "positive_rows": int((y == 1).sum()),
                    "negative_rows": int((y == 0).sum()),
                    "positive_mean": pos.mean(),
                    "negative_mean": neg.mean(),
                    "effect_diff": pos.mean() - neg.mean(),
                    "effect_ratio": safe_ratio(pos.mean(), neg.mean()),
                    "positive_median": pos.median(),
                    "negative_median": neg.median(),
                    "coverage_rate": values.notna().mean(),
                }
            )
    return pd.DataFrame(rows)


def north_vs_northeast_positive_comparison(df: pd.DataFrame) -> pd.DataFrame:
    test_pos = df[(df["year"] == TEST_YEAR) & (pd.to_numeric(df[TARGET], errors="coerce") == 1)].copy()
    rows = []
    for group_name, features in [
        ("weather_moisture", WEATHER_FEATURES),
        ("host_pov", HOST_FEATURES),
        ("spatial_regional", SPATIAL_FEATURES),
        ("analog", ANALOG_FEATURES),
    ]:
        for feature in existing(test_pos, features):
            north = pd.to_numeric(test_pos.loc[test_pos["region"] == "North", feature], errors="coerce")
            ne = pd.to_numeric(test_pos.loc[test_pos["region"] == "Northeast", feature], errors="coerce")
            rows.append(
                {
                    "feature_group": group_name,
                    "feature": feature,
                    "north_positive_mean": north.mean(),
                    "northeast_positive_mean": ne.mean(),
                    "north_minus_northeast": north.mean() - ne.mean(),
                    "north_positive_median": north.median(),
                    "northeast_positive_median": ne.median(),
                    "north_positive_rows": int(north.notna().sum()),
                    "northeast_positive_rows": int(ne.notna().sum()),
                }
            )
    return pd.DataFrame(rows)


def seasonality_diagnostic(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    scopes = [
        ("test_2022_north", df[(df["year"] == TEST_YEAR) & (df["region"] == "North")]),
        ("test_2022_northeast", df[(df["year"] == TEST_YEAR) & (df["region"] == "Northeast")]),
        ("train_2017_2020_north", df[df["year"].isin(TRAIN_YEARS) & (df["region"] == "North")]),
        ("train_2017_2020_northeast", df[df["year"].isin(TRAIN_YEARS) & (df["region"] == "Northeast")]),
    ]
    for scope, subset in scopes:
        y = pd.to_numeric(subset[TARGET], errors="coerce")
        for month, group in subset.groupby("month"):
            gy = pd.to_numeric(group[TARGET], errors="coerce")
            rows.append(
                {
                    "scope": scope,
                    "time_unit": "month",
                    "time_value": int(month) if pd.notna(month) else None,
                    "rows": len(group),
                    "positive_rows": int((gy == 1).sum()),
                    "positive_rate": float((gy == 1).mean()) if len(group) else None,
                    "share_of_scope_positives": safe_ratio(int((gy == 1).sum()), int((y == 1).sum())),
                }
            )
        subset = subset.copy()
        subset["week_bin"] = pd.cut(
            pd.to_numeric(subset["week"], errors="coerce"),
            bins=[0, 13, 26, 39, 54],
            labels=["w01_13", "w14_26", "w27_39", "w40_53"],
            include_lowest=True,
        )
        for week_bin, group in subset.groupby("week_bin", observed=False):
            gy = pd.to_numeric(group[TARGET], errors="coerce")
            rows.append(
                {
                    "scope": scope,
                    "time_unit": "week_bin",
                    "time_value": str(week_bin),
                    "rows": len(group),
                    "positive_rows": int((gy == 1).sum()),
                    "positive_rate": float((gy == 1).mean()) if len(group) else None,
                    "share_of_scope_positives": safe_ratio(int((gy == 1).sum()), int((y == 1).sum())),
                }
            )
    return pd.DataFrame(rows)


def province_failure_summary(df: pd.DataFrame, positive_cases: pd.DataFrame) -> pd.DataFrame:
    train = df[df["year"].isin(TRAIN_YEARS)].copy()
    train_freq = (
        train.groupby("province")
        .agg(
            train_rows=(TARGET, "size"),
            train_positive_rows=(TARGET, lambda s: int((pd.to_numeric(s, errors="coerce") == 1).sum())),
            train_positive_rate=(TARGET, lambda s: float((pd.to_numeric(s, errors="coerce") == 1).mean())),
            train_label_observed_rate=("label_observed", lambda s: float(pd.to_numeric(s, errors="coerce").fillna(0).mean())),
        )
        .reset_index()
    )
    test_north = df[(df["year"] == TEST_YEAR) & (df["region"] == "North")].copy()
    test_summary = (
        test_north.groupby("province")
        .agg(
            test_rows=(TARGET, "size"),
            test_positive_rows=(TARGET, lambda s: int((pd.to_numeric(s, errors="coerce") == 1).sum())),
            test_positive_rate=(TARGET, lambda s: float((pd.to_numeric(s, errors="coerce") == 1).mean())),
            test_label_observed_rate=("label_observed", lambda s: float(pd.to_numeric(s, errors="coerce").fillna(0).mean())),
        )
        .reset_index()
    )
    miss_cols = [col for col in positive_cases.columns if col.startswith("missed_by_")]
    case_counts = positive_cases.groupby("province").agg(north_positive_cases=("province", "size")).reset_index()
    if miss_cols:
        missed = (
            positive_cases.groupby("province")[miss_cols]
            .sum()
            .reset_index()
        )
        case_counts = case_counts.merge(missed, on="province", how="left")

    top = pd.read_csv(TOP_ANALOGS_PATH)
    analog_names = (
        top[top["analog_rank"] <= 5]
        .groupby("province")["analog_province"]
        .apply(lambda values: "|".join(values.tolist()))
        .rename("top5_analog_provinces")
        .reset_index()
    )
    return (
        test_summary.merge(train_freq, on="province", how="left")
        .merge(case_counts, on="province", how="left")
        .merge(analog_names, on="province", how="left")
        .fillna({"north_positive_cases": 0})
        .sort_values(["test_positive_rows", "province"], ascending=[False, True])
    )


def analog_failure_diagnostic(positive_cases: pd.DataFrame) -> pd.DataFrame:
    top = pd.read_csv(TOP_ANALOGS_PATH)
    analog_names = (
        top[top["analog_rank"] <= 5]
        .groupby("province")
        .agg(
            top5_analog_provinces=("analog_province", lambda values: "|".join(values.tolist())),
            same_region_rate=("same_region", "mean"),
            mean_analog_distance_km=("distance_km", "mean"),
        )
        .reset_index()
    )
    cols = [
        "province",
        "datetime",
        "week",
        "month",
        "analog_prevweek_blast",
        "analog_outbreak_frequency_train",
        "analog_prevweek_risk",
        "analog_2w_pressure",
        "analog_leaf_wet_pressure",
        "analog_host_pressure",
        "neighbor_prevweek_blast",
        "neighbor_prevweek_risk",
        "regional_neighbor_pressure_2w",
        "regional_neighbor_pressure_3w",
    ]
    return positive_cases[existing(positive_cases, cols)].merge(analog_names, on="province", how="left")


def label_observation_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scope, subset in [
        ("train_2017_2020_north", df[df["year"].isin(TRAIN_YEARS) & (df["region"] == "North")]),
        ("train_2017_2020_northeast", df[df["year"].isin(TRAIN_YEARS) & (df["region"] == "Northeast")]),
        ("validation_2021_north", df[(df["year"] == VALIDATION_YEAR) & (df["region"] == "North")]),
        ("test_2022_north", df[(df["year"] == TEST_YEAR) & (df["region"] == "North")]),
        ("test_2022_northeast", df[(df["year"] == TEST_YEAR) & (df["region"] == "Northeast")]),
    ]:
        label = pd.to_numeric(subset.get("label_observed"), errors="coerce").fillna(0)
        y = pd.to_numeric(subset[TARGET], errors="coerce")
        rows.append(
            {
                "scope": scope,
                "rows": len(subset),
                "label_observed_rows": int(label.sum()),
                "label_observed_rate": float(label.mean()) if len(label) else None,
                "positive_rows": int((y == 1).sum()),
                "positive_rate": float((y == 1).mean()) if len(y) else None,
                "provinces": int(subset["province"].nunique()),
            }
        )
    return pd.DataFrame(rows)


def classify_failure(row: pd.Series, thresholds: dict[str, float]) -> list[str]:
    labels = []
    if row.get("risk_score", np.nan) < thresholds["risk_score_q25"]:
        labels.append("low weather-risk signal")
    if row.get("host_weighted_risk", np.nan) < thresholds["host_weighted_risk_q25"]:
        labels.append("low host susceptibility/risk signal")
    if row.get("neighbor_prevweek_blast", 0) <= 0 and row.get("analog_prevweek_blast", 0) <= 0:
        labels.append("no neighbor/analog outbreak signal")
    if row.get("analog_outbreak_frequency_train", np.nan) < thresholds["analog_outbreak_frequency_train_q25"]:
        labels.append("sparse historical analog outbreak pattern")
    if row.get("month", np.nan) not in thresholds["train_north_positive_months"]:
        labels.append("seasonality mismatch")
    if row.get("label_observed", 0) == 0:
        labels.append("unobserved label context")
    labels.append("possible terrain/microclimate missing feature")
    return labels


def failure_type_summary(df: pd.DataFrame, positive_cases: pd.DataFrame) -> pd.DataFrame:
    train_north_positive_months = set(
        df[
            df["year"].isin(TRAIN_YEARS)
            & (df["region"] == "North")
            & (pd.to_numeric(df[TARGET], errors="coerce") == 1)
        ]["month"]
        .dropna()
        .astype(int)
        .tolist()
    )
    north_test = df[(df["year"] == TEST_YEAR) & (df["region"] == "North")].copy()
    thresholds = {
        "risk_score_q25": pd.to_numeric(north_test["risk_score"], errors="coerce").quantile(0.25),
        "host_weighted_risk_q25": pd.to_numeric(north_test["host_weighted_risk"], errors="coerce").quantile(0.25),
        "analog_outbreak_frequency_train_q25": pd.to_numeric(
            north_test["analog_outbreak_frequency_train"], errors="coerce"
        ).quantile(0.25),
        "train_north_positive_months": train_north_positive_months,
    }
    rows = []
    for _, row in positive_cases.iterrows():
        for failure_type in classify_failure(row, thresholds):
            rows.append(
                {
                    "province": row["province"],
                    "datetime": row["datetime"],
                    "week": row["week"],
                    "failure_type": failure_type,
                }
            )
    detail = pd.DataFrame(rows)
    summary = (
        detail.groupby("failure_type")
        .agg(cases=("failure_type", "size"), provinces=("province", "nunique"))
        .reset_index()
        .sort_values("cases", ascending=False)
    )
    return summary


def recommendations(
    positive_cases: pd.DataFrame,
    feature_summary_df: pd.DataFrame,
    label_summary: pd.DataFrame,
    failure_summary: pd.DataFrame,
) -> pd.DataFrame:
    terrain_ready = TERRAIN_TEMPLATE_PATH.exists()
    return pd.DataFrame(
        [
            {
                "recommendation": "Add external terrain/elevation table before terrain modeling.",
                "rationale": "Weather source audit found no direct elevation/terrain field and sea-level pressure is not a terrain proxy.",
                "priority": "high",
                "ready_now": terrain_ready,
            },
            {
                "recommendation": "Do not treat analog history as a North solution.",
                "rationale": "North positives remain missed and analog previous-week blast is often absent.",
                "priority": "high",
                "ready_now": True,
            },
            {
                "recommendation": "Investigate North sub-regional seasonality and reporting density.",
                "rationale": "North 2022 positives may occur outside patterns learned from sparse train-year North positives.",
                "priority": "high",
                "ready_now": True,
            },
            {
                "recommendation": "Keep Northeast analog-history mode separate from North diagnostics.",
                "rationale": "Analog history helps Northeast but does not transfer to North.",
                "priority": "medium",
                "ready_now": True,
            },
            {
                "recommendation": "Acquire province terrain table with elevation_mean/min/max/range/std and terrain_roughness.",
                "rationale": "North failures plausibly involve microclimate/terrain not represented in current features.",
                "priority": "high",
                "ready_now": False,
            },
        ]
    )


def safe_ratio(a: float, b: float) -> float:
    if pd.isna(a) or pd.isna(b) or abs(b) < 1e-12:
        return np.nan
    return a / b


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    df = load_augmented_dataset()
    scores = load_model_scores()
    df_with_scores = df.merge(scores, on=["province", "datetime", "year", "week"], how="left")

    positive_cases = north_positive_case_table(df)
    north_summary = feature_summary(df, "North")
    northeast_summary = feature_summary(df, "Northeast")
    pos_compare = north_vs_northeast_positive_comparison(df_with_scores)
    seasonality = seasonality_diagnostic(df)
    province_summary = province_failure_summary(df_with_scores, positive_cases)
    analog_diag = analog_failure_diagnostic(positive_cases)
    label_summary = label_observation_summary(df)
    failure_types = failure_type_summary(df, positive_cases)
    reco = recommendations(positive_cases, north_summary, label_summary, failure_types)

    outputs = {
        "north_positive_case_table.csv": positive_cases,
        "north_positive_vs_negative_feature_summary.csv": north_summary,
        "north_vs_northeast_positive_comparison.csv": pos_compare,
        "north_seasonality_diagnostic.csv": seasonality,
        "north_province_failure_summary.csv": province_summary,
        "north_analog_failure_diagnostic.csv": analog_diag,
        "north_label_observation_summary.csv": label_summary,
        "north_failure_type_summary.csv": failure_types,
        "north_diagnostic_recommendations.csv": reco,
    }
    for filename, out in outputs.items():
        out.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 240)
    pd.set_option("display.max_columns", 80)
    print("\n=== NORTH POSITIVE CASES ===")
    print(positive_cases[["province", "datetime", "week", "score_dnn_core", "score_dnn_analog_history", "score_rf_all_analog", "score_hybrid_tcn_2w", "missed_by_all_available_models"]].to_string(index=False))
    print("\n=== NORTH FEATURE SUMMARY TOP DIFFS ===")
    print(north_summary.sort_values("effect_diff", ascending=False).head(20).to_string(index=False))
    print("\n=== NORTH VS NORTHEAST POSITIVE COMPARISON ===")
    print(pos_compare.sort_values("north_minus_northeast").head(15).to_string(index=False))
    print("\n=== LABEL OBSERVATION SUMMARY ===")
    print(label_summary.to_string(index=False))
    print("\n=== FAILURE TYPES ===")
    print(failure_types.to_string(index=False))
    print("\n=== OUTPUT FILES ===")
    for filename in outputs:
        print(OUTPUT_DIR / filename)


if __name__ == "__main__":
    main()
