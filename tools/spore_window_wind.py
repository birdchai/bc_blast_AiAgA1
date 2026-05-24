from __future__ import annotations

import math

import pandas as pd

from tools.blast_model_v1 import compute_hourly_infection_features
from tools.spatial_epidemiology_v0 import angular_difference_degrees


def _circular_direction_features(df: pd.DataFrame, direction_col: str) -> pd.DataFrame:
    out = df.copy()
    valid = out[direction_col].between(0, 360, inclusive="left")
    radians = out[direction_col].where(valid).map(
        lambda value: math.radians(value) if pd.notna(value) else pd.NA
    )
    out["_dir_sin"] = radians.map(lambda value: math.sin(value) if pd.notna(value) else pd.NA)
    out["_dir_cos"] = radians.map(lambda value: math.cos(value) if pd.notna(value) else pd.NA)
    return out


def _direction_from_components(sin_value: float, cos_value: float):
    if pd.isna(sin_value) or pd.isna(cos_value):
        return pd.NA
    return math.degrees(math.atan2(sin_value, cos_value)) % 360


def compute_spore_window_wind_features(
    weather: pd.DataFrame,
    start_hour: int = 2,
    end_hour: int = 6,
    prefix: str = "spore_window",
) -> pd.DataFrame:
    """
    Aggregate biologically informed wind features during likely spore-release hours.

    The window is inclusive of both boundary hours. For example 02:00-06:00
    includes observations with hour 2, 3, 4, 5, and 6. Windows crossing
    midnight, such as 22:00-06:00, are supported.
    """
    hourly = compute_hourly_infection_features(weather)
    hourly["datetime"] = pd.to_datetime(hourly["datetime"], errors="coerce")
    hourly["hour"] = hourly["datetime"].dt.hour

    if start_hour <= end_hour:
        in_window = hourly["hour"].between(start_hour, end_hour, inclusive="both")
    else:
        in_window = (hourly["hour"] >= start_hour) | (hourly["hour"] <= end_hour)

    window = hourly.loc[in_window].copy()
    window = _circular_direction_features(window, "wdir")
    window = window.set_index("datetime")

    weekly = (
        window.groupby("province")
        .resample("W")
        .agg(
            {
                "wspd": "mean",
                "_dir_sin": "mean",
                "_dir_cos": "mean",
                "leaf_wet_hour": "sum",
                "humid_wind_hour": "sum",
                "hour": "size",
            }
        )
        .reset_index()
    )
    weekly.columns = [
        "province",
        "datetime",
        "wspd_mean",
        "wind_dir_sin_mean",
        "wind_dir_cos_mean",
        "leaf_wet_hours",
        "humid_wind_hours",
        "observed_hours",
    ]

    resultant = (
        weekly["wind_dir_sin_mean"] ** 2 + weekly["wind_dir_cos_mean"] ** 2
    ) ** 0.5

    weekly[f"{prefix}_mean_wind_speed"] = weekly["wspd_mean"]
    weekly[f"{prefix}_prevailing_wind_direction"] = weekly.apply(
        lambda row: _direction_from_components(
            row["wind_dir_sin_mean"],
            row["wind_dir_cos_mean"],
        ),
        axis=1,
    )
    weekly[f"{prefix}_wind_direction_variability"] = 1 - resultant
    weekly[f"{prefix}_leaf_wet_hours"] = weekly["leaf_wet_hours"]
    weekly[f"{prefix}_humid_wind_hours"] = weekly["humid_wind_hours"]
    weekly[f"{prefix}_observed_hours"] = weekly["observed_hours"]

    return weekly[
        [
            "province",
            "datetime",
            f"{prefix}_mean_wind_speed",
            f"{prefix}_prevailing_wind_direction",
            f"{prefix}_wind_direction_variability",
            f"{prefix}_leaf_wet_hours",
            f"{prefix}_humid_wind_hours",
            f"{prefix}_observed_hours",
        ]
    ]


def compute_spore_window_wind_aligned_neighbor_blast(
    weekly_spore_wind: pd.DataFrame,
    weekly_blast: pd.DataFrame,
    neighbors: pd.DataFrame,
    direction_col: str = "spore_window_prevailing_wind_direction",
    output_col: str = "spore_window_wind_aligned_neighbor_blast",
    alignment_tolerance_degrees: float = 45.0,
) -> pd.DataFrame:
    """Compute previous-week infected-neighbor alignment using spore-window wind."""
    required_wind = ["province", "datetime", direction_col]
    missing_wind = [col for col in required_wind if col not in weekly_spore_wind.columns]
    if missing_wind:
        raise ValueError(f"Missing spore-window wind columns: {missing_wind}")

    required_blast = ["province", "datetime", "blast_any"]
    missing_blast = [col for col in required_blast if col not in weekly_blast.columns]
    if missing_blast:
        raise ValueError(f"Missing weekly blast columns: {missing_blast}")

    required_neighbors = ["province", "neighbor_province", "bearing_neighbor_to_province"]
    missing_neighbors = [col for col in required_neighbors if col not in neighbors.columns]
    if missing_neighbors:
        raise ValueError(f"Missing neighbor bearing columns: {missing_neighbors}")

    target_wind = weekly_spore_wind[required_wind].copy()
    target_wind["datetime"] = pd.to_datetime(target_wind["datetime"], errors="coerce")

    previous_blast = weekly_blast[required_blast].copy()
    previous_blast["datetime"] = (
        pd.to_datetime(previous_blast["datetime"], errors="coerce") + pd.Timedelta(days=7)
    )
    previous_blast = previous_blast.rename(
        columns={
            "province": "neighbor_province",
            "blast_any": "neighbor_prevweek_blast",
        }
    )

    directional = target_wind.merge(
        neighbors[required_neighbors],
        on="province",
        how="left",
    )
    directional = directional.merge(
        previous_blast,
        on=["neighbor_province", "datetime"],
        how="left",
    )
    directional["neighbor_prevweek_blast"] = directional["neighbor_prevweek_blast"].fillna(0)

    directional["spore_window_wind_alignment_angle"] = directional.apply(
        lambda row: (
            angular_difference_degrees(
                row[direction_col],
                row["bearing_neighbor_to_province"],
            )
            if pd.notna(row[direction_col])
            and pd.notna(row["bearing_neighbor_to_province"])
            else pd.NA
        ),
        axis=1,
    )
    directional["spore_window_wind_aligned"] = (
        pd.to_numeric(directional["spore_window_wind_alignment_angle"], errors="coerce")
        <= alignment_tolerance_degrees
    )
    directional["_aligned_neighbor_blast"] = (
        directional["neighbor_prevweek_blast"]
        * directional["spore_window_wind_aligned"].astype(int)
    )

    weekly = (
        directional.groupby(["province", "datetime"])
        .agg(
            **{
                output_col: ("_aligned_neighbor_blast", "mean"),
                "spore_window_wind_aligned_neighbor_count": (
                    "spore_window_wind_aligned",
                    "sum",
                ),
                "spore_window_min_wind_alignment_angle": (
                    "spore_window_wind_alignment_angle",
                    "min",
                ),
                "spore_window_mean_wind_alignment_angle": (
                    "spore_window_wind_alignment_angle",
                    "mean",
                ),
            }
        )
        .reset_index()
    )

    return weekly
