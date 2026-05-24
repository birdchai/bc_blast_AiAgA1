from __future__ import annotations

from pathlib import Path
import random
import sys

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
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
from sklearn.utils.class_weight import compute_class_weight
from xgboost import XGBClassifier

import tensorflow as tf

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

DATASET_PATH = BASE_DIR / "experiments" / "outputs" / "region_temporal_sequence_dataset_updated_labels_2015_2021.csv"
OUTPUT_DIR = BASE_DIR / "experiments" / "outputs"
TARGET = "blast_t_plus_1"

TRAIN_YEARS = [2017, 2018, 2019]
VALIDATION_YEARS = [2020]
TEST_YEARS = [2021]

TARGET_COLUMNS = ["blast_t_plus_1", "blast_t_plus_2"]
CURRENT_LABEL_COLUMNS = ["blast_any", "blast_days", "blast_area"]
BUS_COLUMNS = [
    "bus_feature_available",
    "bus_observed_days",
    "avgbus_mean",
    "avgbus_max",
    "maxbus_max",
    "bus_critical_days",
    "bus_critical_any",
    "bus_critical_ratio",
]
EXCLUDED_COLUMNS = set(
    TARGET_COLUMNS
    + CURRENT_LABEL_COLUMNS
    + BUS_COLUMNS
    + [
        "datetime",
        "year",
        "week",
        "label_source_available",
        "label_observed",
    ]
)

CORE_NUMERIC_CANDIDATES = [
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
    "total_pov_area",
    "pov_variety_count",
    "host_weighted_risk",
    "host_weighted_rolling_2w",
    "host_weighted_rolling_3w",
    "neighbor_prevweek_risk",
    "neighbor_prevweek_blast",
    "spatial_host_weather_risk",
    "prevailing_wind_direction",
    "wind_direction_variability",
    "mean_wind_speed",
    "max_wind_speed",
    "mean_wind_gust",
    "humid_wind_hours",
    "leaf_wet_wind_hours",
    "wind_aligned_neighbor_blast",
    "wind_aligned_neighbor_count",
    "regional_neighbor_pressure_2w",
    "regional_neighbor_pressure_3w",
    "regional_leaf_wet_accumulation",
    "regional_host_pressure",
    "regional_wind_alignment_frequency",
    "spore_window_leaf_wet_hours",
    "spore_window_humid_wind_hours",
    "spore_window_wind_aligned_neighbor_blast",
    "week_sin",
    "week_cos",
]
CATEGORICAL_CANDIDATES = ["province", "region"]


def set_reproducibility(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)


