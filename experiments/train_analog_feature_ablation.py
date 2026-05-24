from __future__ import annotations

import random
from pathlib import Path
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

import tensorflow as tf


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from experiments.analyze_province_similarity import (  # noqa: E402
    OUTPUT_DIR,
    TEST_YEAR,
    TRAIN_YEARS,
    VALIDATION_YEAR,
    build_analog_features,
    prepare_dataset,
)


TARGET = "blast_t_plus_1"

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
    + ["datetime", "year", "week", "label_source_available", "label_observed"]
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

ANALOG_HISTORY_FEATURES = [
    "analog_prevweek_blast",
    "analog_outbreak_frequency_train",
]
ANALOG_PRESSURE_FEATURES = [
    "analog_prevweek_risk",
    "analog_2w_pressure",
    "analog_leaf_wet_pressure",
    "analog_regional_leaf_wet_pressure",
    "analog_host_pressure",
]
GEOGRAPHIC_PRESSURE_FEATURES = [
    "neighbor_prevweek_blast",
    "neighbor_prevweek_risk",
    "regional_neighbor_pressure_2w",
    "regional_neighbor_pressure_3w",
    "regional_host_pressure",
    "spatial_host_weather_risk",
]


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


def safe_existing(df: pd.DataFrame, features: list[str]) -> list[str]:
    return [feature for feature in features if feature in df.columns and feature not in EXCLUDED_COLUMNS]


def load_augmented_dataset() -> pd.DataFrame:
    base = prepare_dataset()
    base = add_week_seasonality(base)
    top = pd.read_csv(OUTPUT_DIR / "province_top_analog_neighbors.csv")
    train = base[base["year"].isin(TRAIN_YEARS)].copy()
    analog = build_analog_features(base, top, train)

    analog_cols = [
        "province",
        "datetime",
        "year",
        "week",
        "analog_prevweek_blast",
        "analog_prevweek_risk",
        "analog_2w_pressure",
        "analog_host_pressure",
        "analog_leaf_wet_pressure",
        "analog_regional_leaf_wet_pressure",
        "analog_outbreak_frequency_train",
    ]
    out = base.merge(analog[analog_cols], on=["province", "datetime", "year", "week"], how="left")
    for col in CORE_NUMERIC_CANDIDATES + ANALOG_HISTORY_FEATURES + ANALOG_PRESSURE_FEATURES:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def feature_sets(df: pd.DataFrame) -> dict[str, dict[str, list[str] | str]]:
    core = safe_existing(df, CORE_NUMERIC_CANDIDATES)
    history = safe_existing(df, ANALOG_HISTORY_FEATURES)
    pressure = safe_existing(df, ANALOG_PRESSURE_FEATURES)
    geo = [feature for feature in GEOGRAPHIC_PRESSURE_FEATURES if feature in core]
    categorical = [col for col in CATEGORICAL_CANDIDATES if col in df.columns and col not in EXCLUDED_COLUMNS]

    return {
        "core_no_BUS": {
            "numeric": core,
            "categorical": categorical,
            "description": "Existing corrected-label core_no_BUS baseline including existing geographic/regional pressure features.",
        },
        "core_plus_analog_history": {
            "numeric": core + [f for f in history if f not in core],
            "categorical": categorical,
            "description": "Core plus similarity-weighted analog outbreak-history features.",
        },
        "core_plus_analog_pressure": {
            "numeric": core + [f for f in pressure if f not in core],
            "categorical": categorical,
            "description": "Core plus similarity-weighted analog risk, moisture, host, and pressure features.",
        },
        "core_plus_all_analog": {
            "numeric": core + [f for f in history + pressure if f not in core],
            "categorical": categorical,
            "description": "Core plus all analog history and pressure features.",
        },
        "core_plus_geographic_pressure_only": {
            "numeric": core,
            "categorical": categorical,
            "description": "Comparator only: under current policy, geographic/regional pressure already exists in core_no_BUS.",
        },
        "core_plus_analog_and_geographic": {
            "numeric": core + [f for f in history + pressure if f not in core],
            "categorical": categorical,
            "description": "Core already includes geographic pressure; this adds all analog features on top.",
        },
    }


