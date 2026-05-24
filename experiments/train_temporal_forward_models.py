from __future__ import annotations

from pathlib import Path
import random
import sys

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
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

import tensorflow as tf

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

DATASET_PATH = BASE_DIR / "experiments" / "outputs" / "region_temporal_sequence_dataset_updated_labels_2015_2022.csv"
OUTPUT_DIR = BASE_DIR / "experiments" / "outputs"
TARGET = "blast_t_plus_1"

TRAIN_YEARS = [2017, 2018, 2019, 2020]
VALIDATION_YEARS = [2021]
TEST_YEARS = [2022]
SEQUENCE_LENGTHS = [2, 4]

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
    for col in CORE_NUMERIC_CANDIDATES + TARGET_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def safe_existing(df: pd.DataFrame, features: list[str]) -> list[str]:
    return [feature for feature in features if feature in df.columns and feature not in EXCLUDED_COLUMNS]


def feature_lists(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    numeric = safe_existing(df, CORE_NUMERIC_CANDIDATES)
    categorical = [col for col in CATEGORICAL_CANDIDATES if col in df.columns and col not in EXCLUDED_COLUMNS]
    return numeric, categorical


def build_preprocessor(numeric_features: list[str], categorical_features: list[str]) -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
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


def to_dense(matrix) -> np.ndarray:
    if hasattr(matrix, "toarray"):
        return matrix.toarray().astype("float32")
    return np.asarray(matrix).astype("float32")


def fit_transform(df: pd.DataFrame, numeric_features: list[str], categorical_features: list[str]) -> tuple[pd.DataFrame, np.ndarray]:
    features = numeric_features + categorical_features
    usable = df[df[TARGET].notna()].copy()
    usable[TARGET] = (pd.to_numeric(usable[TARGET], errors="coerce") > 0).astype(int)
    train_mask = usable["year"].isin(TRAIN_YEARS)
    preprocessor = build_preprocessor(numeric_features, categorical_features)
    preprocessor.fit(usable.loc[train_mask, features])
    transformed = to_dense(preprocessor.transform(usable[features]))
    metadata = usable[["province", "region", "datetime", "year", "week", TARGET]].copy()
    metadata["_feature_index"] = range(len(metadata))
    return metadata, transformed


def create_sequences(
    metadata: pd.DataFrame,
    transformed_features: np.ndarray,
    sequence_length: int,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], pd.DataFrame]:
    arrays: dict[str, list[np.ndarray]] = {"train": [], "validation": [], "test": []}
    current_arrays: dict[str, list[np.ndarray]] = {"train": [], "validation": [], "test": []}
    targets: dict[str, list[int]] = {"train": [], "validation": [], "test": []}
    manifest_rows = []

    split_by_year = {
        **{year: "train" for year in TRAIN_YEARS},
        **{year: "validation" for year in VALIDATION_YEARS},
        **{year: "test" for year in TEST_YEARS},
    }

    data = metadata.copy()
    data["datetime"] = pd.to_datetime(data["datetime"], errors="coerce")
    data = data.sort_values(["province", "year", "datetime", "week"])

    for (province, year), group in data.groupby(["province", "year"], sort=False):
        split_name = split_by_year.get(int(year))
        if split_name is None:
            continue
        group = group.sort_values(["datetime", "week"]).reset_index(drop=True)
        for end_pos in range(sequence_length - 1, len(group)):
            target = group.loc[end_pos, TARGET]
            if pd.isna(target):
                continue
            window = group.iloc[end_pos - sequence_length + 1 : end_pos + 1]
            feature_indices = window["_feature_index"].to_numpy()
            sequence = transformed_features[feature_indices]
            arrays[split_name].append(sequence)
            current_arrays[split_name].append(sequence[-1])
            targets[split_name].append(int(target > 0))
            manifest_rows.append(
                {
                    "split": split_name,
                    "province": province,
                    "region": group.loc[end_pos, "region"],
                    "year": int(year),
                    "start_datetime": window.iloc[0]["datetime"],
                    "end_datetime": group.loc[end_pos, "datetime"],
                    "start_week": int(window.iloc[0]["week"]),
                    "end_week": int(group.loc[end_pos, "week"]),
                    "sequence_length": sequence_length,
                    "target": int(target > 0),
                }
            )

    feature_dim = transformed_features.shape[1]
    sequence_arrays = {
        split: np.stack(values).astype("float32") if values else np.empty((0, sequence_length, feature_dim), dtype="float32")
        for split, values in arrays.items()
    }
    current_feature_arrays = {
        split: np.stack(values).astype("float32") if values else np.empty((0, feature_dim), dtype="float32")
        for split, values in current_arrays.items()
    }
    target_arrays = {split: np.asarray(values).astype("int32") for split, values in targets.items()}
    return sequence_arrays, current_feature_arrays, target_arrays, pd.DataFrame(manifest_rows)


def build_gru(input_shape: tuple[int, int]) -> tf.keras.Model:
    inputs = tf.keras.layers.Input(shape=input_shape)
    x = tf.keras.layers.GRU(32, dropout=0.20)(inputs)
    x = tf.keras.layers.Dense(16, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.20)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)
    return compile_model(tf.keras.Model(inputs, outputs))


