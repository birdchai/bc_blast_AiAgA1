from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.blast_model_v1 import weather_to_weekly_risk
from tools.data_loader import load_weather_data
from tools.region_mapping import add_region
from tools.spatial_epidemiology_v0 import (
    add_spatial_host_weather_score,
    compute_province_distances,
    compute_weekly_neighbor_pressure,
    compute_wind_aligned_neighbor_blast,
    haversine_km,
    load_province_centroids_from_pov,
    top_nearest_neighbors,
)
from tools.susceptibility_v0 import add_host_weighted_scores, compute_weekly_susceptibility
from tools.temporal_epidemiology_v0 import (
    add_region_aware_temporal_features,
    add_week_metadata,
)
from tools.time_utils import parse_datetime
from tools.updated_data_loaders import (
    BUS_CRITICAL_THRESHOLD,
    bus_to_weekly_features,
    load_bus_daily,
    load_updated_blast_outbreak_weekly,
    load_updated_pov_monthly,
    updated_pov_to_weekly_variety_ratio,
)


OUTPUT_DIR = BASE_DIR / "experiments" / "outputs"
UPDATED_DIR = BASE_DIR / "updated data"
YEARS = list(range(2015, 2022))

SEQUENCE_COLUMNS = [
    "province",
    "region",
    "datetime",
    "year",
    "week",
    "label_source_available",
    "label_observed",
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
    "bus_feature_available",
    "bus_observed_days",
    "avgbus_mean",
    "avgbus_max",
    "maxbus_max",
    "bus_critical_days",
    "bus_critical_any",
    "bus_critical_ratio",
    "blast_any",
    "blast_days",
    "blast_area",
    "blast_t_plus_1",
    "blast_t_plus_2",
]


