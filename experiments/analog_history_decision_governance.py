from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "experiments" / "outputs"
PREDICTIONS_PATH = OUTPUT_DIR / "analog_ablation_all_predictions.csv"

CANDIDATES = {
    ("dnn_no_class_weight", "core_no_BUS"): "DNN core",
    ("dnn_no_class_weight", "core_plus_analog_history"): "DNN analog history",
    ("random_forest", "core_no_BUS"): "RF core",
    ("random_forest", "core_plus_analog_history"): "RF analog history",
    ("random_forest", "core_plus_all_analog"): "RF all analog",
}

ALERT_BINS = [-0.001, 0.05, 0.15, 0.30, 1.001]
ALERT_LABELS = ["low_risk", "watch", "warning", "high_alert"]


def safe_roc_auc(y_true: pd.Series, y_score: np.ndarray) -> float | None:
    if pd.Series(y_true).nunique() < 2:
        return None
    return float(roc_auc_score(y_true, y_score))


def safe_pr_auc(y_true: pd.Series, y_score: np.ndarray) -> float | None:
    if pd.Series(y_true).nunique() < 2:
        return None
    return float(average_precision_score(y_true, y_score))


def load_predictions() -> pd.DataFrame:
    df = pd.read_csv(PREDICTIONS_PATH, low_memory=False)
    keep = pd.Series(False, index=df.index)
    for model, feature_set in CANDIDATES:
        keep = keep | ((df["model"] == model) & (df["feature_set"] == feature_set))
    df = df[keep].copy()
    df["model_feature"] = df.apply(
        lambda row: f"{row['model']}__{row['feature_set']}", axis=1
    )
    df["model_label"] = df.apply(
        lambda row: CANDIDATES[(row["model"], row["feature_set"])], axis=1
    )
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["y_true"] = pd.to_numeric(df["y_true"], errors="coerce").astype(int)
    df["y_score"] = pd.to_numeric(df["y_score"], errors="coerce")
    return df.dropna(subset=["y_score"])