def tcn_block(inputs: tf.keras.layers.Layer) -> tf.keras.layers.Layer:
    x = tf.keras.layers.Conv1D(32, kernel_size=2, padding="causal", dilation_rate=1, activation="relu")(inputs)
    x = tf.keras.layers.Dropout(0.15)(x)
    x = tf.keras.layers.Conv1D(32, kernel_size=2, padding="causal", dilation_rate=2, activation="relu")(x)
    x = tf.keras.layers.GlobalAveragePooling1D()(x)
    return x


def build_tcn(input_shape: tuple[int, int]) -> tf.keras.Model:
    inputs = tf.keras.layers.Input(shape=input_shape)
    x = tcn_block(inputs)
    x = tf.keras.layers.Dense(16, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.20)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)
    return compile_model(tf.keras.Model(inputs, outputs))


def build_hybrid_gru(input_shape: tuple[int, int], current_dim: int) -> tf.keras.Model:
    seq_input = tf.keras.layers.Input(shape=input_shape, name="sequence_input")
    current_input = tf.keras.layers.Input(shape=(current_dim,), name="current_input")
    seq = tf.keras.layers.GRU(32, dropout=0.20)(seq_input)
    cur = tf.keras.layers.Dense(32, activation="relu")(current_input)
    merged = tf.keras.layers.Concatenate()([seq, cur])
    x = tf.keras.layers.Dense(24, activation="relu")(merged)
    x = tf.keras.layers.Dropout(0.20)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)
    return compile_model(tf.keras.Model([seq_input, current_input], outputs))


def build_hybrid_tcn(input_shape: tuple[int, int], current_dim: int) -> tf.keras.Model:
    seq_input = tf.keras.layers.Input(shape=input_shape, name="sequence_input")
    current_input = tf.keras.layers.Input(shape=(current_dim,), name="current_input")
    seq = tcn_block(seq_input)
    cur = tf.keras.layers.Dense(32, activation="relu")(current_input)
    merged = tf.keras.layers.Concatenate()([seq, cur])
    x = tf.keras.layers.Dense(24, activation="relu")(merged)
    x = tf.keras.layers.Dropout(0.20)(x)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)
    return compile_model(tf.keras.Model([seq_input, current_input], outputs))


def compile_model(model: tf.keras.Model) -> tf.keras.Model:
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss="binary_crossentropy",
        metrics=[
            tf.keras.metrics.AUC(name="roc_auc"),
            tf.keras.metrics.AUC(curve="PR", name="pr_auc"),
        ],
    )
    return model


def class_weight_dict(y_train: np.ndarray) -> dict[int, float]:
    classes = np.array([0, 1])
    weights = compute_class_weight("balanced", classes=classes, y=y_train)
    return {int(label): float(weight) for label, weight in zip(classes, weights)}


def choose_threshold(y_true: np.ndarray, y_score: np.ndarray) -> float:
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


def safe_roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, y_score))


def safe_pr_auc(y_true: np.ndarray, y_score: np.ndarray) -> float | None:
    if len(np.unique(y_true)) < 2:
        return None
    return float(average_precision_score(y_true, y_score))


def metric_row(
    model_name: str,
    sequence_length: int,
    split: str,
    y_true: np.ndarray,
    y_score: np.ndarray,
    threshold: float,
) -> dict:
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "model": model_name,
        "sequence_length": sequence_length,
        "feature_set": "core_no_BUS",
        "split": split,
        "rows": int(len(y_true)),
        "positive_rows": int((y_true == 1).sum()),
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


def train_one_model(
    model_name: str,
    sequence_length: int,
    model: tf.keras.Model,
    sequences: dict[str, np.ndarray],
    current_features: dict[str, np.ndarray],
    targets: dict[str, np.ndarray],
    manifest: pd.DataFrame,
) -> tuple[list[dict], list[dict], list[dict]]:
    is_hybrid = model_name.startswith("hybrid")
    train_x = [sequences["train"], current_features["train"]] if is_hybrid else sequences["train"]
    val_x = [sequences["validation"], current_features["validation"]] if is_hybrid else sequences["validation"]
    test_x = [sequences["test"], current_features["test"]] if is_hybrid else sequences["test"]

    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor="val_pr_auc",
        mode="max",
        patience=8,
        restore_best_weights=True,
    )
    history = model.fit(
        train_x,
        targets["train"],
        validation_data=(val_x, targets["validation"]),
        epochs=80,
        batch_size=128,
        class_weight=class_weight_dict(targets["train"]),
        callbacks=[early_stop],
        verbose=0,
    )

    val_score = model.predict(val_x, verbose=0).ravel()
    threshold = choose_threshold(targets["validation"], val_score)

    metrics = []
    predictions = []
    histories = []
    for epoch, loss in enumerate(history.history.get("loss", []), start=1):
        histories.append(
            {
                "model": model_name,
                "sequence_length": sequence_length,
                "epoch": epoch,
                "loss": loss,
                "val_loss": history.history.get("val_loss", [None])[epoch - 1],
                "roc_auc": history.history.get("roc_auc", [None])[epoch - 1],
                "val_roc_auc": history.history.get("val_roc_auc", [None])[epoch - 1],
                "pr_auc": history.history.get("pr_auc", [None])[epoch - 1],
                "val_pr_auc": history.history.get("val_pr_auc", [None])[epoch - 1],
            }
        )

    split_inputs = {
        "train": train_x,
        "validation": val_x,
        "test": test_x,
    }
    for split, x_values in split_inputs.items():
        score = model.predict(x_values, verbose=0).ravel()
        metrics.append(metric_row(model_name, sequence_length, split, targets[split], score, threshold))
        split_manifest = manifest[manifest["split"] == split].reset_index(drop=True)
        for idx, row in split_manifest.iterrows():
            predictions.append(
                {
                    "model": model_name,
                    "sequence_length": sequence_length,
                    "feature_set": "core_no_BUS",
                    "split": split,
                    "province": row["province"],
                    "region": row["region"],
                    "year": int(row["year"]),
                    "end_datetime": row["end_datetime"],
                    "end_week": int(row["end_week"]),
                    "y_true": int(targets[split][idx]),
                    "y_score": float(score[idx]),
                    "threshold": threshold,
                    "y_pred": int(score[idx] >= threshold),
                }
            )
    return metrics, predictions, histories


