from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

DATASET_PATH = BASE_DIR / "experiments" / "outputs" / "region_temporal_sequence_dataset_updated_labels_2015_2021.csv"
OUTPUT_DIR = BASE_DIR / "experiments" / "outputs"
TARGET = "blast_t_plus_1"
BUS_THRESHOLD = 2.25

BUS_FEATURES = [
    "avgbus_mean",
    "avgbus_max",
    "maxbus_max",
    "bus_critical_days",
    "bus_critical_any",
    "bus_critical_ratio",
]

CORE_FEATURES = [
    "temperature_mean",
    "humidity_mean",
    "rainfall_sum",
    "leaf_wet_hours",
    "leaf_wet_ratio",
    "rolling_2w_leaf_wet_hours",
    "rolling_3w_leaf_wet_hours",
    "risk_score",
    "rolling_2w_risk",
    "rolling_3w_risk",
    "susceptibility_score",
    "host_weighted_risk",
    "host_weighted_rolling_2w",
    "host_weighted_rolling_3w",
    "neighbor_prevweek_risk",
    "neighbor_prevweek_blast",
    "spatial_host_weather_risk",
    "prevailing_wind_direction",
    "wind_direction_variability",
    "mean_wind_speed",
    "humid_wind_hours",
    "leaf_wet_wind_hours",
    "wind_aligned_neighbor_blast",
    "wind_aligned_neighbor_count",
    "regional_neighbor_pressure_2w",
    "regional_neighbor_pressure_3w",
    "regional_leaf_wet_accumulation",
    "regional_host_pressure",
    "regional_wind_alignment_frequency",
    "week_sin",
    "week_cos",
]

HOST_SPATIAL_FEATURES = [
    "susceptibility_score",
    "host_weighted_risk",
    "regional_neighbor_pressure_2w",
    "regional_neighbor_pressure_3w",
    "neighbor_prevweek_blast",
    "wind_aligned_neighbor_blast",
]

CATEGORICAL_FEATURES = ["region"]
RULES = {
    "bus_critical_any": ("bus_critical_any", "binary_gt_0"),
    "bus_critical_ratio_gt_0": ("bus_critical_ratio", "binary_gt_0"),
    "avgbus_mean_ge_2_25": ("avgbus_mean", "threshold_2_25"),
    "avgbus_max_ge_2_25": ("avgbus_max", "threshold_2_25"),
}


def add_week_seasonality(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["week"] = pd.to_numeric(out["week"], errors="coerce")
    out["week_sin"] = np.sin(2 * np.pi * out["week"] / 53.0)
    out["week_cos"] = np.cos(2 * np.pi * out["week"] / 53.0)
    return out


def safe_roc_auc(y_true: pd.Series, y_score: np.ndarray) -> float | None:
    if pd.Series(y_true).nunique() < 2:
        return None
    return float(roc_auc_score(y_true, y_score))


def safe_pr_auc(y_true: pd.Series, y_score: np.ndarray) -> float | None:
    if pd.Series(y_true).nunique() < 2:
        return None
    return float(average_precision_score(y_true, y_score))


def metric_row(
    analysis: str,
    model: str,
    split: str,
    feature_set: str,
    y_true: pd.Series,
    y_score: np.ndarray,
    threshold: float,
    threshold_source: str,
) -> dict:
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "analysis": analysis,
        "model": model,
        "split": split,
        "feature_set": feature_set,
        "rows": int(len(y_true)),
        "positive_rows": int(pd.Series(y_true).sum()),
        "threshold": float(threshold),
        "threshold_source": threshold_source,
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": safe_roc_auc(y_true, y_score),
        "pr_auc": safe_pr_auc(y_true, y_score),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }


def choose_threshold(y_true: pd.Series, y_score: np.ndarray) -> float:
    rows = []
    for threshold in np.linspace(0.05, 0.95, 19):
        y_pred = (y_score >= threshold).astype(int)
        rows.append(
            {
                "threshold": threshold,
                "f1": f1_score(y_true, y_pred, zero_division=0),
                "recall": recall_score(y_true, y_pred, zero_division=0),
                "precision": precision_score(y_true, y_pred, zero_division=0),
            }
        )
    ranked = pd.DataFrame(rows).sort_values(["f1", "recall", "precision"], ascending=[False, False, False])
    return float(ranked.iloc[0]["threshold"])