def add_week_seasonality(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["week"] = pd.to_numeric(out["week"], errors="coerce")
    out["week_sin"] = np.sin(2 * np.pi * out["week"] / 53.0)
    out["week_cos"] = np.cos(2 * np.pi * out["week"] / 53.0)
    return out


def load_dataset() -> pd.DataFrame:
    df = pd.read_csv(DATASET_PATH)
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = add_week_seasonality(df)
    for col in CORE_NUMERIC_CANDIDATES + TARGET_COLUMNS + CURRENT_LABEL_COLUMNS + ["label_observed"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def safe_existing(df: pd.DataFrame, features: list[str]) -> list[str]:
    return [feature for feature in features if feature in df.columns and feature not in EXCLUDED_COLUMNS]


def feature_lists(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    numeric = safe_existing(df, CORE_NUMERIC_CANDIDATES)
    categorical = [col for col in CATEGORICAL_CANDIDATES if col in df.columns and col not in EXCLUDED_COLUMNS]
    return numeric, categorical


def split_data(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    usable = df[df[TARGET].notna()].copy()
    usable[TARGET] = (pd.to_numeric(usable[TARGET], errors="coerce") > 0).astype(int)
    return {
        "train": usable[usable["year"].isin(TRAIN_YEARS)].copy(),
        "validation": usable[usable["year"].isin(VALIDATION_YEARS)].copy(),
        "test": usable[usable["year"].isin(TEST_YEARS)].copy(),
    }


def split_summary(df: pd.DataFrame, splits: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for split_name, split_df in splits.items():
        target = pd.to_numeric(split_df[TARGET], errors="coerce")
        rows.append(
            {
                "split": split_name,
                "years": "|".join(map(str, sorted(split_df["year"].dropna().astype(int).unique()))),
                "rows": len(split_df),
                "positive_rows": int(target.fillna(0).sum()),
                "positive_rate": float(target.mean()) if len(target) else None,
                "provinces": int(split_df["province"].nunique()),
                "regions": int(split_df["region"].nunique()),
                "label_observed_rows": int(pd.to_numeric(split_df["label_observed"], errors="coerce").fillna(0).sum())
                if "label_observed" in split_df.columns
                else None,
                "label_observed_rate": float(pd.to_numeric(split_df["label_observed"], errors="coerce").fillna(0).mean())
                if "label_observed" in split_df.columns and len(split_df)
                else None,
            }
        )
    rows.append(
        {
            "split": "feature_only_2015",
            "years": "2015",
            "rows": int((df["year"] == 2015).sum()),
            "positive_rows": None,
            "positive_rate": None,
            "provinces": int(df.loc[df["year"] == 2015, "province"].nunique()),
            "regions": int(df.loc[df["year"] == 2015, "region"].nunique()),
            "label_observed_rows": int(pd.to_numeric(df.loc[df["year"] == 2015, "label_observed"], errors="coerce").fillna(0).sum())
            if "label_observed" in df.columns
            else None,
            "label_observed_rate": 0.0,
        }
    )
    return pd.DataFrame(rows)


def make_preprocessor(
    numeric_features: list[str],
    categorical_features: list[str],
    scale_numeric: bool,
) -> ColumnTransformer:
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))
    numeric_pipeline = Pipeline(steps=numeric_steps)
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ]
    )


def encoded_feature_names(
    preprocessor: ColumnTransformer,
    numeric_features: list[str],
    categorical_features: list[str],
) -> list[str]:
    names = list(numeric_features)
    if categorical_features:
        encoder = preprocessor.named_transformers_["categorical"].named_steps["onehot"]
        if hasattr(encoder, "get_feature_names_out"):
            names.extend(encoder.get_feature_names_out(categorical_features).tolist())
        else:
            names.extend(encoder.get_feature_names(categorical_features).tolist())
    return names


def safe_roc_auc(y_true: pd.Series, y_score: np.ndarray) -> float | None:
    if pd.Series(y_true).nunique() < 2:
        return None
    return float(roc_auc_score(y_true, y_score))


def safe_pr_auc(y_true: pd.Series, y_score: np.ndarray) -> float | None:
    if pd.Series(y_true).nunique() < 2:
        return None
    return float(average_precision_score(y_true, y_score))


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


def metric_row(
    model: str,
    split: str,
    y_true: pd.Series,
    y_score: np.ndarray,
    threshold: float,
) -> dict:
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "model": model,
        "feature_set": "core_no_BUS",
        "split": split,
        "rows": int(len(y_true)),
        "positive_rows": int(pd.Series(y_true).sum()),
        "threshold": float(threshold),
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


def train_tree_models(
    splits: dict[str, pd.DataFrame],
    numeric_features: list[str],
    categorical_features: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    features = numeric_features + categorical_features
    x_train = splits["train"][features]
    y_train = splits["train"][TARGET]
    x_val = splits["validation"][features]
    y_val = splits["validation"][TARGET]
    x_test = splits["test"][features]
    y_test = splits["test"][TARGET]

    models = {
        "random_forest_core_no_BUS": RandomForestClassifier(
            n_estimators=350,
            max_depth=9,
            min_samples_leaf=8,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        ),
        "xgboost_core_no_BUS": XGBClassifier(
            n_estimators=250,
            max_depth=3,
            learning_rate=0.04,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=42,
            n_jobs=1,
            scale_pos_weight=float((y_train == 0).sum() / max((y_train == 1).sum(), 1)),
        ),
    }

    metrics = []
    predictions = []
    importances = []
    confusion_rows = []

    for model_name, estimator in models.items():
        preprocessor = make_preprocessor(numeric_features, categorical_features, scale_numeric=False)
        pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("model", estimator)])
        pipeline.fit(x_train, y_train)

        val_score = pipeline.predict_proba(x_val)[:, 1]
        threshold = choose_threshold(y_val, val_score)
        feature_names = encoded_feature_names(preprocessor, numeric_features, categorical_features)

        for split_name, split_df, y_true, x_values in [
            ("train", splits["train"], y_train, x_train),
            ("validation", splits["validation"], y_val, x_val),
            ("test", splits["test"], y_test, x_test),
        ]:
            score = pipeline.predict_proba(x_values)[:, 1]
            metrics.append(metric_row(model_name, split_name, y_true, score, threshold))
            add_predictions(predictions, model_name, split_name, split_df, y_true, score, threshold)
            confusion_rows.append(confusion_dict(model_name, split_name, y_true, score, threshold))

        fitted = pipeline.named_steps["model"]
        if hasattr(fitted, "feature_importances_"):
            for feature, importance in zip(feature_names, fitted.feature_importances_):
                importances.append(
                    {
                        "model": model_name,
                        "feature_set": "core_no_BUS",
                        "feature": feature,
                        "importance": float(importance),
                    }
                )

    return (
        pd.DataFrame(metrics),
        pd.DataFrame(predictions),
        pd.DataFrame(confusion_rows),
        pd.DataFrame(importances),
    )