def region_performance(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    test = predictions[predictions["split"] == "test"].copy()
    for (model, sequence_length, region), group in test.groupby(["model", "sequence_length", "region"], dropna=False):
        y_true = group["y_true"].astype(int)
        y_score = group["y_score"].astype(float)
        y_pred = group["y_pred"].astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        rows.append(
            {
                "model": model,
                "sequence_length": sequence_length,
                "region": region,
                "rows": len(group),
                "positive_rows": int(y_true.sum()),
                "precision": precision_score(y_true, y_pred, zero_division=0),
                "recall": recall_score(y_true, y_pred, zero_division=0),
                "f1": f1_score(y_true, y_pred, zero_division=0),
                "roc_auc": safe_roc_auc(y_true.to_numpy(), y_score.to_numpy()),
                "pr_auc": safe_pr_auc(y_true.to_numpy(), y_score.to_numpy()),
                "true_negative": int(tn),
                "false_positive": int(fp),
                "false_negative": int(fn),
                "true_positive": int(tp),
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
    metadata, transformed = fit_transform(df, numeric_features, categorical_features)

    all_metrics = []
    all_predictions = []
    all_histories = []
    manifest_rows = []

    for sequence_length in SEQUENCE_LENGTHS:
        sequences, current_features, targets, manifest = create_sequences(metadata, transformed, sequence_length)
        input_shape = (sequence_length, transformed.shape[1])
        current_dim = transformed.shape[1]
        model_builders = {
            "gru": lambda: build_gru(input_shape),
            "tcn": lambda: build_tcn(input_shape),
            "hybrid_dnn_gru": lambda: build_hybrid_gru(input_shape, current_dim),
            "hybrid_dnn_tcn": lambda: build_hybrid_tcn(input_shape, current_dim),
        }
        for split in ["train", "validation", "test"]:
            manifest_rows.append(
                {
                    "sequence_length": sequence_length,
                    "split": split,
                    "rows": int(len(targets[split])),
                    "positive_rows": int((targets[split] == 1).sum()),
                    "feature_dim": int(transformed.shape[1]),
                    "numeric_feature_count": len(numeric_features),
                    "categorical_feature_count": len(categorical_features),
                    "numeric_features": "|".join(numeric_features),
                    "categorical_features": "|".join(categorical_features),
                }
            )

        for model_name, builder in model_builders.items():
            set_reproducibility(42)
            model = builder()
            metrics, predictions, histories = train_one_model(
                model_name,
                sequence_length,
                model,
                sequences,
                current_features,
                targets,
                manifest,
            )
            all_metrics.extend(metrics)
            all_predictions.extend(predictions)
            all_histories.extend(histories)

    metrics_df = pd.DataFrame(all_metrics)
    predictions_df = pd.DataFrame(all_predictions)
    history_df = pd.DataFrame(all_histories)
    manifest_df = pd.DataFrame(manifest_rows)
    region_df = region_performance(predictions_df)

    outputs = {
        "temporal_model_forward_metrics.csv": metrics_df,
        "temporal_model_forward_all_predictions.csv": predictions_df,
        "temporal_model_forward_predictions.csv": predictions_df[predictions_df["split"] == "test"].copy(),
        "temporal_model_forward_region_performance.csv": region_df,
        "temporal_model_forward_training_history.csv": history_df,
        "temporal_model_forward_manifest.csv": manifest_df,
    }
    for filename, out_df in outputs.items():
        out_df.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 80)
    print("\n=== TEMPORAL TEST METRICS ===")
    print(
        metrics_df[metrics_df["split"] == "test"]
        .sort_values(["f1", "pr_auc"], ascending=[False, False])
        .to_string(index=False)
    )
    print("\n=== OUTPUT FILES ===")
    for filename in outputs:
        print(OUTPUT_DIR / filename)


if __name__ == "__main__":
    main()
