from __future__ import annotations

import glob
import math
import os
import re
from pathlib import Path

import pandas as pd


WEATHER_COLUMNS = ["province", "datetime", "temperature", "humidity", "rainfall"]
OPTIONAL_WEATHER_COLUMNS = ["wspd", "wgust", "wdir", "dew", "cloudcover", "sealevelpressure"]
HIGH_WIND_SPEED_THRESHOLD = 10.0


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def compute_hourly_infection_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Baseline BUS-like hourly infection conditions.

    The weights intentionally prioritize humidity and favorable temperature.
    Rainfall is treated as a secondary moisture signal because it can be
    missing or less directly related to leaf wetness than relative humidity.
    """
    _require_columns(df, WEATHER_COLUMNS)

    out = df.copy()
    out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce")

    for col in ["temperature", "humidity", "rainfall"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    for col in OPTIONAL_WEATHER_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out.dropna(subset=["province", "datetime", "temperature", "humidity"])
    out["rainfall"] = out["rainfall"].fillna(0)
    out["wspd_filled"] = out["wspd"].fillna(0)

    out["temp_favorable"] = out["temperature"].between(20, 32, inclusive="both")
    out["temp_optimal"] = out["temperature"].between(24, 28, inclusive="both")
    out["humidity_favorable"] = out["humidity"] >= 85
    out["humidity_optimal"] = out["humidity"] >= 90
    out["rainfall_event"] = out["rainfall"] > 0

    out["favorable_hour"] = out["temp_favorable"] & out["humidity_favorable"]
    out["optimal_hour"] = out["temp_optimal"] & out["humidity_optimal"]
    out["leaf_wet_hour"] = out["temp_favorable"] & out["humidity_optimal"]
    out["high_wind_hour"] = out["wspd_filled"] >= HIGH_WIND_SPEED_THRESHOLD
    out["humid_wind_hour"] = out["humidity_favorable"] & (out["wspd_filled"] > 0)
    out["leaf_wet_wind_hour"] = out["leaf_wet_hour"] & (out["wspd_filled"] > 0)

    valid_wdir = out["wdir"].between(0, 360, inclusive="left")
    wdir_radians = out["wdir"].where(valid_wdir).map(
        lambda value: math.radians(value) if pd.notna(value) else pd.NA
    )
    out["wind_dir_sin"] = wdir_radians.map(lambda value: math.sin(value) if pd.notna(value) else pd.NA)
    out["wind_dir_cos"] = wdir_radians.map(lambda value: math.cos(value) if pd.notna(value) else pd.NA)

    out["hourly_risk_points"] = (
        out["temp_favorable"].astype(int)
        + out["temp_optimal"].astype(int)
        + (2 * out["humidity_favorable"].astype(int))
        + (2 * out["humidity_optimal"].astype(int))
        + out["rainfall_event"].astype(int)
    )

    return out


def weather_to_weekly_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert hourly weather into province-week risk features.

    Output uses the same weekly timestamp convention as pandas resample("W"):
    each datetime is the week-ending Sunday.
    """
    hourly = compute_hourly_infection_features(df)
    hourly = hourly.set_index("datetime")

    weekly = (
        hourly.groupby("province")
        .resample("W")
        .agg(
            {
                "temperature": ["mean", "size"],
                "humidity": "mean",
                "rainfall": "sum",
                "favorable_hour": "sum",
                "optimal_hour": "sum",
                "humidity_favorable": "sum",
                "humidity_optimal": "sum",
                "rainfall_event": "sum",
                "leaf_wet_hour": "sum",
                "wspd": ["mean", "max"],
                "wgust": "mean",
                "wind_dir_sin": "mean",
                "wind_dir_cos": "mean",
                "high_wind_hour": "sum",
                "humid_wind_hour": "sum",
                "leaf_wet_wind_hour": "sum",
                "dew": "mean",
                "cloudcover": "mean",
                "sealevelpressure": "mean",
                "hourly_risk_points": "mean",
            }
        )
        .reset_index()
    )

    weekly.columns = [
        "province",
        "datetime",
        "temperature_mean",
        "observed_hours",
        "humidity_mean",
        "rainfall_sum",
        "favorable_hours",
        "optimal_hours",
        "humidity_favorable_hours",
        "humidity_optimal_hours",
        "rainfall_hours",
        "leaf_wet_hours",
        "mean_wind_speed",
        "max_wind_speed",
        "mean_wind_gust",
        "mean_wind_dir_sin",
        "mean_wind_dir_cos",
        "high_wind_hours",
        "humid_wind_hours",
        "leaf_wet_wind_hours",
        "dew_mean",
        "cloudcover_mean",
        "sealevelpressure_mean",
        "hourly_risk_mean",
    ]

    weekly["infection_ratio"] = weekly["favorable_hours"] / weekly["observed_hours"]
    weekly["optimal_ratio"] = weekly["optimal_hours"] / weekly["observed_hours"]
    weekly["humidity_ratio"] = weekly["humidity_optimal_hours"] / weekly["observed_hours"]
    weekly["rainfall_ratio"] = weekly["rainfall_hours"] / weekly["observed_hours"]
    weekly["leaf_wet_ratio"] = weekly["leaf_wet_hours"] / weekly["observed_hours"]
    weekly["high_wind_ratio"] = weekly["high_wind_hours"] / weekly["observed_hours"]
    weekly["humid_wind_ratio"] = weekly["humid_wind_hours"] / weekly["observed_hours"]
    weekly["leaf_wet_wind_ratio"] = weekly["leaf_wet_wind_hours"] / weekly["observed_hours"]

    resultant = (
        (weekly["mean_wind_dir_sin"] ** 2 + weekly["mean_wind_dir_cos"] ** 2) ** 0.5
    )
    direction = weekly.apply(
        lambda row: (
            math.degrees(math.atan2(row["mean_wind_dir_sin"], row["mean_wind_dir_cos"])) % 360
            if pd.notna(row["mean_wind_dir_sin"]) and pd.notna(row["mean_wind_dir_cos"])
            else pd.NA
        ),
        axis=1,
    )
    weekly["prevailing_wind_direction"] = direction
    weekly["wind_direction_variability"] = 1 - resultant

    weekly["risk_score"] = (
        55 * weekly["infection_ratio"]
        + 25 * weekly["optimal_ratio"]
        + 15 * weekly["humidity_ratio"]
        + 5 * weekly["rainfall_ratio"]
    ).clip(0, 100)

    weekly["risk_level"] = pd.cut(
        weekly["risk_score"],
        bins=[-0.01, 25, 60, 100],
        labels=["Low", "Moderate", "High"],
    ).astype(str)

    return add_temporal_accumulation_features(weekly)