def compute_future_labels_preserve_missing(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().sort_values(["province", "datetime"])
    out["blast_t_plus_1"] = out.groupby("province")["blast_any"].shift(-1)
    out["blast_t_plus_2"] = out.groupby("province")["blast_any"].shift(-2)
    return out


def assign_bus_to_nearest_province(bus_weekly: pd.DataFrame, centroids: pd.DataFrame) -> pd.DataFrame:
    required = ["location", "latitude", "longitude"]
    missing = [col for col in required if col not in bus_weekly.columns]
    if missing:
        raise ValueError(f"BUS weekly missing columns: {missing}")

    centroid_records = centroids[["province", "latitude", "longitude"]].dropna().to_dict("records")
    location_coords = (
        bus_weekly[["location", "latitude", "longitude"]]
        .dropna()
        .drop_duplicates("location")
        .to_dict("records")
    )

    location_rows = []
    for loc in location_coords:
        nearest = min(
            centroid_records,
            key=lambda p: haversine_km(
                float(loc["latitude"]),
                float(loc["longitude"]),
                float(p["latitude"]),
                float(p["longitude"]),
            ),
        )
        distance = haversine_km(
            float(loc["latitude"]),
            float(loc["longitude"]),
            float(nearest["latitude"]),
            float(nearest["longitude"]),
        )
        location_rows.append(
            {
                "location": loc["location"],
                "province": nearest["province"],
                "bus_to_province_distance_km": distance,
            }
        )

    location_map = pd.DataFrame(location_rows)
    bus = bus_weekly.merge(location_map, on="location", how="left")
    province_week = (
        bus.groupby(["province", "datetime"], dropna=False)
        .agg(
            bus_feature_available=("location", "nunique"),
            bus_observed_days=("bus_observed_days", "sum"),
            avgbus_mean=("avgbus_mean", "mean"),
            avgbus_max=("avgbus_max", "max"),
            maxbus_max=("maxbus_max", "max"),
            minbus_min=("minbus_min", "min"),
            bus_critical_days=("bus_critical_days", "sum"),
            bus_critical_any=("bus_critical_any", "max"),
            bus_critical_ratio=("bus_critical_ratio", "mean"),
            bus_to_province_distance_km=("bus_to_province_distance_km", "mean"),
        )
        .reset_index()
    )
    return province_week


def prepare_updated_sources() -> dict[str, pd.DataFrame]:
    print("Loading updated POV monthly...")
    pov_monthly = load_updated_pov_monthly(UPDATED_DIR / "pov_rice_monthly")
    weekly_pov = updated_pov_to_weekly_variety_ratio(pov_monthly)
    weekly_susceptibility = compute_weekly_susceptibility(weekly_pov)

    print("Loading updated outbreak labels...")
    weekly_blast = load_updated_blast_outbreak_weekly(UPDATED_DIR / "rice_blast_outbreak_weekly")

    print("Loading BUS daily and creating weekly province features...")
    bus_root = UPDATED_DIR / "bus_value_daily"
    if not bus_root.exists():
        bus_root = UPDATED_DIR / "bus_value_dayly"
    bus_daily = load_bus_daily(bus_root)
    bus_weekly = bus_to_weekly_features(bus_daily)

    print("Computing province centroids and neighbors...")
    centroids = load_province_centroids_from_pov(str(UPDATED_DIR / "pov_rice_monthly"))
    distances = compute_province_distances(centroids)
    neighbors = top_nearest_neighbors(distances, top_n=5)
    bus_province_week = assign_bus_to_nearest_province(bus_weekly, centroids)

    return {
        "pov_monthly": pov_monthly,
        "weekly_pov": weekly_pov,
        "weekly_susceptibility": weekly_susceptibility,
        "weekly_blast": weekly_blast,
        "bus_weekly": bus_weekly,
        "bus_province_week": bus_province_week,
        "centroids": centroids,
        "neighbors": neighbors,
    }


def build_year_sequence(year: int, sources: dict[str, pd.DataFrame]) -> pd.DataFrame:
    weather_folder = UPDATED_DIR / "weather_hourly" / f"Weather_Data_Blast_24H_{year}"
    weather = load_weather_data(str(weather_folder))
    weather = parse_datetime(weather, "datetime")
    weekly_risk = weather_to_weekly_risk(weather)

    weekly_susceptibility = sources["weekly_susceptibility"]
    weekly_susceptibility = weekly_susceptibility[
        weekly_susceptibility["datetime"].dt.year == year
    ].copy()
    weekly_host = add_host_weighted_scores(weekly_risk, weekly_susceptibility)

    all_blast = sources["weekly_blast"].copy()
    source_years = set(all_blast["source_year"].dropna().astype(int).unique())
    source_available = year in source_years
    year_blast = all_blast[all_blast["source_year"] == year].copy()

    if source_available:
        blast_for_spatial = weekly_risk[["province", "datetime"]].merge(
            year_blast[["province", "datetime", "blast_any", "blast_days", "blast_area"]],
            on=["province", "datetime"],
            how="left",
        )
        blast_for_spatial["label_observed"] = blast_for_spatial["blast_any"].notna().astype(int)
        blast_for_spatial["blast_any"] = blast_for_spatial["blast_any"].fillna(0).astype(int)
        blast_for_spatial["blast_days"] = blast_for_spatial["blast_days"].fillna(0)
        blast_for_spatial["blast_area"] = blast_for_spatial["blast_area"].fillna(0)
    else:
        blast_for_spatial = weekly_risk[["province", "datetime"]].copy()
        blast_for_spatial["blast_any"] = pd.NA
        blast_for_spatial["blast_days"] = pd.NA
        blast_for_spatial["blast_area"] = pd.NA
        blast_for_spatial["label_observed"] = 0

    spatial_label = blast_for_spatial[["province", "datetime", "blast_any"]].copy()
    spatial_label["blast_any"] = spatial_label["blast_any"].fillna(0).astype(int)

    neighbor_pressure = compute_weekly_neighbor_pressure(
        weekly_host,
        spatial_label,
        sources["neighbors"],
        risk_col="host_weighted_risk",
    )
    weekly_spatial = add_spatial_host_weather_score(
        weekly_host,
        neighbor_pressure,
        host_col="host_weighted_risk",
        neighbor_col="neighbor_prevweek_risk",
        output_col="spatial_host_weather_risk",
    )
    directional = compute_wind_aligned_neighbor_blast(
        weekly_spatial,
        spatial_label,
        sources["neighbors"],
        alignment_tolerance_degrees=45.0,
    )

    weekly = weekly_spatial.merge(directional, on=["province", "datetime"], how="left")
    for col in ["wind_aligned_neighbor_blast", "wind_aligned_neighbor_count"]:
        weekly[col] = weekly[col].fillna(0)

    weekly = weekly.merge(
        blast_for_spatial[
            [
                "province",
                "datetime",
                "blast_any",
                "blast_days",
                "blast_area",
                "label_observed",
            ]
        ],
        on=["province", "datetime"],
        how="left",
    )
    weekly["label_source_available"] = int(source_available)

    bus = sources["bus_province_week"]
    bus_year = bus[bus["datetime"].dt.year == year].copy()
    weekly = weekly.merge(bus_year, on=["province", "datetime"], how="left")
    weekly["bus_feature_available"] = weekly["bus_feature_available"].fillna(0).astype(int)
    for col in [
        "bus_observed_days",
        "bus_critical_days",
        "bus_critical_any",
        "bus_critical_ratio",
    ]:
        if col in weekly.columns:
            weekly[col] = weekly[col].fillna(0)

    weekly = add_region(weekly)
    weekly = add_region_aware_temporal_features(weekly)
    weekly = compute_future_labels_preserve_missing(weekly)
    weekly = add_week_metadata(weekly)
    weekly["year"] = year
    return weekly


def summarize_sequence(sequences: pd.DataFrame) -> pd.DataFrame:
    return (
        sequences.groupby("year", dropna=False)
        .agg(
            rows=("province", "count"),
            provinces=("province", "nunique"),
            regions=("region", "nunique"),
            label_source_available=("label_source_available", "max"),
            label_observed_rows=("label_observed", "sum"),
            blast_positive=("blast_any", lambda s: int(pd.to_numeric(s, errors="coerce").fillna(0).sum())),
            blast_t_plus_1_positive=("blast_t_plus_1", lambda s: int(pd.to_numeric(s, errors="coerce").fillna(0).sum())),
            blast_t_plus_2_positive=("blast_t_plus_2", lambda s: int(pd.to_numeric(s, errors="coerce").fillna(0).sum())),
            bus_feature_rows=("bus_feature_available", "sum"),
        )
        .reset_index()
        .sort_values("year")
    )


def label_distribution(sequences: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for group_cols in [["year"], ["region"], ["year", "region"]]:
        grouped = sequences.groupby(group_cols, dropna=False)
        for keys, group in grouped:
            if not isinstance(keys, tuple):
                keys = (keys,)
            row = {"grouping": "+".join(group_cols)}
            row.update({col: value for col, value in zip(group_cols, keys)})
            target = pd.to_numeric(group["blast_any"], errors="coerce")
            row.update(
                {
                    "rows": len(group),
                    "known_label_rows": int(target.notna().sum()),
                    "positive_rows": int(target.fillna(0).sum()),
                    "positive_rate": float(target.mean()) if target.notna().any() else None,
                    "blast_t_plus_1_positive": int(pd.to_numeric(group["blast_t_plus_1"], errors="coerce").fillna(0).sum()),
                    "blast_t_plus_2_positive": int(pd.to_numeric(group["blast_t_plus_2"], errors="coerce").fillna(0).sum()),
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def feature_integrity(sequences: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in sequences.columns:
        series = sequences[col]
        row = {
            "column": col,
            "dtype": str(series.dtype),
            "missing_count": int(series.isna().sum()),
            "missing_rate": float(series.isna().mean()),
            "unique_count": int(series.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(series):
            numeric = pd.to_numeric(series, errors="coerce")
            finite = np.isfinite(numeric.dropna())
            row.update(
                {
                    "infinite_count": int((~np.isfinite(numeric) & numeric.notna()).sum()),
                    "is_constant": bool(numeric.nunique(dropna=True) <= 1),
                    "min": float(numeric.min()) if numeric.notna().any() else None,
                    "max": float(numeric.max()) if numeric.notna().any() else None,
                    "mean": float(numeric.mean()) if numeric.notna().any() else None,
                    "finite_count": int(finite.sum()),
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


def pov_ratio_summary(pov_monthly: pd.DataFrame) -> pd.DataFrame:
    return (
        pov_monthly.groupby(["year", "season", "variety"], dropna=False)
        .agg(
            province_month_rows=("province", "count"),
            provinces=("province", "nunique"),
            total_area=("area", "sum"),
            mean_ratio=("ratio", "mean"),
            max_ratio=("ratio", "max"),
        )
        .reset_index()
        .sort_values(["year", "season", "total_area"], ascending=[True, True, False])
    )


def susceptibility_summary(weekly_susceptibility: pd.DataFrame) -> pd.DataFrame:
    out = weekly_susceptibility.copy()
    out["year"] = out["datetime"].dt.year
    return (
        out.groupby("year", dropna=False)
        .agg(
            rows=("province", "count"),
            provinces=("province", "nunique"),
            mean_susceptibility=("susceptibility_score", "mean"),
            min_susceptibility=("susceptibility_score", "min"),
            max_susceptibility=("susceptibility_score", "max"),
            mean_pov_area=("total_pov_area", "mean"),
            mean_variety_count=("pov_variety_count", "mean"),
        )
        .reset_index()
        .sort_values("year")
    )


def bus_feature_summary(sequences: pd.DataFrame) -> pd.DataFrame:
    return (
        sequences.groupby("year", dropna=False)
        .agg(
            rows=("province", "count"),
            bus_feature_rows=("bus_feature_available", "sum"),
            provinces_with_bus=("province", lambda s: sequences.loc[s.index].query("bus_feature_available > 0")["province"].nunique()),
            mean_avgbus=("avgbus_mean", "mean"),
            max_avgbus=("avgbus_max", "max"),
            bus_critical_weeks=("bus_critical_any", "sum"),
            mean_bus_critical_ratio=("bus_critical_ratio", "mean"),
        )
        .reset_index()
        .sort_values("year")
    )


def old_new_label_comparison_with_region() -> pd.DataFrame:
    path = OUTPUT_DIR / "updated_vs_old_blast_label_comparison.csv"
    if not path.exists():
        return pd.DataFrame()
    comparison = pd.read_csv(path)
    if "label_agree" not in comparison.columns:
        comparison["label_agree"] = comparison["blast_any_old"] == comparison["blast_any_updated"]
    comparison = add_region(comparison)
    region = (
        comparison.groupby(["year", "region"], dropna=False)
        .agg(
            rows=("province", "count"),
            old_positive=("blast_any_old", "sum"),
            updated_positive=("blast_any_updated", "sum"),
            disagreements=("label_agree", lambda s: int((~s).sum())),
            old_positive_updated_negative=("old_positive_updated_negative", "sum"),
            old_negative_updated_positive=("old_negative_updated_positive", "sum"),
        )
        .reset_index()
    )
    province = (
        comparison.groupby(["year", "region", "province"], dropna=False)
        .agg(
            rows=("datetime", "count"),
            old_positive=("blast_any_old", "sum"),
            updated_positive=("blast_any_updated", "sum"),
            disagreements=("label_agree", lambda s: int((~s).sum())),
            old_positive_updated_negative=("old_positive_updated_negative", "sum"),
            old_negative_updated_positive=("old_negative_updated_positive", "sum"),
        )
        .reset_index()
    )
    region["level"] = "region"
    province["level"] = "province"
    return pd.concat([region, province], ignore_index=True, sort=False)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    OUTPUT_DIR.mkdir(exist_ok=True)

    sources = prepare_updated_sources()

    frames = []
    for year in YEARS:
        print(f"\n=== BUILD UPDATED SEQUENCE {year} ===")
        sequence = build_year_sequence(year, sources)
        frames.append(sequence)
        print(
            {
                "year": year,
                "rows": len(sequence),
                "provinces": sequence["province"].nunique(),
                "positives": int(pd.to_numeric(sequence["blast_any"], errors="coerce").fillna(0).sum()),
                "bus_rows": int(sequence["bus_feature_available"].sum()),
            }
        )

    sequences = pd.concat(frames, ignore_index=True)
    sequences = sequences[[col for col in SEQUENCE_COLUMNS if col in sequences.columns]].copy()

    outputs = {
        "region_temporal_sequence_dataset_updated_labels_2015_2021.csv": sequences,
        "updated_sequence_dataset_summary.csv": summarize_sequence(sequences),
        "updated_label_distribution_summary.csv": label_distribution(sequences),
        "updated_feature_integrity_summary.csv": feature_integrity(sequences),
        "updated_old_vs_new_label_comparison.csv": old_new_label_comparison_with_region(),
        "updated_pov_variety_ratio_summary.csv": pov_ratio_summary(sources["pov_monthly"]),
        "updated_susceptibility_summary.csv": susceptibility_summary(sources["weekly_susceptibility"]),
        "updated_bus_feature_summary.csv": bus_feature_summary(sequences),
    }
    for filename, df in outputs.items():
        df.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 80)
    print("\n=== UPDATED SEQUENCE SUMMARY ===")
    print(outputs["updated_sequence_dataset_summary.csv"].to_string(index=False))
    print("\n=== UPDATED BUS FEATURE SUMMARY ===")
    print(outputs["updated_bus_feature_summary.csv"].to_string(index=False))
    print("\n=== OUTPUT FILES ===")
    for filename in outputs:
        print(OUTPUT_DIR / filename)


if __name__ == "__main__":
    main()