def split_data(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    usable = df[df[TARGET].notna()].copy()
    usable[TARGET] = (pd.to_numeric(usable[TARGET], errors="coerce") > 0).astype(int)
    return {
        "train": usable[usable["year"].isin(TRAIN_YEARS)].copy(),
        "validation": usable[usable["year"] == VALIDATION_YEAR].copy(),
        "test": usable[usable["year"] == TEST_YEAR].copy(),
    }


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


def safe_roc_auc(y_true: pd.Series, y_score: np.ndarray) -> float | None:
    if pd.Series(y_true).nunique() < 2:
        return None
    return float(roc_auc_score(y_true, y_score))


def safe_pr_auc(y_true: pd.Series, y_score: np.ndarray) -> float | None:
    if pd.Series(y_true).nunique() < 2:
        return None
    return float(average_precision_score(y_true, y_score))


def metric_row(
    model: str,
    feature_set: str,
    split: str,
    y_true: pd.Series,
    y_score: np.ndarray,
    threshold: float,
) -> dict:
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "model": model,
        "feature_set": feature_set,
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


def add_predictions(
    rows: list[dict],
    model: str,
    feature_set: str,
    split_name: str,
    split_df: pd.DataFrame,
    y_true: pd.Series,
    y_score: np.ndarray,
    threshold: float,
) -> None:
    for idx, (_, row) in enumerate(split_df.iterrows()):
        rows.append(
            {
                "model": model,
                "feature_set": feature_set,
                "split": split_name,
                "province": row["province"],
                "region": row["region"],
                "datetime": row["datetime"],
                "year": int(row["year"]),
                "week": int(row["week"]),
                "y_true": int(y_true.iloc[idx]),
                "y_score": float(y_score[idx]),
                "threshold": float(threshold),
                "y_pred": int(y_score[idx] >= threshold),
            }
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
        metrics=[
            tf.keras.metrics.AUC(name="auc"),
            tf.keras.metrics.AUC(name="pr_auc", curve="PR"),
        ],
    )
    return model


def train_rf(
    feature_set: str,
    splits: dict[str, pd.DataFrame],
    numeric_features: list[str],
    categorical_features: list[str],
) -> tuple[list[dict], list[dict], list[dict]]:
    features = numeric_features + categorical_features
    x_train = splits["train"][features]
    y_train = splits["train"][TARGET].astype(int)
    x_val = splits["validation"][features]
    y_val = splits["validation"][TARGET].astype(int)

    preprocessor = make_preprocessor(numeric_features, categorical_features, scale_numeric=False)
    model = RandomForestClassifier(
        n_estimators=350,
        max_depth=9,
        min_samples_leaf=8,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])
    pipeline.fit(x_train, y_train)
    val_score = pipeline.predict_proba(x_val)[:, 1]
    threshold = choose_threshold(y_val, val_score)

    metrics = []
    predictions = []
    for split_name, split_df in splits.items():
        y_true = split_df[TARGET].astype(int)
        y_score = pipeline.predict_proba(split_df[features])[:, 1]
        metrics.append(metric_row("random_forest", feature_set, split_name, y_true, y_score, threshold))
        add_predictions(predictions, "random_forest", feature_set, split_name, split_df, y_true, y_score, threshold)

    feature_names = encoded_feature_names(preprocessor, numeric_features, categorical_features)
    importances = [
        {
            "model": "random_forest",
            "feature_set": feature_set,
            "feature": feature,
            "importance": float(importance),
            "is_analog_feature": feature.startswith("analog_"),
        }
        for feature, importance in zip(feature_names, pipeline.named_steps["model"].feature_importances_)
    ]
    return metrics, predictions, importances


def train_dnn(
    feature_set: str,
    splits: dict[str, pd.DataFrame],
    numeric_features: list[str],
    categorical_features: list[str],
) -> tuple[list[dict], list[dict]]:
    features = numeric_features + categorical_features
    x_train = splits["train"][features]
    y_train = splits["train"][TARGET].astype(int)
    x_val = splits["validation"][features]
    y_val = splits["validation"][TARGET].astype(int)

    preprocessor = make_preprocessor(numeric_features, categorical_features, scale_numeric=True)
    x_train_t = preprocessor.fit_transform(x_train)
    x_val_t = preprocessor.transform(x_val)
    if hasattr(x_train_t, "toarray"):
        x_train_t = x_train_t.toarray()
        x_val_t = x_val_t.toarray()

    set_reproducibility(42)
    model = build_dnn(x_train_t.shape[1])
    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=10,
        restore_best_weights=True,
    )
    model.fit(
        x_train_t,
        y_train.to_numpy(),
        validation_data=(x_val_t, y_val.to_numpy()),
        epochs=120,
        batch_size=128,
        callbacks=[early_stop],
        verbose=0,
    )

    val_score = model.predict(x_val_t, verbose=0).ravel()
    threshold = choose_threshold(y_val, val_score)

    metrics = []
    predictions = []
    for split_name, split_df in splits.items():
        y_true = split_df[TARGET].astype(int)
        x_values = preprocessor.transform(split_df[features])
        if hasattr(x_values, "toarray"):
            x_values = x_values.toarray()
        y_score = model.predict(x_values, verbose=0).ravel()
        metrics.append(metric_row("dnn_no_class_weight", feature_set, split_name, y_true, y_score, threshold))
        add_predictions(predictions, "dnn_no_class_weight", feature_set, split_name, split_df, y_true, y_score, threshold)

    return metrics, predictions