def add_temporal_accumulation_features(weekly: pd.DataFrame) -> pd.DataFrame:
    """Add rolling cumulative risk and infection-hour features by province."""
    _require_columns(
        weekly,
        [
            "province",
            "datetime",
            "risk_score",
            "favorable_hours",
            "optimal_hours",
            "leaf_wet_hours",
        ],
    )

    out = weekly.copy().sort_values(["province", "datetime"])
    grouped = out.groupby("province", group_keys=False)

    for window in [2, 3]:
        out[f"rolling_{window}w_risk"] = grouped["risk_score"].transform(
            lambda s: s.rolling(window, min_periods=1).sum()
        )
        out[f"rolling_{window}w_risk_mean"] = grouped["risk_score"].transform(
            lambda s: s.rolling(window, min_periods=1).mean()
        )
        out[f"rolling_{window}w_infection_hours"] = grouped["favorable_hours"].transform(
            lambda s: s.rolling(window, min_periods=1).sum()
        )
        out[f"rolling_{window}w_optimal_hours"] = grouped["optimal_hours"].transform(
            lambda s: s.rolling(window, min_periods=1).sum()
        )
        out[f"rolling_{window}w_leaf_wet_hours"] = grouped["leaf_wet_hours"].transform(
            lambda s: s.rolling(window, min_periods=1).sum()
        )

    return out


def _infer_blast_province(file_path: str) -> str:
    name = Path(file_path).stem
    return re.sub(r"\s+Blast_\d{4}$", "", name).strip()


def load_blast_data(folder_path: str) -> pd.DataFrame:
    """Load daily blast CSV files and attach province/year from file paths."""
    files = glob.glob(os.path.join(folder_path, "**", "*.csv"), recursive=True)

    dfs = []
    for file_path in files:
        try:
            df = pd.read_csv(file_path, encoding="cp874", low_memory=False)
            _require_columns(df, ["datetime", "blast"])
            df = df[["datetime", "blast"]].copy()
            df["province"] = _infer_blast_province(file_path)
            df["source_file"] = os.path.basename(file_path)
            dfs.append(df)
        except Exception as exc:
            print(f"Failed to read {file_path}: {exc}")

    if not dfs:
        raise ValueError("No blast CSV files could be loaded.")

    combined = pd.concat(dfs, ignore_index=True)
    combined["datetime"] = pd.to_datetime(combined["datetime"], errors="coerce")
    combined["blast"] = pd.to_numeric(combined["blast"], errors="coerce").fillna(0)
    combined["blast"] = (combined["blast"] > 0).astype(int)
    combined = combined.dropna(subset=["province", "datetime"])

    return combined