def threshold_grid(y_true: pd.Series, y_score: pd.Series) -> pd.DataFrame:
    rows = []
    for threshold in np.linspace(0.01, 0.99, 99):
        y_pred = (y_score >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        rows.append(
            {
                "threshold": float(threshold),
                "precision": precision_score(y_true, y_pred, zero_division=0),
                "recall": recall_score(y_true, y_pred, zero_division=0),
                "f1": f1_score(y_true, y_pred, zero_division=0),
                "false_positive": int(fp),
                "false_negative": int(fn),
                "true_positive": int(tp),
                "true_negative": int(tn),
            }
        )
    return pd.DataFrame(rows)


def threshold_row(group_keys: tuple, policy: str, region: str, row: pd.Series) -> dict:
    model, feature_set, model_label, model_feature = group_keys
    out = {
        "model": model,
        "feature_set": feature_set,
        "model_label": model_label,
        "model_feature": model_feature,
        "policy": policy,
        "region": region,
    }
    for col in [
        "threshold",
        "precision",
        "recall",
        "f1",
        "false_positive",
        "false_negative",
        "true_positive",
        "true_negative",
    ]:
        out[f"validation_{col}"] = row[col]
    return out


def pick_thresholds(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    val = predictions[predictions["split"] == "validation"].copy()
    for keys, group in val.groupby(["model", "feature_set", "model_label", "model_feature"]):
        grid = threshold_grid(group["y_true"], group["y_score"])
        f1_row = grid.sort_values(["f1", "recall", "precision"], ascending=[False, False, False]).iloc[0]
        rows.append(threshold_row(keys, "global_f1", "all", f1_row))

        viable = grid[grid["f1"] >= grid["f1"].quantile(0.75)].copy()
        viable["precision_recall_gap"] = (viable["precision"] - viable["recall"]).abs()
        rows.append(
            threshold_row(
                keys,
                "balanced_default",
                "all",
                viable.sort_values(["precision_recall_gap", "f1"], ascending=[True, False]).iloc[0],
            )
        )

        hp = grid[(grid["recall"] >= 0.10) & (grid["true_positive"] > 0)].copy()
        rows.append(
            threshold_row(
                keys,
                "high_precision",
                "all",
                hp.sort_values(["precision", "f1", "recall"], ascending=[False, False, False]).iloc[0],
            )
        )

        hr = grid[(grid["precision"] >= 0.10) & (grid["true_positive"] > 0)].copy()
        rows.append(
            threshold_row(
                keys,
                "high_recall",
                "all",
                hr.sort_values(["recall", "f1", "precision"], ascending=[False, False, False]).iloc[0],
            )
        )

        for region, region_group in group.groupby("region"):
            if region_group["y_true"].sum() == 0:
                continue
            region_grid = threshold_grid(region_group["y_true"], region_group["y_score"])
            region_f1 = region_grid.sort_values(
                ["f1", "recall", "precision"], ascending=[False, False, False]
            ).iloc[0]
            rows.append(threshold_row(keys, "region_f1_exploratory", region, region_f1))

    return pd.DataFrame(rows)


def metric_row(
    keys: tuple,
    policy: str,
    split: str,
    y_true: pd.Series,
    y_score: pd.Series,
    y_pred: np.ndarray,
    threshold: float | None,
) -> dict:
    model, feature_set, model_label, model_feature = keys
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "model": model,
        "feature_set": feature_set,
        "model_label": model_label,
        "model_feature": model_feature,
        "policy": policy,
        "split": split,
        "rows": int(len(y_true)),
        "positive_rows": int(y_true.sum()),
        "threshold": threshold,
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": safe_roc_auc(y_true, y_score.to_numpy()),
        "pr_auc": safe_pr_auc(y_true, y_score.to_numpy()),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }


def add_failures(rows: list[dict], group: pd.DataFrame, y_pred: np.ndarray, policy: str, threshold: float | None) -> None:
    temp = group.copy()
    temp["policy_pred"] = y_pred
    failed = temp[temp["y_true"] != temp["policy_pred"]].copy()
    for row in failed.itertuples(index=False):
        rows.append(
            {
                "model": row.model,
                "feature_set": row.feature_set,
                "model_label": row.model_label,
                "model_feature": row.model_feature,
                "policy": policy,
                "threshold": threshold,
                "error_type": "false_positive" if row.y_true == 0 else "false_negative",
                "province": row.province,
                "region": row.region,
                "datetime": row.datetime,
                "year": int(row.year),
                "week": int(row.week),
                "y_true": int(row.y_true),
                "y_score": float(row.y_score),
                "y_pred": int(row.policy_pred),
            }
        )


def evaluate_policies(predictions: pd.DataFrame, thresholds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metric_rows = []
    confusion_rows = []
    failure_rows = []
    test = predictions[predictions["split"] == "test"].copy()
    global_thresholds = thresholds[thresholds["region"] == "all"].copy()

    for threshold in global_thresholds.itertuples(index=False):
        group = test[test["model_feature"] == threshold.model_feature].copy()
        keys = (threshold.model, threshold.feature_set, threshold.model_label, threshold.model_feature)
        y_pred = (group["y_score"] >= threshold.validation_threshold).astype(int).to_numpy()
        row = metric_row(
            keys,
            threshold.policy,
            "test",
            group["y_true"],
            group["y_score"],
            y_pred,
            float(threshold.validation_threshold),
        )
        metric_rows.append(row)
        confusion_rows.append(row)
        add_failures(failure_rows, group, y_pred, threshold.policy, float(threshold.validation_threshold))

    return pd.DataFrame(metric_rows), pd.DataFrame(confusion_rows), pd.DataFrame(failure_rows)


def fit_calibrators(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    calibrated_frames = []
    threshold_rows = []
    reliability_rows = []

    for keys, group in predictions.groupby(["model", "feature_set", "model_label", "model_feature"]):
        val = group[group["split"] == "validation"].copy()
        test = group[group["split"] == "test"].copy()
        if val["y_true"].nunique() < 2:
            continue

        platt = LogisticRegression(max_iter=1000)
        platt.fit(val[["y_score"]], val["y_true"])
        for split_group in [val, test]:
            out = split_group.copy()
            out["calibrator"] = "platt"
            out["calibrated_score"] = platt.predict_proba(out[["y_score"]])[:, 1]
            calibrated_frames.append(out)

        if len(val) >= 200 and val["y_true"].sum() >= 20:
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(val["y_score"], val["y_true"])
            for split_group in [val, test]:
                out = split_group.copy()
                out["calibrator"] = "isotonic"
                out["calibrated_score"] = iso.predict(out["y_score"])
                calibrated_frames.append(out)

    calibrated = pd.concat(calibrated_frames, ignore_index=True)

    for keys, group in calibrated.groupby(["model", "feature_set", "model_label", "model_feature", "calibrator"]):
        model, feature_set, model_label, model_feature, calibrator = keys
        base_keys = (model, feature_set, model_label, model_feature)
        val = group[group["split"] == "validation"].copy()
        test = group[group["split"] == "test"].copy()
        grid = threshold_grid(val["y_true"], val["calibrated_score"])
        best = grid.sort_values(["f1", "recall", "precision"], ascending=[False, False, False]).iloc[0]
        threshold_rows.append(threshold_row(base_keys, f"{calibrator}_global_f1", "all", best))
        y_pred = (test["calibrated_score"] >= best["threshold"]).astype(int).to_numpy()
        reliability_rows.append(
            metric_row(
                base_keys,
                f"{calibrator}_global_f1",
                "test",
                test["y_true"],
                test["calibrated_score"],
                y_pred,
                float(best["threshold"]),
            )
        )

        for split_name, split_group in group.groupby("split"):
            binned = split_group.copy()
            binned["bin"] = pd.cut(binned["calibrated_score"], bins=np.linspace(0, 1, 11), include_lowest=True)
            for bin_value, bin_group in binned.groupby("bin", dropna=False):
                if len(bin_group) == 0:
                    continue
                reliability_rows.append(
                    {
                        "model": model,
                        "feature_set": feature_set,
                        "model_label": model_label,
                        "model_feature": model_feature,
                        "policy": f"{calibrator}_reliability",
                        "split": split_name,
                        "calibrator": calibrator,
                        "bin": str(bin_value),
                        "rows": int(len(bin_group)),
                        "positive_rows": int(bin_group["y_true"].sum()),
                        "mean_score": float(bin_group["calibrated_score"].mean()),
                        "observed_positive_rate": float(bin_group["y_true"].mean()),
                    }
                )

    return calibrated, pd.DataFrame(threshold_rows), pd.DataFrame(reliability_rows)


def region_performance(predictions: pd.DataFrame, thresholds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    test = predictions[predictions["split"] == "test"].copy()
    policies = ["global_f1", "balanced_default", "high_precision", "high_recall"]
    for threshold in thresholds[(thresholds["region"] == "all") & (thresholds["policy"].isin(policies))].itertuples(index=False):
        group = test[test["model_feature"] == threshold.model_feature].copy()
        group["policy_pred"] = (group["y_score"] >= threshold.validation_threshold).astype(int)
        keys = (threshold.model, threshold.feature_set, threshold.model_label, threshold.model_feature)
        for region, rg in group.groupby("region"):
            row = metric_row(
                keys,
                threshold.policy,
                f"test_region_{region}",
                rg["y_true"],
                rg["y_score"],
                rg["policy_pred"].to_numpy(),
                float(threshold.validation_threshold),
            )
            row["region"] = region
            rows.append(row)
    return pd.DataFrame(rows)


def alert_tiers(calibrated: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    platt = calibrated[(calibrated["calibrator"] == "platt") & (calibrated["split"] == "test")].copy()
    platt["alert_tier"] = pd.cut(platt["calibrated_score"], bins=ALERT_BINS, labels=ALERT_LABELS).astype(str)
    platt["action_positive"] = platt["alert_tier"].isin(["warning", "high_alert"]).astype(int)

    summary = (
        platt.groupby(["model", "feature_set", "model_label", "model_feature", "alert_tier"], dropna=False)
        .agg(
            rows=("y_true", "size"),
            positive_rows=("y_true", "sum"),
            observed_positive_rate=("y_true", "mean"),
            mean_calibrated_score=("calibrated_score", "mean"),
            false_positive_as_action=("action_positive", lambda s: int(((platt.loc[s.index, "y_true"] == 0) & (s == 1)).sum())),
            false_negative_as_low_watch=("action_positive", lambda s: int(((platt.loc[s.index, "y_true"] == 1) & (s == 0)).sum())),
        )
        .reset_index()
    )
    region = (
        platt.groupby(["model", "feature_set", "model_label", "model_feature", "alert_tier", "region"], dropna=False)
        .agg(
            rows=("y_true", "size"),
            positive_rows=("y_true", "sum"),
            observed_positive_rate=("y_true", "mean"),
        )
        .reset_index()
    )
    errors = platt[platt["y_true"] != platt["action_positive"]].copy()
    errors["error_type"] = np.where(errors["y_true"] == 0, "false_positive_action", "false_negative_low_watch")
    return summary, region, errors


def policy_comparison(metrics: pd.DataFrame, reliability: pd.DataFrame) -> pd.DataFrame:
    calibrated_metrics = reliability[reliability["policy"].astype(str).str.endswith("_global_f1")].copy()
    common = [col for col in metrics.columns if col in calibrated_metrics.columns]
    return pd.concat([metrics[common], calibrated_metrics[common]], ignore_index=True).sort_values(
        ["f1", "pr_auc", "roc_auc"], ascending=[False, False, False]
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    OUTPUT_DIR.mkdir(exist_ok=True)
    predictions = load_predictions()
    thresholds = pick_thresholds(predictions)
    policy_metrics, confusion, failures = evaluate_policies(predictions, thresholds)
    calibrated, calibration_thresholds, reliability = fit_calibrators(predictions)
    all_thresholds = pd.concat([thresholds, calibration_thresholds], ignore_index=True, sort=False)
    region_df = region_performance(predictions, thresholds)
    alert_summary, alert_region, alert_errors = alert_tiers(calibrated)
    comparison = policy_comparison(policy_metrics, reliability)

    outputs = {
        "analog_decision_policy_metrics.csv": policy_metrics,
        "analog_decision_model_comparison.csv": comparison,
        "analog_decision_region_performance.csv": region_df,
        "analog_decision_confusion_matrix.csv": confusion,
        "analog_decision_alert_tier_summary.csv": alert_summary,
        "analog_decision_alert_tier_region_summary.csv": alert_region,
        "analog_decision_calibration_reliability.csv": reliability,
        "analog_decision_failure_cases.csv": pd.concat([failures, alert_errors], ignore_index=True, sort=False),
        "analog_decision_thresholds.csv": all_thresholds,
        "analog_decision_calibrated_predictions.csv": calibrated,
    }
    for filename, out_df in outputs.items():
        out_df.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 240)
    pd.set_option("display.max_columns", 80)
    print("\n=== ANALOG DECISION COMPARISON ===")
    print(comparison.head(30).to_string(index=False))
    print("\n=== THRESHOLDS ===")
    print(all_thresholds[all_thresholds["region"] == "all"].to_string(index=False))
    print("\n=== ALERT TIERS ===")
    print(alert_summary.to_string(index=False))
    print("\n=== OUTPUT FILES ===")
    for filename in outputs:
        print(OUTPUT_DIR / filename)


if __name__ == "__main__":
    main()