def build_dnn(input_dim: int) -> tf.keras.Model:
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(input_dim,)),
            tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dropout(0.25),
            tf.keras.layers.Dense(32, activation="relu"),
            tf.keras.layers.Dropout(0.20),
            tf.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="binary_crossentropy",
        metrics=[tf.keras.metrics.AUC(name="auc"), tf.keras.metrics.AUC(name="pr_auc", curve="PR")],
    )
    return model


def train_dnn_models(
    splits: dict[str, pd.DataFrame],
    numeric_features: list[str],
    categorical_features: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    features = numeric_features + categorical_features
    x_train = splits["train"][features]
    y_train = splits["train"][TARGET].astype(int)
    x_val = splits["validation"][features]
    y_val = splits["validation"][TARGET].astype(int)
    x_test = splits["test"][features]
    y_test = splits["test"][TARGET].astype(int)

    preprocessor = make_preprocessor(numeric_features, categorical_features, scale_numeric=True)
    x_train_t = preprocessor.fit_transform(x_train)
    x_val_t = preprocessor.transform(x_val)
    x_test_t = preprocessor.transform(x_test)
    if hasattr(x_train_t, "toarray"):
        x_train_t = x_train_t.toarray()
        x_val_t = x_val_t.toarray()
        x_test_t = x_test_t.toarray()

    classes = np.array([0, 1])
    weights = compute_class_weight(class_weight="balanced", classes=classes, y=y_train)
    class_weight = {int(cls): float(weight) for cls, weight in zip(classes, weights)}

    model_configs = {
        "dnn_no_class_weight_core_no_BUS": None,
        "dnn_class_weight_core_no_BUS": class_weight,
    }

    metrics = []
    predictions = []
    confusion_rows = []
    histories = []

    for model_name, weights_for_model in model_configs.items():
        set_reproducibility(42)
        model = build_dnn(x_train_t.shape[1])
        early_stop = tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=10,
            restore_best_weights=True,
        )
        history = model.fit(
            x_train_t,
            y_train.to_numpy(),
            validation_data=(x_val_t, y_val.to_numpy()),
            epochs=120,
            batch_size=128,
            callbacks=[early_stop],
            class_weight=weights_for_model,
            verbose=0,
        )
        for epoch, values in enumerate(history.history.get("loss", []), start=1):
            histories.append(
                {
                    "model": model_name,
                    "epoch": epoch,
                    "loss": values,
                    "val_loss": history.history.get("val_loss", [None] * len(history.history.get("loss", [])))[epoch - 1],
                    "auc": history.history.get("auc", [None] * len(history.history.get("loss", [])))[epoch - 1],
                    "val_auc": history.history.get("val_auc", [None] * len(history.history.get("loss", [])))[epoch - 1],
                    "pr_auc": history.history.get("pr_auc", [None] * len(history.history.get("loss", [])))[epoch - 1],
                    "val_pr_auc": history.history.get("val_pr_auc", [None] * len(history.history.get("loss", [])))[epoch - 1],
                }
            )

        val_score = model.predict(x_val_t, verbose=0).ravel()
        threshold = choose_threshold(y_val, val_score)

        for split_name, split_df, y_true, x_values in [
            ("train", splits["train"], y_train, x_train_t),
            ("validation", splits["validation"], y_val, x_val_t),
            ("test", splits["test"], y_test, x_test_t),
        ]:
            score = model.predict(x_values, verbose=0).ravel()
            metrics.append(metric_row(model_name, split_name, y_true, score, threshold))
            add_predictions(predictions, model_name, split_name, split_df, y_true, score, threshold)
            confusion_rows.append(confusion_dict(model_name, split_name, y_true, score, threshold))

    return (
        pd.DataFrame(metrics),
        pd.DataFrame(predictions),
        pd.DataFrame(confusion_rows),
        pd.DataFrame(histories),
    )