def blast_to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily blast occurrence into province-week labels."""
    _require_columns(df, ["province", "datetime", "blast"])

    out = df.copy()
    out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce")
    out["blast"] = pd.to_numeric(out["blast"], errors="coerce").fillna(0)
    out = out.dropna(subset=["province", "datetime"])
    out["blast"] = (out["blast"] > 0).astype(int)
    out = out.set_index("datetime")

    weekly = (
        out.groupby("province")
        .resample("W")
        .agg({"blast": ["max", "sum", "size"]})
        .reset_index()
    )
    weekly.columns = ["province", "datetime", "blast_any", "blast_days", "observed_days"]

    return weekly


def join_weekly_risk_with_blast(
    weekly_risk: pd.DataFrame,
    weekly_blast: pd.DataFrame,
    risk_lag_weeks: int = 0,
) -> pd.DataFrame:
    """
    Join weekly risk with weekly disease labels.

    risk_lag_weeks=1 compares this week's disease with last week's risk.
    """
    _require_columns(weekly_risk, ["province", "datetime", "risk_score"])
    _require_columns(weekly_blast, ["province", "datetime", "blast_any"])

    risk = weekly_risk.copy().sort_values(["province", "datetime"])
    if risk_lag_weeks:
        risk_feature_cols = [col for col in risk.columns if col not in ["province", "datetime"]]
        risk[risk_feature_cols] = risk.groupby("province")[risk_feature_cols].shift(risk_lag_weeks)

    joined = weekly_blast.merge(
        risk,
        on=["province", "datetime"],
        how="inner",
        suffixes=("_blast", "_risk"),
    )

    return joined.dropna(subset=["risk_score", "blast_any"])


def validate_weekly_risk(
    joined: pd.DataFrame,
    threshold: float = 60,
    risk_score_col: str = "risk_score",
) -> dict:
    """Compute lightweight validation metrics without extra ML dependencies."""
    _require_columns(joined, [risk_score_col, "blast_any"])

    if joined.empty:
        raise ValueError("Joined validation dataset is empty.")

    df = joined.copy()
    df["predicted_positive"] = df[risk_score_col] >= threshold
    df["actual_positive"] = df["blast_any"] > 0

    tp = int((df["predicted_positive"] & df["actual_positive"]).sum())
    fp = int((df["predicted_positive"] & ~df["actual_positive"]).sum())
    fn = int((~df["predicted_positive"] & df["actual_positive"]).sum())
    tn = int((~df["predicted_positive"] & ~df["actual_positive"]).sum())

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0

    diseased = df.loc[df["actual_positive"], risk_score_col]
    non_diseased = df.loc[~df["actual_positive"], risk_score_col]

    correlation = df[risk_score_col].corr(df["blast_any"])

    return {
        "rows": int(len(df)),
        "disease_weeks": int(df["actual_positive"].sum()),
        "risk_score_col": risk_score_col,
        "threshold": threshold,
        "mean_risk_disease_weeks": float(diseased.mean()) if len(diseased) else None,
        "mean_risk_no_disease_weeks": float(non_diseased.mean()) if len(non_diseased) else None,
        "risk_blast_correlation": float(correlation) if pd.notna(correlation) else None,
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def threshold_sweep(
    joined: pd.DataFrame,
    thresholds: list[float],
    risk_score_col: str = "risk_score",
) -> pd.DataFrame:
    """Evaluate one joined risk/blast dataset across multiple thresholds."""
    rows = []
    for threshold in thresholds:
        rows.append(
            validate_weekly_risk(
                joined,
                threshold=threshold,
                risk_score_col=risk_score_col,
            )
        )

    return pd.DataFrame(rows)


def lag_threshold_sweep(
    weekly_risk: pd.DataFrame,
    weekly_blast: pd.DataFrame,
    lags: list[int],
    thresholds: list[float],
    risk_score_col: str = "risk_score",
) -> pd.DataFrame:
    """Evaluate multiple risk lags and thresholds without changing the model."""
    rows = []
    for lag in lags:
        joined = join_weekly_risk_with_blast(
            weekly_risk,
            weekly_blast,
            risk_lag_weeks=lag,
        )
        sweep = threshold_sweep(
            joined,
            thresholds,
            risk_score_col=risk_score_col,
        )
        sweep.insert(0, "lag_weeks", lag)
        rows.append(sweep)

    if not rows:
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True)
