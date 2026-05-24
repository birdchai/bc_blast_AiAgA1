from __future__ import annotations

import glob
import math
import os

import pandas as pd


def load_province_centroids_from_pov(folder_path: str) -> pd.DataFrame:
    """Build province centroid table from POV latitude/longitude columns."""
    files = glob.glob(os.path.join(folder_path, "**", "*.csv"), recursive=True)

    rows = []
    for file_path in files:
        try:
            df = pd.read_csv(
                file_path,
                encoding="cp874",
                usecols=["address", "latitude", "longitude"],
                low_memory=False,
            )
            df = df.rename(columns={"address": "province"})
            df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
            df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
            df = df.dropna(subset=["province", "latitude", "longitude"])
            rows.append(df)
        except Exception as exc:
            print(f"Failed to read centroid data from {file_path}: {exc}")

    if not rows:
        raise ValueError("No POV centroid data could be loaded.")

    combined = pd.concat(rows, ignore_index=True)
    centroids = (
        combined.groupby("province")
        .agg(latitude=("latitude", "mean"), longitude=("longitude", "mean"))
        .reset_index()
    )

    return centroids


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers."""
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return radius_km * c


def bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from point 1 to point 2 in degrees clockwise from north."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    x = math.sin(delta_lambda) * math.cos(phi2)
    y = (
        math.cos(phi1) * math.sin(phi2)
        - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    )

    return (math.degrees(math.atan2(x, y)) + 360) % 360


def angular_difference_degrees(direction_a: float, direction_b: float) -> float:
    """Smallest absolute difference between two compass directions."""
    return abs((direction_a - direction_b + 180) % 360 - 180)


def compute_province_distances(centroids: pd.DataFrame) -> pd.DataFrame:
    """Compute all province-to-province distances from centroid coordinates."""
    required = ["province", "latitude", "longitude"]
    missing = [col for col in required if col not in centroids.columns]
    if missing:
        raise ValueError(f"Missing centroid columns: {missing}")

    rows = []
    records = centroids[required].dropna().to_dict("records")
    for src in records:
        for dst in records:
            if src["province"] == dst["province"]:
                continue
            rows.append(
                {
                    "province": src["province"],
                    "neighbor_province": dst["province"],
                    "distance_km": haversine_km(
                        src["latitude"],
                        src["longitude"],
                        dst["latitude"],
                        dst["longitude"],
                    ),
                    "bearing_neighbor_to_province": bearing_degrees(
                        dst["latitude"],
                        dst["longitude"],
                        src["latitude"],
                        src["longitude"],
                    ),
                }
            )

    return pd.DataFrame(rows).sort_values(["province", "distance_km"])


def top_nearest_neighbors(distances: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """Select top N nearest neighboring provinces for each province."""
    required = ["province", "neighbor_province", "distance_km"]
    missing = [col for col in required if col not in distances.columns]
    if missing:
        raise ValueError(f"Missing distance columns: {missing}")

    return (
        distances.sort_values(["province", "distance_km"])
        .groupby("province")
        .head(top_n)
        .reset_index(drop=True)
    )


def compute_wind_aligned_neighbor_blast(
    weekly_risk: pd.DataFrame,
    weekly_blast: pd.DataFrame,
    neighbors: pd.DataFrame,
    alignment_tolerance_degrees: float = 45.0,
) -> pd.DataFrame:
    """
    Estimate previous-week infected-neighbor pressure aligned with target wind.

    The bearing is from neighbor province to target province. If the target's
    prevailing wind direction is close to that bearing, the infected neighbor is
    considered directionally aligned. This is exploratory association only.
    """
    required_risk = ["province", "datetime", "prevailing_wind_direction"]
    missing_risk = [col for col in required_risk if col not in weekly_risk.columns]
    if missing_risk:
        raise ValueError(f"Missing weekly risk columns: {missing_risk}")

    required_blast = ["province", "datetime", "blast_any"]
    missing_blast = [col for col in required_blast if col not in weekly_blast.columns]
    if missing_blast:
        raise ValueError(f"Missing weekly blast columns: {missing_blast}")

    required_neighbors = ["province", "neighbor_province", "bearing_neighbor_to_province"]
    missing_neighbors = [col for col in required_neighbors if col not in neighbors.columns]
    if missing_neighbors:
        raise ValueError(f"Missing neighbor bearing columns: {missing_neighbors}")

    target_wind = weekly_risk[required_risk].copy()
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

    directional["wind_alignment_angle"] = directional.apply(
        lambda row: (
            angular_difference_degrees(
                row["prevailing_wind_direction"],
                row["bearing_neighbor_to_province"],
            )
            if pd.notna(row["prevailing_wind_direction"])
            and pd.notna(row["bearing_neighbor_to_province"])
            else pd.NA
        ),
        axis=1,
    )
    directional["wind_aligned"] = (
        pd.to_numeric(directional["wind_alignment_angle"], errors="coerce")
        <= alignment_tolerance_degrees
    )
    directional["aligned_neighbor_blast"] = (
        directional["neighbor_prevweek_blast"] * directional["wind_aligned"].astype(int)
    )

    weekly = (
        directional.groupby(["province", "datetime"])
        .agg(
            wind_aligned_neighbor_blast=("aligned_neighbor_blast", "mean"),
            wind_aligned_neighbor_count=("wind_aligned", "sum"),
            wind_neighbor_count=("neighbor_province", "nunique"),
            min_wind_alignment_angle=("wind_alignment_angle", "min"),
            mean_wind_alignment_angle=("wind_alignment_angle", "mean"),
        )
        .reset_index()
    )

    return weekly


def compute_weekly_neighbor_pressure(
    weekly_risk: pd.DataFrame,
    weekly_blast: pd.DataFrame,
    neighbors: pd.DataFrame,
    risk_col: str = "host_weighted_risk",
) -> pd.DataFrame:
    """
    Compute previous-week mean neighbor risk and blast pressure.

    neighbor_prevweek_risk is the average previous-week risk among each
    province's top-N nearest neighbors. neighbor_prevweek_blast is the previous
    week's mean binary blast occurrence among those same neighbors.
    """
    required_risk = ["province", "datetime", risk_col]
    missing_risk = [col for col in required_risk if col not in weekly_risk.columns]
    if missing_risk:
        raise ValueError(f"Missing weekly risk columns: {missing_risk}")

    required_blast = ["province", "datetime", "blast_any"]
    missing_blast = [col for col in required_blast if col not in weekly_blast.columns]
    if missing_blast:
        raise ValueError(f"Missing weekly blast columns: {missing_blast}")

    required_neighbors = ["province", "neighbor_province"]
    missing_neighbors = [col for col in required_neighbors if col not in neighbors.columns]
    if missing_neighbors:
        raise ValueError(f"Missing neighbor columns: {missing_neighbors}")

    risk = weekly_risk[required_risk].copy()
    risk["datetime"] = pd.to_datetime(risk["datetime"], errors="coerce") + pd.Timedelta(days=7)
    risk = risk.rename(
        columns={
            "province": "neighbor_province",
            risk_col: "neighbor_prevweek_risk",
        }
    )

    blast = weekly_blast[required_blast].copy()
    blast["datetime"] = pd.to_datetime(blast["datetime"], errors="coerce") + pd.Timedelta(days=7)
    blast = blast.rename(
        columns={
            "province": "neighbor_province",
            "blast_any": "neighbor_prevweek_blast",
        }
    )

    neighbor_weeks = neighbors[["province", "neighbor_province"]].merge(
        risk,
        on="neighbor_province",
        how="left",
    )
    neighbor_weeks = neighbor_weeks.merge(
        blast,
        on=["neighbor_province", "datetime"],
        how="left",
    )

    pressure = (
        neighbor_weeks.groupby(["province", "datetime"])
        .agg(
            neighbor_prevweek_risk=("neighbor_prevweek_risk", "mean"),
            neighbor_prevweek_blast=("neighbor_prevweek_blast", "mean"),
            neighbor_count=("neighbor_province", "nunique"),
        )
        .reset_index()
    )

    return pressure


def add_spatial_host_weather_score(
    weekly_host_risk: pd.DataFrame,
    neighbor_pressure: pd.DataFrame,
    host_col: str = "host_weighted_risk",
    neighbor_col: str = "neighbor_prevweek_risk",
    output_col: str = "spatial_host_weather_risk",
) -> pd.DataFrame:
    """Join spatial pressure and create conservative 70/30 combined score."""
    required = ["province", "datetime", host_col]
    missing = [col for col in required if col not in weekly_host_risk.columns]
    if missing:
        raise ValueError(f"Missing host risk columns: {missing}")

    pressure_required = ["province", "datetime", neighbor_col, "neighbor_prevweek_blast"]
    pressure_missing = [col for col in pressure_required if col not in neighbor_pressure.columns]
    if pressure_missing:
        raise ValueError(f"Missing neighbor pressure columns: {pressure_missing}")

    out = weekly_host_risk.merge(
        neighbor_pressure,
        on=["province", "datetime"],
        how="left",
    )
    out[neighbor_col] = out[neighbor_col].fillna(out[host_col])
    out["neighbor_prevweek_blast"] = out["neighbor_prevweek_blast"].fillna(0)
    out["neighbor_count"] = out["neighbor_count"].fillna(0)
    out[output_col] = (0.7 * out[host_col]) + (0.3 * out[neighbor_col])

    return out