def load_dataset() -> pd.DataFrame:
    df = pd.read_csv(DATASET_PATH)
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = add_week_seasonality(df)
    for col in [TARGET, "blast_any", "label_observed", "bus_feature_available"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def bus_available_mask(df: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(df["bus_feature_available"], errors="coerce").fillna(0) > 0


def coverage_audit(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groupings = {
        "overall": [],
        "year": ["year"],
        "region": ["region"],
        "province": ["province"],
        "year_region": ["year", "region"],
        "year_province": ["year", "province"],
    }
    for name, cols in groupings.items():
        grouped = [((), df)] if not cols else df.groupby(cols, dropna=False)
        for keys, group in grouped:
            if not isinstance(keys, tuple):
                keys = (keys,)
            row = {"grouping": name}
            row.update({col: value for col, value in zip(cols, keys)})
            bus_mask = bus_available_mask(group)
            target = pd.to_numeric(group[TARGET], errors="coerce")
            current = pd.to_numeric(group["blast_any"], errors="coerce")
            row.update(
                {
                    "rows": len(group),
                    "bus_rows": int(bus_mask.sum()),
                    "bus_missing_rows": int((~bus_mask).sum()),
                    "bus_missing_rate": float((~bus_mask).mean()),
                    "bus_critical_weeks": int(pd.to_numeric(group["bus_critical_any"], errors="coerce").fillna(0).sum()),
                    "target_known_rows": int(target.notna().sum()),
                    "target_positive_rows": int(target.fillna(0).sum()),
                    "bus_rows_with_target": int((bus_mask & target.notna()).sum()),
                    "bus_rows_target_positive": int(target[bus_mask].fillna(0).sum()),
                    "current_label_positive_in_bus_rows": int(current[bus_mask].fillna(0).sum()),
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def rule_scores(df: pd.DataFrame, rule_name: str) -> tuple[pd.Series, pd.Series]:
    col, kind = RULES[rule_name]
    score = pd.to_numeric(df[col], errors="coerce").fillna(0)
    if kind == "binary_gt_0":
        pred_score = (score > 0).astype(float)
    elif kind == "threshold_2_25":
        pred_score = (score >= BUS_THRESHOLD).astype(float)
    else:
        raise ValueError(kind)
    return score, pred_score


def rule_baselines(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    scopes = {
        "full_updated_dataset": df[df[TARGET].notna()].copy(),
        "bus_covered_subset": df[df[TARGET].notna() & bus_available_mask(df)].copy(),
    }
    for scope, scope_df in scopes.items():
        y_true = (pd.to_numeric(scope_df[TARGET], errors="coerce") > 0).astype(int)
        for rule_name in RULES:
            continuous_score, pred_score = rule_scores(scope_df, rule_name)
            rows.append(
                metric_row(
                    analysis="bus_rule_baseline",
                    model=rule_name,
                    split=scope,
                    feature_set="BUS_rule",
                    y_true=y_true,
                    y_score=pred_score.to_numpy(),
                    threshold=0.5,
                    threshold_source="fixed_rule",
                )
            )
            rows[-1]["continuous_roc_auc"] = safe_roc_auc(y_true, continuous_score.to_numpy())
            rows[-1]["continuous_pr_auc"] = safe_pr_auc(y_true, continuous_score.to_numpy())
    return pd.DataFrame(rows)


def association_summary(df: pd.DataFrame) -> pd.DataFrame:
    features = [
        *BUS_FEATURES,
        "risk_score",
        "leaf_wet_hours",
        "host_weighted_risk",
        "spatial_host_weather_risk",
        "neighbor_prevweek_blast",
        "wind_aligned_neighbor_blast",
        "spore_window_leaf_wet_hours",
    ]
    targets = ["blast_any", TARGET, "risk_score", "leaf_wet_hours", "host_weighted_risk"]
    rows = []
    bus_df = df[bus_available_mask(df)].copy()
    for target_col in targets:
        if target_col not in bus_df.columns:
            continue
        target = pd.to_numeric(bus_df[target_col], errors="coerce")
        for feature in features:
            if feature not in bus_df.columns or feature == target_col:
                continue
            value = pd.to_numeric(bus_df[feature], errors="coerce")
            mask = target.notna() & value.notna()
            if not mask.any():
                continue
            if target_col in ["blast_any", TARGET]:
                binary = (target[mask] > 0).astype(int)
                disease = value[mask & (binary == 1)]
                no_disease = value[mask & (binary == 0)]
                corr = value[mask].corr(binary)
                rows.append(
                    {
                        "target": target_col,
                        "feature": feature,
                        "rows": int(mask.sum()),
                        "positive_rows": int(binary.sum()),
                        "mean_positive": float(disease.mean()) if len(disease) else None,
                        "mean_negative": float(no_disease.mean()) if len(no_disease) else None,
                        "effect_diff": float(disease.mean() - no_disease.mean()) if len(disease) and len(no_disease) else None,
                        "correlation": float(corr) if pd.notna(corr) else None,
                    }
                )
            else:
                corr = value[mask].corr(target[mask])
                rows.append(
                    {
                        "target": target_col,
                        "feature": feature,
                        "rows": int(mask.sum()),
                        "positive_rows": None,
                        "mean_positive": None,
                        "mean_negative": None,
                        "effect_diff": None,
                        "correlation": float(corr) if pd.notna(corr) else None,
                    }
                )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["abs_correlation"] = pd.to_numeric(out["correlation"], errors="coerce").abs()
    return out.sort_values(["target", "abs_correlation"], ascending=[True, False])


def region_summary(df: pd.DataFrame) -> pd.DataFrame:
    bus_df = df[df[TARGET].notna() & bus_available_mask(df)].copy()
    rows = []
    for cols in [["region"], ["year", "region"], ["province", "region"]]:
        for keys, group in bus_df.groupby(cols, dropna=False):
            if not isinstance(keys, tuple):
                keys = (keys,)
            row = {"grouping": "+".join(cols)}
            row.update({col: value for col, value in zip(cols, keys)})
            target = (pd.to_numeric(group[TARGET], errors="coerce") > 0).astype(int)
            critical = pd.to_numeric(group["bus_critical_any"], errors="coerce").fillna(0) > 0
            row.update(
                {
                    "rows": len(group),
                    "positive_rows": int(target.sum()),
                    "positive_rate": float(target.mean()) if len(target) else None,
                    "bus_critical_rows": int(critical.sum()),
                    "bus_critical_rate": float(critical.mean()) if len(critical) else None,
                    "positive_rate_bus_critical": float(target[critical].mean()) if critical.any() else None,
                    "positive_rate_bus_noncritical": float(target[~critical].mean()) if (~critical).any() else None,
                    "mean_avgbus": float(pd.to_numeric(group["avgbus_mean"], errors="coerce").mean()),
                    "max_avgbus": float(pd.to_numeric(group["avgbus_max"], errors="coerce").max()),
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def feature_sets(df: pd.DataFrame) -> dict[str, list[str]]:
    existing_bus = [col for col in BUS_FEATURES if col in df.columns]
    existing_core = [col for col in CORE_FEATURES if col in df.columns]
    existing_host_spatial = [col for col in HOST_SPATIAL_FEATURES if col in df.columns]
    return {
        "BUS_only": existing_bus,
        "core_no_BUS": existing_core,
        "core_plus_BUS": existing_core + existing_bus,
        "BUS_plus_host_spatial": existing_bus + existing_host_spatial,
    }


def build_preprocessor(numeric_features: list[str], categorical_features: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_features,
            ),
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ]
    )


def train_models(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    bus_df = df[df[TARGET].notna() & bus_available_mask(df)].copy()
    train = bus_df[bus_df["year"] == 2020].copy()
    test = bus_df[bus_df["year"] == 2021].copy()
    rows = []
    predictions = []
    manifest = []

    if train.empty or test.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), feasibility_summary(df, train, test)

    train[TARGET] = (pd.to_numeric(train[TARGET], errors="coerce") > 0).astype(int)
    test[TARGET] = (pd.to_numeric(test[TARGET], errors="coerce") > 0).astype(int)

    for set_name, numeric_features in feature_sets(df).items():
        categorical = [col for col in CATEGORICAL_FEATURES if col in df.columns]
        features = numeric_features + categorical
        manifest.append(
            {
                "feature_set": set_name,
                "numeric_feature_count": len(numeric_features),
                "categorical_feature_count": len(categorical),
                "features": "|".join(features),
                "analysis_policy": "exploratory_train_2020_test_2021_due_no_BUS_rows_2017_2019",
            }
        )
        if not numeric_features:
            continue

        x_train = train[features]
        y_train = train[TARGET]
        x_test = test[features]
        y_test = test[TARGET]

        scale_pos_weight = (
            float((y_train == 0).sum() / (y_train == 1).sum())
            if int((y_train == 1).sum()) > 0
            else 1.0
        )
        models = {
            "xgboost": XGBClassifier(
                n_estimators=120,
                max_depth=2,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                eval_metric="logloss",
                random_state=42,
                n_jobs=1,
                scale_pos_weight=scale_pos_weight,
            ),
            "logistic_class_weighted": LogisticRegression(
                class_weight="balanced",
                max_iter=1000,
                random_state=42,
            ),
        }

        for model_name, estimator in models.items():
            preprocessor = build_preprocessor(numeric_features, categorical)
            pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("model", estimator)])
            pipeline.fit(x_train, y_train)
            train_score = pipeline.predict_proba(x_train)[:, 1]
            test_score = pipeline.predict_proba(x_test)[:, 1]
            threshold = choose_threshold(y_train, train_score)
            rows.append(
                metric_row(
                    analysis="bus_ablation_exploratory",
                    model=model_name,
                    split="train_2020",
                    feature_set=set_name,
                    y_true=y_train,
                    y_score=train_score,
                    threshold=threshold,
                    threshold_source="train_2020_f1",
                )
            )
            rows.append(
                metric_row(
                    analysis="bus_ablation_exploratory",
                    model=model_name,
                    split="test_2021",
                    feature_set=set_name,
                    y_true=y_test,
                    y_score=test_score,
                    threshold=threshold,
                    threshold_source="train_2020_f1",
                )
            )
            for row_id, (_, original) in enumerate(test.iterrows()):
                predictions.append(
                    {
                        "model": model_name,
                        "feature_set": set_name,
                        "split": "test_2021",
                        "province": original["province"],
                        "region": original["region"],
                        "datetime": original["datetime"],
                        "year": original["year"],
                        "week": original["week"],
                        "y_true": int(original[TARGET]),
                        "y_score": float(test_score[row_id]),
                        "threshold": float(threshold),
                        "y_pred": int(test_score[row_id] >= threshold),
                    }
                )

    return (
        pd.DataFrame(rows),
        pd.DataFrame(manifest),
        pd.DataFrame(predictions),
        feasibility_summary(df, train, test),
    )


def feasibility_summary(df: pd.DataFrame, train_2020: pd.DataFrame, test_2021: pd.DataFrame) -> pd.DataFrame:
    bus_df = df[df[TARGET].notna() & bus_available_mask(df)].copy()
    train_candidate = bus_df[bus_df["year"].isin([2017, 2018, 2019])]
    rows = [
        {
            "item": "bus_year_coverage",
            "value": "|".join(map(str, sorted(bus_df["year"].dropna().astype(int).unique()))),
            "interpretation": "BUS rows in updated 2015-2021 sequence are available only for these years.",
        },
        {
            "item": "standard_train_2017_2019_bus_rows",
            "value": int(len(train_candidate)),
            "interpretation": "Standard corrected-label train split has no BUS-covered rows, so final BUS model training is not valid yet.",
        },
        {
            "item": "exploratory_train_2020_rows",
            "value": int(len(train_2020)),
            "interpretation": "Used only for exploratory feasibility, not final performance.",
        },
        {
            "item": "exploratory_test_2021_rows",
            "value": int(len(test_2021)),
            "interpretation": "Held out from exploratory 2020 training, but still not a final nationwide split.",
        },
        {
            "item": "dnn_policy",
            "value": "skipped",
            "interpretation": "DNN skipped because BUS coverage has no 2017-2019 training rows and only one BUS-covered training year.",
        },
    ]
    return pd.DataFrame(rows)


def comparison_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    if metrics.empty:
        return pd.DataFrame()
    test = metrics[(metrics["analysis"] == "bus_ablation_exploratory") & (metrics["split"] == "test_2021")].copy()
    if test.empty:
        return pd.DataFrame()
    pivot = test.pivot_table(
        index="model",
        columns="feature_set",
        values=["precision", "recall", "f1", "roc_auc", "pr_auc", "false_positive", "false_negative"],
        aggfunc="first",
    )
    rows = []
    for model in test["model"].unique():
        model_rows = test[test["model"] == model].set_index("feature_set")
        if {"core_no_BUS", "core_plus_BUS"}.issubset(model_rows.index):
            rows.append(
                {
                    "model": model,
                    "comparison": "core_plus_BUS_minus_core_no_BUS",
                    "f1_delta": model_rows.loc["core_plus_BUS", "f1"] - model_rows.loc["core_no_BUS", "f1"],
                    "precision_delta": model_rows.loc["core_plus_BUS", "precision"] - model_rows.loc["core_no_BUS", "precision"],
                    "recall_delta": model_rows.loc["core_plus_BUS", "recall"] - model_rows.loc["core_no_BUS", "recall"],
                    "pr_auc_delta": model_rows.loc["core_plus_BUS", "pr_auc"] - model_rows.loc["core_no_BUS", "pr_auc"],
                    "interpretation_scope": "exploratory_bus_covered_2020_to_2021",
                }
            )
        if {"BUS_only", "BUS_plus_host_spatial"}.issubset(model_rows.index):
            rows.append(
                {
                    "model": model,
                    "comparison": "BUS_plus_host_spatial_minus_BUS_only",
                    "f1_delta": model_rows.loc["BUS_plus_host_spatial", "f1"] - model_rows.loc["BUS_only", "f1"],
                    "precision_delta": model_rows.loc["BUS_plus_host_spatial", "precision"] - model_rows.loc["BUS_only", "precision"],
                    "recall_delta": model_rows.loc["BUS_plus_host_spatial", "recall"] - model_rows.loc["BUS_only", "recall"],
                    "pr_auc_delta": model_rows.loc["BUS_plus_host_spatial", "pr_auc"] - model_rows.loc["BUS_only", "pr_auc"],
                    "interpretation_scope": "exploratory_bus_covered_2020_to_2021",
                }
            )
    summary = pd.DataFrame(rows)
    return summary


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    OUTPUT_DIR.mkdir(exist_ok=True)

    df = load_dataset()
    coverage = coverage_audit(df)
    rule_metrics = rule_baselines(df)
    associations = association_summary(df)
    regions = region_summary(df)
    ablation_metrics, manifest, predictions, feasibility = train_models(df)
    comparison = comparison_summary(ablation_metrics)

    outputs = {
        "bus_coverage_audit.csv": coverage,
        "bus_rule_baseline_metrics.csv": rule_metrics,
        "bus_feature_association_summary.csv": associations,
        "bus_region_summary.csv": regions,
        "bus_feature_feasibility_summary.csv": feasibility,
        "bus_ablation_metrics.csv": ablation_metrics,
        "bus_ablation_feature_manifest.csv": manifest,
        "bus_ablation_predictions.csv": predictions,
        "bus_vs_core_comparison_summary.csv": comparison,
    }
    for filename, out_df in outputs.items():
        out_df.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 80)
    print("\n=== BUS FEASIBILITY ===")
    print(feasibility.to_string(index=False))
    print("\n=== BUS RULE METRICS ===")
    print(rule_metrics.to_string(index=False))
    print("\n=== BUS ABLATION TEST 2021 ===")
    if not ablation_metrics.empty:
        print(ablation_metrics[ablation_metrics["split"] == "test_2021"].to_string(index=False))
    else:
        print("No ablation metrics generated.")
    print("\n=== BUS VS CORE SUMMARY ===")
    print(comparison.to_string(index=False) if not comparison.empty else "No comparison summary generated.")
    print("\n=== OUTPUT FILES ===")
    for filename in outputs:
        print(OUTPUT_DIR / filename)


if __name__ == "__main__":
    main()