def add_predictions(
    rows: list[dict],
    model_name: str,
    split_name: str,
    split_df: pd.DataFrame,
    y_true: pd.Series,
    y_score: np.ndarray,
    threshold: float,
) -> None:
    for idx, (_, original) in enumerate(split_df.iterrows()):
        rows.append(
            {
                "model": model_name,
                "feature_set": "core_no_BUS",
                "split": split_name,
                "province": original["province"],
                "region": original["region"],
                "datetime": original["datetime"],
                "year": int(original["year"]),
                "week": int(original["week"]),
                "y_true": int(y_true.iloc[idx]),
                "y_score": float(y_score[idx]),
                "threshold": float(threshold),
                "y_pred": int(y_score[idx] >= threshold),
            }
        )


def confusion_dict(model_name: str, split_name: str, y_true: pd.Series, y_score: np.ndarray, threshold: float) -> dict:
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "model": model_name,
        "feature_set": "core_no_BUS",
        "split": split_name,
        "threshold": float(threshold),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }


def region_performance(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    test = predictions[predictions["split"] == "test"].copy()
    for (model, region), group in test.groupby(["model", "region"], dropna=False):
        rows.append(region_metric_row(model, "region", region, group))
    return pd.DataFrame(rows)


def region_metric_row(model: str, level: str, value: str, group: pd.DataFrame) -> dict:
    y_true = group["y_true"].astype(int)
    y_score = group["y_score"].astype(float)
    y_pred = group["y_pred"].astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "model": model,
        "level": level,
        "value": value,
        "rows": len(group),
        "positive_rows": int(y_true.sum()),
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


def error_cases(predictions: pd.DataFrame, error_type: str) -> pd.DataFrame:
    test = predictions[predictions["split"] == "test"].copy()
    if error_type == "false_positive":
        out = test[(test["y_true"] == 0) & (test["y_pred"] == 1)].copy()
    elif error_type == "false_negative":
        out = test[(test["y_true"] == 1) & (test["y_pred"] == 0)].copy()
    else:
        raise ValueError(error_type)
    return out.sort_values(["model", "region", "province", "datetime"])


def feature_manifest(numeric_features: list[str], categorical_features: list[str]) -> pd.DataFrame:
    rows = []
    for feature in numeric_features:
        rows.append(
            {
                "feature": feature,
                "feature_type": "numeric",
                "feature_set": "core_no_BUS",
                "included": True,
                "notes": "Corrected-label core epidemiological predictor; BUS excluded.",
            }
        )
    for feature in categorical_features:
        rows.append(
            {
                "feature": feature,
                "feature_type": "categorical_encoded",
                "feature_set": "core_no_BUS",
                "included": True,
                "notes": "Safely one-hot encoded metadata.",
            }
        )
    for feature in sorted(EXCLUDED_COLUMNS):
        rows.append(
            {
                "feature": feature,
                "feature_type": "excluded",
                "feature_set": "excluded",
                "included": False,
                "notes": "Excluded by Step 9.8 feature policy.",
            }
        )
    return pd.DataFrame(rows)


def old_metric_comparison(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    old_sources = [
        (OUTPUT_DIR / "controlled_feature_selection_metrics.csv", "old_label_controlled"),
        (OUTPUT_DIR / "classical_ml_baseline_metrics.csv", "old_label_classical"),
    ]
    updated_test = metrics[metrics["split"] == "test"].copy()
    for path, source in old_sources:
        if not path.exists():
            continue
        old = pd.read_csv(path)
        old = old[old["split"] == "test"].copy()
        for _, old_row in old.iterrows():
            old_model = str(old_row.get("model", ""))
            old_feature_set = str(old_row.get("feature_set", "core_only"))
            if source == "old_label_controlled" and old_feature_set != "core_only":
                continue
            candidate_map = {
                "controlled_dnn_class_weight": "dnn_class_weight_core_no_BUS",
                "controlled_xgboost": "xgboost_core_no_BUS",
                "random_forest": "random_forest_core_no_BUS",
                "xgboost": "xgboost_core_no_BUS",
            }
            updated_model = candidate_map.get(old_model)
            if updated_model is None:
                continue
            match = updated_test[updated_test["model"] == updated_model]
            if match.empty:
                continue
            new_row = match.iloc[0]
            rows.append(
                {
                    "old_source": source,
                    "old_model": old_model,
                    "updated_model": updated_model,
                    "old_feature_set": old_feature_set,
                    "old_label_f1": old_row.get("f1"),
                    "updated_label_f1": new_row.get("f1"),
                    "f1_delta_updated_minus_old": new_row.get("f1") - old_row.get("f1"),
                    "old_label_precision": old_row.get("precision"),
                    "updated_label_precision": new_row.get("precision"),
                    "old_label_recall": old_row.get("recall"),
                    "updated_label_recall": new_row.get("recall"),
                    "old_label_roc_auc": old_row.get("roc_auc"),
                    "updated_label_roc_auc": new_row.get("roc_auc"),
                    "old_label_pr_auc": old_row.get("pr_auc"),
                    "updated_label_pr_auc": new_row.get("pr_auc"),
                    "old_label_false_positive": old_row.get("false_positive"),
                    "updated_label_false_positive": new_row.get("false_positive"),
                    "old_label_false_negative": old_row.get("false_negative"),
                    "updated_label_false_negative": new_row.get("false_negative"),
                    "interpretation": "Old-label metric is methodology reference only, not final claim.",
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    set_reproducibility(42)
    OUTPUT_DIR.mkdir(exist_ok=True)

    df = load_dataset()
    numeric_features, categorical_features = feature_lists(df)
    splits = split_data(df)
    split_info = split_summary(df, splits)
    manifest = feature_manifest(numeric_features, categorical_features)

    tree_metrics, tree_predictions, tree_confusion, tree_importance = train_tree_models(
        splits,
        numeric_features,
        categorical_features,
    )
    dnn_metrics, dnn_predictions, dnn_confusion, dnn_history = train_dnn_models(
        splits,
        numeric_features,
        categorical_features,
    )

    metrics = pd.concat([tree_metrics, dnn_metrics], ignore_index=True)
    predictions = pd.concat([tree_predictions, dnn_predictions], ignore_index=True)
    confusion = pd.concat([tree_confusion, dnn_confusion], ignore_index=True)
    region_perf = region_performance(predictions)
    false_positives = error_cases(predictions, "false_positive")
    false_negatives = error_cases(predictions, "false_negative")
    old_comparison = old_metric_comparison(metrics)

    model_comparison = (
        metrics[metrics["split"] == "test"]
        .sort_values(["f1", "pr_auc", "roc_auc"], ascending=[False, False, False])
        .reset_index(drop=True)
    )

    outputs = {
        "updated_label_baseline_metrics.csv": metrics,
        "updated_label_model_comparison.csv": model_comparison,
        "updated_label_test_predictions.csv": predictions[predictions["split"] == "test"].copy(),
        "updated_label_confusion_matrix.csv": confusion,
        "updated_label_feature_importance.csv": tree_importance.sort_values(["model", "importance"], ascending=[True, False]),
        "updated_label_region_performance.csv": region_perf,
        "updated_label_false_positives.csv": false_positives,
        "updated_label_false_negatives.csv": false_negatives,
        "updated_label_split_summary.csv": split_info,
        "updated_label_feature_manifest.csv": manifest,
        "updated_label_old_vs_new_metric_comparison.csv": old_comparison,
        "updated_label_dnn_training_history.csv": dnn_history,
    }
    for filename, out_df in outputs.items():
        out_df.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 80)
    print("\n=== SPLIT SUMMARY ===")
    print(split_info.to_string(index=False))
    print("\n=== TEST MODEL COMPARISON ===")
    print(model_comparison.to_string(index=False))
    print("\n=== OLD VS UPDATED METRIC COMPARISON ===")
    print(old_comparison.to_string(index=False) if not old_comparison.empty else "No old comparison rows.")
    print("\n=== OUTPUT FILES ===")
    for filename in outputs:
        print(OUTPUT_DIR / filename)


if __name__ == "__main__":
    main()