def region_performance(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    test = predictions[predictions["split"] == "test"].copy()
    for (model, feature_set, region), group in test.groupby(["model", "feature_set", "region"], dropna=False):
        y_true = group["y_true"].astype(int)
        y_score = group["y_score"].astype(float)
        y_pred = group["y_pred"].astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        rows.append(
            {
                "model": model,
                "feature_set": feature_set,
                "region": region,
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
        )
    return pd.DataFrame(rows)


def failure_cases(predictions: pd.DataFrame) -> pd.DataFrame:
    test = predictions[predictions["split"] == "test"].copy()
    fp = test[(test["y_true"] == 0) & (test["y_pred"] == 1)].copy()
    fp["error_type"] = "false_positive"
    fn = test[(test["y_true"] == 1) & (test["y_pred"] == 0)].copy()
    fn["error_type"] = "false_negative"
    return pd.concat([fp, fn], ignore_index=True).sort_values(
        ["model", "feature_set", "error_type", "region", "province", "datetime"]
    )


def feature_manifest(feature_set_defs: dict[str, dict[str, list[str] | str]]) -> pd.DataFrame:
    rows = []
    for name, definition in feature_set_defs.items():
        numeric = definition["numeric"]
        categorical = definition["categorical"]
        assert isinstance(numeric, list)
        assert isinstance(categorical, list)
        rows.append(
            {
                "feature_set": name,
                "feature": "__feature_set__",
                "feature_type": "definition",
                "included": True,
                "notes": definition["description"],
            }
        )
        for feature in numeric:
            rows.append(
                {
                    "feature_set": name,
                    "feature": feature,
                    "feature_type": "numeric",
                    "included": True,
                    "notes": "analog" if feature.startswith("analog_") else "core_no_BUS",
                }
            )
        for feature in categorical:
            rows.append(
                {
                    "feature_set": name,
                    "feature": feature,
                    "feature_type": "categorical_encoded",
                    "included": True,
                    "notes": "one-hot encoded",
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    set_reproducibility(42)
    df = load_augmented_dataset()
    splits = split_data(df)
    definitions = feature_sets(df)

    all_metrics: list[dict] = []
    all_predictions: list[dict] = []
    all_importances: list[dict] = []

    for feature_set, definition in definitions.items():
        numeric = definition["numeric"]
        categorical = definition["categorical"]
        assert isinstance(numeric, list)
        assert isinstance(categorical, list)
        print(f"Training {feature_set}: {len(numeric)} numeric + {len(categorical)} categorical")

        rf_metrics, rf_predictions, rf_importances = train_rf(
            feature_set,
            splits,
            numeric,
            categorical,
        )
        dnn_metrics, dnn_predictions = train_dnn(
            feature_set,
            splits,
            numeric,
            categorical,
        )

        all_metrics.extend(rf_metrics)
        all_predictions.extend(rf_predictions)
        all_importances.extend(rf_importances)
        all_metrics.extend(dnn_metrics)
        all_predictions.extend(dnn_predictions)

    metrics = pd.DataFrame(all_metrics)
    predictions = pd.DataFrame(all_predictions)
    importances = pd.DataFrame(all_importances)
    region = region_performance(predictions)
    failures = failure_cases(predictions)
    manifest = feature_manifest(definitions)

    comparison = (
        metrics[metrics["split"] == "test"]
        .sort_values(["f1", "pr_auc", "roc_auc"], ascending=[False, False, False])
        .reset_index(drop=True)
    )

    outputs = {
        "analog_ablation_metrics.csv": metrics,
        "analog_ablation_model_comparison.csv": comparison,
        "analog_ablation_region_performance.csv": region,
        "analog_ablation_feature_importance.csv": importances.sort_values(
            ["feature_set", "model", "importance"], ascending=[True, True, False]
        ),
        "analog_ablation_test_predictions.csv": predictions[predictions["split"] == "test"].copy(),
        "analog_ablation_failure_cases.csv": failures,
        "analog_ablation_feature_manifest.csv": manifest,
    }
    for filename, out_df in outputs.items():
        out_df.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 80)
    print("\n=== TEST COMPARISON ===")
    print(comparison.to_string(index=False))
    print("\n=== RF TOP ANALOG IMPORTANCES ===")
    print(
        importances[importances["is_analog_feature"]]
        .sort_values(["feature_set", "importance"], ascending=[True, False])
        .groupby("feature_set")
        .head(8)
        .to_string(index=False)
    )
    print("\n=== OUTPUT FILES ===")
    for filename in outputs:
        print(OUTPUT_DIR / filename)


if __name__ == "__main__":
    main()
