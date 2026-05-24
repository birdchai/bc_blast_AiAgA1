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

TABULAR_PREDICTIONS = OUTPUT_DIR / "updated_2022_all_predictions.csv"
TEMPORAL_PREDICTIONS = OUTPUT_DIR / "temporal_model_forward_all_predictions.csv"

CANDIDATE_TABULAR = {
    "dnn_no_class_weight_core_no_BUS": "DNN no class weight",
    "random_forest_core_no_BUS": "Random Forest",
    "dnn_class_weight_core_no_BUS": "DNN class weighted",
}
CANDIDATE_TEMPORAL = {
    ("hybrid_dnn_tcn", 2): "Hybrid DNN TCN 2w",
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
    frames = []

    tabular = pd.read_csv(TABULAR_PREDICTIONS)
    tabular = tabular[tabular["model"].isin(CANDIDATE_TABULAR)].copy()
    tabular["model_label"] = tabular["model"].map(CANDIDATE_TABULAR)
    tabular["sequence_length"] = 0
    tabular["datetime"] = pd.to_datetime(tabular["datetime"], errors="coerce")
    frames.append(
        tabular[
            [
                "model",
                "model_label",
                "sequence_length",
                "split",
                "province",
                "region",
                "datetime",
                "year",
                "week",
                "y_true",
                "y_score",
            ]
        ]
    )

    temporal = pd.read_csv(TEMPORAL_PREDICTIONS)
    keep = pd.Series(False, index=temporal.index)
    for (model, sequence_length), label in CANDIDATE_TEMPORAL.items():
        keep = keep | ((temporal["model"] == model) & (temporal["sequence_length"] == sequence_length))
    temporal = temporal[keep].copy()
    temporal["model_label"] = [
        CANDIDATE_TEMPORAL.get((row.model, int(row.sequence_length)))
        for row in temporal.itertuples(index=False)
    ]
    temporal["datetime"] = pd.to_datetime(temporal["end_datetime"], errors="coerce")
    temporal["week"] = temporal["end_week"]
    frames.append(
        temporal[
            [
                "model",
                "model_label",
                "sequence_length",
                "split",
                "province",
                "region",
                "datetime",
                "year",
                "week",
                "y_true",
                "y_score",
            ]
        ]
    )

    out = pd.concat(frames, ignore_index=True)
    out["y_true"] = pd.to_numeric(out["y_true"], errors="coerce").astype(int)
    out["y_score"] = pd.to_numeric(out["y_score"], errors="coerce")
    return out.dropna(subset=["y_score"])


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


def pick_thresholds(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    val = predictions[predictions["split"] == "validation"].copy()
    for (model, label, sequence_length), group in val.groupby(["model", "model_label", "sequence_length"]):
        grid = threshold_grid(group["y_true"], group["y_score"])
        f1_row = grid.sort_values(["f1", "recall", "precision"], ascending=[False, False, False]).iloc[0]
        rows.append(threshold_row(model, label, sequence_length, "global_f1", "all", f1_row))

        hp_pool = grid[(grid["recall"] >= 0.10) & (grid["true_positive"] > 0)].copy()
        if hp_pool.empty:
            hp_pool = grid[grid["true_positive"] > 0].copy()
        hp_row = hp_pool.sort_values(["precision", "f1", "recall"], ascending=[False, False, False]).iloc[0]
        rows.append(threshold_row(model, label, sequence_length, "high_precision", "all", hp_row))

        hr_pool = grid[(grid["precision"] >= 0.10) & (grid["true_positive"] > 0)].copy()
        if hr_pool.empty:
            hr_pool = grid[grid["true_positive"] > 0].copy()
        hr_row = hr_pool.sort_values(["recall", "f1", "precision"], ascending=[False, False, False]).iloc[0]
        rows.append(threshold_row(model, label, sequence_length, "high_recall", "all", hr_row))

        viable = grid[grid["f1"] >= grid["f1"].quantile(0.75)].copy()
        viable["precision_recall_gap"] = (viable["precision"] - viable["recall"]).abs()
        balanced = viable.sort_values(["precision_recall_gap", "f1"], ascending=[True, False]).iloc[0]
        rows.append(threshold_row(model, label, sequence_length, "balanced_default", "all", balanced))

        for region, region_group in group.groupby("region"):
            if region_group["y_true"].sum() == 0:
                continue
            region_grid = threshold_grid(region_group["y_true"], region_group["y_score"])
            region_row = region_grid.sort_values(["f1", "recall", "precision"], ascending=[False, False, False]).iloc[0]
            rows.append(threshold_row(model, label, sequence_length, "region_f1_exploratory", region, region_row))
    return pd.DataFrame(rows)


def threshold_row(model: str, label: str, sequence_length: int, policy: str, region: str, row: pd.Series) -> dict:
    out = {
        "model": model,
        "model_label": label,
        "sequence_length": int(sequence_length),
        "policy": policy,
        "region": region,
    }
    for col in ["threshold", "precision", "recall", "f1", "false_positive", "false_negative", "true_positive", "true_negative"]:
        out[f"validation_{col}"] = row[col]
    return out


def metric_row(
    model: str,
    label: str,
    sequence_length: int,
    policy: str,
    split: str,
    y_true: pd.Series,
    y_score: pd.Series,
    y_pred: np.ndarray,
    threshold: float | None,
) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "model": model,
        "model_label": label,
        "sequence_length": int(sequence_length),
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


def evaluate_policies(predictions: pd.DataFrame, thresholds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metric_rows = []
    confusion_rows = []
    failure_rows = []
    test = predictions[predictions["split"] == "test"].copy()
    global_policies = thresholds[thresholds["region"] == "all"].copy()

    for threshold in global_policies.itertuples(index=False):
        group = test[
            (test["model"] == threshold.model)
            & (test["sequence_length"] == threshold.sequence_length)
        ].copy()
        y_pred = (group["y_score"] >= threshold.validation_threshold).astype(int).to_numpy()
        row = metric_row(
            threshold.model,
            threshold.model_label,
            threshold.sequence_length,
            threshold.policy,
            "test",
            group["y_true"],
            group["y_score"],
            y_pred,
            float(threshold.validation_threshold),
        )
        metric_rows.append(row)
        confusion_rows.append(row)
        add_failures(failure_rows, group, y_pred, threshold.policy, threshold.validation_threshold)

    region_thresholds = thresholds[thresholds["policy"] == "region_f1_exploratory"].copy()
    for (model, label, sequence_length), group in test.groupby(["model", "model_label", "sequence_length"]):
        model_thresholds = region_thresholds[
            (region_thresholds["model"] == model)
            & (region_thresholds["sequence_length"] == sequence_length)
        ].set_index("region")
        fallback = global_policies[
            (global_policies["model"] == model)
            & (global_policies["sequence_length"] == sequence_length)
            & (global_policies["policy"] == "global_f1")
        ]["validation_threshold"].iloc[0]
        thresholds_used = group["region"].map(model_thresholds["validation_threshold"]).fillna(fallback)
        y_pred = (group["y_score"].to_numpy() >= thresholds_used.to_numpy()).astype(int)
        row = metric_row(
            model,
            label,
            sequence_length,
            "region_f1_exploratory",
            "test",
            group["y_true"],
            group["y_score"],
            y_pred,
            None,
        )
        metric_rows.append(row)
        confusion_rows.append(row)
        add_failures(failure_rows, group, y_pred, "region_f1_exploratory", None)

    return pd.DataFrame(metric_rows), pd.DataFrame(confusion_rows), pd.DataFrame(failure_rows)


def add_failures(rows: list[dict], group: pd.DataFrame, y_pred: np.ndarray, policy: str, threshold: float | None) -> None:
    temp = group.copy()
    temp["y_pred_policy"] = y_pred
    failed = temp[temp["y_true"] != temp["y_pred_policy"]].copy()
    for row in failed.itertuples(index=False):
        rows.append(
            {
                "model": row.model,
                "model_label": row.model_label,
                "sequence_length": int(row.sequence_length),
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
                "y_pred": int(row.y_pred_policy),
            }
        )


def fit_calibrators(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    calibrated_frames = []
    reliability_rows = []
    threshold_rows = []
    for (model, label, sequence_length), group in predictions.groupby(["model", "model_label", "sequence_length"]):
        val = group[group["split"] == "validation"].copy()
        test = group[group["split"] == "test"].copy()
        if val["y_true"].nunique() < 2:
            continue

        platt = LogisticRegression(max_iter=1000)
        platt.fit(val[["y_score"]], val["y_true"])
        for split_name, split_group in [("validation", val), ("test", test)]:
            out = split_group.copy()
            out["calibrator"] = "platt"
            out["calibrated_score"] = platt.predict_proba(out[["y_score"]])[:, 1]
            calibrated_frames.append(out)

        if len(val) >= 200 and val["y_true"].sum() >= 20:
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(val["y_score"], val["y_true"])
            for split_name, split_group in [("validation", val), ("test", test)]:
                out = split_group.copy()
                out["calibrator"] = "isotonic"
                out["calibrated_score"] = iso.predict(out["y_score"])
                calibrated_frames.append(out)

    calibrated = pd.concat(calibrated_frames, ignore_index=True)

    for (model, label, sequence_length, calibrator), group in calibrated.groupby(["model", "model_label", "sequence_length", "calibrator"]):
        val = group[group["split"] == "validation"].copy()
        test = group[group["split"] == "test"].copy()
        grid = threshold_grid(val["y_true"], val["calibrated_score"])
        best = grid.sort_values(["f1", "recall", "precision"], ascending=[False, False, False]).iloc[0]
        threshold_rows.append(threshold_row(model, label, sequence_length, f"{calibrator}_global_f1", "all", best))

        y_pred = (test["calibrated_score"] >= best["threshold"]).astype(int).to_numpy()
        reliability_rows.append(
            metric_row(
                model,
                label,
                sequence_length,
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
                        "model_label": label,
                        "sequence_length": int(sequence_length),
                        "policy": f"{calibrator}_reliability",
                        "split": split_name,
                        "bin": str(bin_value),
                        "rows": int(len(bin_group)),
                        "positive_rows": int(bin_group["y_true"].sum()),
                        "mean_score": float(bin_group["calibrated_score"].mean()),
                        "observed_positive_rate": float(bin_group["y_true"].mean()),
                        "calibrator": calibrator,
                    }
                )

    return calibrated, pd.DataFrame(threshold_rows), pd.DataFrame(reliability_rows)


def alert_tiers(calibrated: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    platt_test = calibrated[(calibrated["calibrator"] == "platt") & (calibrated["split"] == "test")].copy()
    platt_test["alert_tier"] = pd.cut(platt_test["calibrated_score"], bins=ALERT_BINS, labels=ALERT_LABELS).astype(str)
    platt_test["action_positive"] = platt_test["alert_tier"].isin(["warning", "high_alert"]).astype(int)

    summary_rows = []
    region_rows = []
    error_rows = []
    for (model, label, sequence_length, tier), group in platt_test.groupby(["model", "model_label", "sequence_length", "alert_tier"], dropna=False):
        y_true = group["y_true"].astype(int)
        action = group["action_positive"].astype(int)
        summary_rows.append(
            {
                "model": model,
                "model_label": label,
                "sequence_length": int(sequence_length),
                "alert_tier": tier,
                "rows": int(len(group)),
                "positive_rows": int(y_true.sum()),
                "observed_positive_rate": float(y_true.mean()) if len(y_true) else None,
                "mean_calibrated_score": float(group["calibrated_score"].mean()) if len(group) else None,
                "false_positive_as_action": int(((y_true == 0) & (action == 1)).sum()),
                "false_negative_as_low_watch": int(((y_true == 1) & (action == 0)).sum()),
            }
        )
    for (model, label, sequence_length, tier, region), group in platt_test.groupby(["model", "model_label", "sequence_length", "alert_tier", "region"], dropna=False):
        region_rows.append(
            {
                "model": model,
                "model_label": label,
                "sequence_length": int(sequence_length),
                "alert_tier": tier,
                "region": region,
                "rows": int(len(group)),
                "positive_rows": int(group["y_true"].sum()),
                "observed_positive_rate": float(group["y_true"].mean()) if len(group) else None,
            }
        )
    for row in platt_test[platt_test["y_true"] != platt_test["action_positive"]].itertuples(index=False):
        error_rows.append(
            {
                "model": row.model,
                "model_label": row.model_label,
                "sequence_length": int(row.sequence_length),
                "alert_tier": row.alert_tier,
                "error_type": "false_positive_action" if row.y_true == 0 else "false_negative_low_watch",
                "province": row.province,
                "region": row.region,
                "datetime": row.datetime,
                "y_true": int(row.y_true),
                "calibrated_score": float(row.calibrated_score),
            }
        )
    return pd.DataFrame(summary_rows), pd.DataFrame(region_rows), pd.DataFrame(error_rows)


def region_performance(predictions: pd.DataFrame, thresholds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    test = predictions[predictions["split"] == "test"].copy()
    use_policies = thresholds[(thresholds["region"] == "all") & (thresholds["policy"].isin(["global_f1", "high_precision", "high_recall", "balanced_default"]))]
    for threshold in use_policies.itertuples(index=False):
        group = test[(test["model"] == threshold.model) & (test["sequence_length"] == threshold.sequence_length)].copy()
        group["y_pred"] = (group["y_score"] >= threshold.validation_threshold).astype(int)
        for region, rg in group.groupby("region"):
            rows.append(
                metric_row(
                    threshold.model,
                    threshold.model_label,
                    threshold.sequence_length,
                    threshold.policy,
                    "test_region_" + str(region),
                    rg["y_true"],
                    rg["y_score"],
                    rg["y_pred"].to_numpy(),
                    float(threshold.validation_threshold),
                )
            )
            rows[-1]["region"] = region
    return pd.DataFrame(rows)


def policy_comparison(metrics: pd.DataFrame, reliability: pd.DataFrame) -> pd.DataFrame:
    classification = metrics.copy()
    calibrated_metrics = reliability[reliability["policy"].astype(str).str.endswith("_global_f1")].copy()
    common_cols = [col for col in classification.columns if col in calibrated_metrics.columns]
    combined = pd.concat([classification[common_cols], calibrated_metrics[common_cols]], ignore_index=True)
    return combined.sort_values(["f1", "pr_auc", "roc_auc"], ascending=[False, False, False])


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    OUTPUT_DIR.mkdir(exist_ok=True)

    predictions = load_predictions()
    thresholds = pick_thresholds(predictions)
    policy_metrics, confusion, failures = evaluate_policies(predictions, thresholds)
    calibrated, calibration_thresholds, reliability = fit_calibrators(predictions)
    alert_summary, alert_region, alert_errors = alert_tiers(calibrated)
    region_df = region_performance(predictions, thresholds)
    comparison = policy_comparison(policy_metrics, reliability)

    thresholds_all = pd.concat([thresholds, calibration_thresholds], ignore_index=True, sort=False)
    calibrated.to_csv(OUTPUT_DIR / "forward_calibrated_predictions.csv", index=False, encoding="utf-8-sig")

    outputs = {
        "forward_decision_policy_metrics.csv": policy_metrics,
        "forward_model_thresholds.csv": thresholds_all,
        "forward_decision_region_performance.csv": region_df,
        "forward_decision_confusion_matrix.csv": confusion,
        "forward_alert_tier_summary.csv": alert_summary,
        "forward_alert_tier_region_summary.csv": alert_region,
        "forward_policy_model_comparison.csv": comparison,
        "forward_calibration_reliability_summary.csv": reliability,
        "forward_decision_failure_cases.csv": pd.concat([failures, alert_errors], ignore_index=True, sort=False),
    }
    for filename, df in outputs.items():
        df.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 80)
    print("\n=== POLICY COMPARISON TOP ROWS ===")
    print(comparison.head(20).to_string(index=False))
    print("\n=== THRESHOLDS ===")
    print(thresholds_all[thresholds_all["region"] == "all"].to_string(index=False))
    print("\n=== ALERT SUMMARY ===")
    print(alert_summary.to_string(index=False))
    print("\n=== OUTPUT FILES ===")
    print(OUTPUT_DIR / "forward_calibrated_predictions.csv")
    for filename in outputs:
        print(OUTPUT_DIR / filename)


if __name__ == "__main__":
    main()
