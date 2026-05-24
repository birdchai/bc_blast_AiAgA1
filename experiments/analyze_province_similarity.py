from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "experiments" / "outputs"
DATASET_PATH = OUTPUT_DIR / "region_temporal_sequence_dataset_updated_labels_2015_2022.csv"
CENTROIDS_PATH = OUTPUT_DIR / "province_centroids_from_pov.csv"
DISTANCES_PATH = OUTPUT_DIR / "province_distances.csv"

TRAIN_YEARS = [2017, 2018, 2019, 2020]
VALIDATION_YEAR = 2021
TEST_YEAR = 2022


WEATHER_FEATURES = [
    "temperature_mean",
    "humidity_mean",
    "rainfall_sum",
    "leaf_wet_hours",
    "leaf_wet_ratio",
    "regional_leaf_wet_accumulation",
    "spore_window_leaf_wet_hours",
]

HOST_FEATURES = [
    "susceptibility_score",
    "host_weighted_risk",
    "host_weighted_rolling_2w",
    "host_weighted_rolling_3w",
    "total_pov_area",
    "pov_variety_count",
]

PRESSURE_FEATURES = [
    "neighbor_prevweek_blast",
    "neighbor_prevweek_risk",
    "regional_neighbor_pressure_2w",
    "regional_neighbor_pressure_3w",
    "regional_host_pressure",
    "regional_wind_alignment_frequency",
    "wind_aligned_neighbor_blast",
]


def existing_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    return [col for col in columns if col in df.columns]


def prepare_dataset() -> pd.DataFrame:
    df = pd.read_csv(DATASET_PATH, low_memory=False)
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["week"] = pd.to_numeric(df["week"], errors="coerce")
    df["month"] = df["datetime"].dt.month

    for col in ["blast_any", "blast_t_plus_1", "risk_score", "host_weighted_risk"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.dropna(subset=["province", "datetime", "year"]).copy()


def aggregate_profile(train: pd.DataFrame, columns: list[str], prefix: str) -> pd.DataFrame:
    cols = existing_columns(train, columns)
    if not cols:
        return train[["province"]].drop_duplicates().reset_index(drop=True)

    numeric = train[["province"] + cols].copy()
    for col in cols:
        numeric[col] = pd.to_numeric(numeric[col], errors="coerce")

    mean = numeric.groupby("province")[cols].mean().add_prefix(f"{prefix}_mean_")
    std = numeric.groupby("province")[cols].std(ddof=0).add_prefix(f"{prefix}_std_")
    profile = pd.concat([mean, std], axis=1).reset_index()
    return profile


def outbreak_profile(train: pd.DataFrame) -> pd.DataFrame:
    base = train[["province", "blast_any", "blast_t_plus_1", "month", "week"]].copy()
    base["blast_any"] = pd.to_numeric(base["blast_any"], errors="coerce").fillna(0)
    base["blast_t_plus_1"] = pd.to_numeric(base["blast_t_plus_1"], errors="coerce").fillna(0)

    summary = (
        base.groupby("province")
        .agg(
            outbreak_history_blast_any_frequency=("blast_any", "mean"),
            outbreak_history_tplus1_frequency=("blast_t_plus_1", "mean"),
            outbreak_history_positive_weeks=("blast_any", "sum"),
            outbreak_history_rows=("blast_any", "count"),
        )
        .reset_index()
    )

    monthly = (
        base.pivot_table(
            index="province",
            columns="month",
            values="blast_t_plus_1",
            aggfunc="mean",
            fill_value=0,
        )
        .rename(columns=lambda month: f"outbreak_history_month_{int(month):02d}")
        .reset_index()
    )

    week_bins = pd.cut(
        base["week"],
        bins=[0, 13, 26, 39, 54],
        labels=["q1", "q2", "q3", "q4"],
        include_lowest=True,
    )
    base = base.assign(week_quarter=week_bins)
    seasonal = (
        base.pivot_table(
            index="province",
            columns="week_quarter",
            values="blast_t_plus_1",
            aggfunc="mean",
            fill_value=0,
            observed=False,
        )
        .rename(columns=lambda q: f"outbreak_history_week_{q}")
        .reset_index()
    )

    return summary.merge(monthly, on="province", how="left").merge(
        seasonal, on="province", how="left"
    )


def matrix_from_profile(profile: pd.DataFrame, name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    provinces = profile["province"].astype(str).tolist()
    feature_cols = [col for col in profile.columns if col != "province"]

    if not feature_cols:
        identity = pd.DataFrame(np.eye(len(provinces)), index=provinces, columns=provinces)
        return identity, pd.DataFrame({"feature_group": name, "feature": []})

    x = profile[feature_cols].apply(pd.to_numeric, errors="coerce")
    x = SimpleImputer(strategy="median").fit_transform(x)
    x = StandardScaler().fit_transform(x)

    cos = cosine_similarity(x)
    dist = euclidean_distances(x)
    euclidean_sim = 1 / (1 + dist)
    sim = (cos + 1) / 2
    combined = (sim + euclidean_sim) / 2
    np.fill_diagonal(combined, 1.0)

    matrix = pd.DataFrame(combined, index=provinces, columns=provinces)
    manifest = pd.DataFrame({"feature_group": name, "feature": feature_cols})
    return matrix, manifest


def save_similarity_matrix(matrix: pd.DataFrame, path: Path) -> None:
    matrix.rename_axis("province").reset_index().to_csv(path, index=False)


def combine_matrices(matrices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    names = list(matrices)
    base = matrices[names[0]].copy()
    total = np.zeros(base.shape, dtype=float)
    count = np.zeros(base.shape, dtype=float)

    for matrix in matrices.values():
        aligned = matrix.reindex(index=base.index, columns=base.columns)
        values = aligned.to_numpy(dtype=float)
        mask = np.isfinite(values)
        total[mask] += values[mask]
        count[mask] += 1

    combined = np.divide(total, count, out=np.zeros_like(total), where=count > 0)
    np.fill_diagonal(combined, 1.0)
    return pd.DataFrame(combined, index=base.index, columns=base.columns)


def load_geographic_distances() -> pd.DataFrame:
    if DISTANCES_PATH.exists():
        return pd.read_csv(DISTANCES_PATH)

    if not CENTROIDS_PATH.exists():
        return pd.DataFrame(columns=["province", "neighbor_province", "distance_km"])

    centroids = pd.read_csv(CENTROIDS_PATH)
    rows = []
    for src in centroids.to_dict("records"):
        for dst in centroids.to_dict("records"):
            if src["province"] == dst["province"]:
                continue
            rows.append(
                {
                    "province": src["province"],
                    "neighbor_province": dst["province"],
                    "distance_km": haversine_km(
                        src["latitude"], src["longitude"], dst["latitude"], dst["longitude"]
                    ),
                }
            )
    return pd.DataFrame(rows).sort_values(["province", "distance_km"])


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def top_analogs(
    combined: pd.DataFrame,
    group_matrices: dict[str, pd.DataFrame],
    regions: pd.DataFrame,
    distances: pd.DataFrame,
    top_n: int = 5,
) -> pd.DataFrame:
    distance_lookup = distances.set_index(["province", "neighbor_province"])["distance_km"]
    region_lookup = regions.set_index("province")["region"].to_dict()

    rows = []
    for province in combined.index:
        scores = combined.loc[province].drop(index=province).sort_values(ascending=False)
        for rank, (analog, score) in enumerate(scores.head(top_n).items(), start=1):
            row = {
                "province": province,
                "analog_province": analog,
                "analog_rank": rank,
                "combined_similarity": score,
                "province_region": region_lookup.get(province, "Unknown"),
                "analog_region": region_lookup.get(analog, "Unknown"),
                "same_region": region_lookup.get(province) == region_lookup.get(analog),
                "distance_km": distance_lookup.get((province, analog), np.nan),
            }
            for name, matrix in group_matrices.items():
                row[f"{name}_similarity"] = matrix.loc[province, analog]
            rows.append(row)

    return pd.DataFrame(rows)


def analog_vs_geographic(top: pd.DataFrame, distances: pd.DataFrame) -> pd.DataFrame:
    geo_top = (
        distances.sort_values(["province", "distance_km"])
        .groupby("province")
        .head(5)
        .groupby("province")["neighbor_province"]
        .apply(set)
        .to_dict()
    )

    rows = []
    for province, group in top.groupby("province"):
        analog_set = set(group["analog_province"])
        geo_set = geo_top.get(province, set())
        rows.append(
            {
                "province": province,
                "top5_analog_provinces": "|".join(group["analog_province"].tolist()),
                "top5_geographic_neighbors": "|".join(sorted(geo_set)),
                "analog_geo_overlap_count": len(analog_set & geo_set),
                "analog_geo_overlap_rate": len(analog_set & geo_set) / 5 if geo_set else np.nan,
                "mean_analog_distance_km": group["distance_km"].mean(),
                "same_region_rate": group["same_region"].mean(),
                "cross_region_rate": 1 - group["same_region"].mean(),
            }
        )
    return pd.DataFrame(rows)


def build_analog_features(df: pd.DataFrame, top: pd.DataFrame, train: pd.DataFrame) -> pd.DataFrame:
    analogs = top[top["analog_rank"] <= 5][["province", "analog_province", "combined_similarity"]]
    analogs = analogs.rename(columns={"province": "target_province", "analog_province": "province"})

    train_freq = (
        train.groupby("province")["blast_t_plus_1"]
        .mean()
        .rename("analog_train_blast_tplus1_frequency")
        .reset_index()
    )

    current_cols = [
        "province",
        "datetime",
        "risk_score",
        "host_weighted_risk",
        "host_weighted_rolling_2w",
        "susceptibility_score",
        "leaf_wet_hours",
        "regional_leaf_wet_accumulation",
        "blast_any",
    ]
    current_cols = existing_columns(df, current_cols)
    analog_week = df[current_cols].copy()

    for col in current_cols:
        if col not in ["province", "datetime"]:
            analog_week[col] = pd.to_numeric(analog_week[col], errors="coerce")

    prev = analog_week.copy()
    prev["datetime"] = prev["datetime"] + pd.Timedelta(days=7)
    prev = prev.rename(
        columns={
            "risk_score": "analog_prevweek_risk_component",
            "blast_any": "analog_prevweek_blast_component",
        }
    )

    current = analog_week.rename(
        columns={
            "host_weighted_risk": "analog_host_pressure_component",
            "host_weighted_rolling_2w": "analog_2w_pressure_component",
            "susceptibility_score": "analog_susceptibility_component",
            "leaf_wet_hours": "analog_leaf_wet_component",
            "regional_leaf_wet_accumulation": "analog_regional_leaf_wet_component",
        }
    )

    base_keys = df[["province", "region", "datetime", "year", "week", "blast_t_plus_1"]].copy()
    expanded = base_keys.rename(columns={"province": "target_province"}).merge(
        analogs, on="target_province", how="left"
    )

    expanded = expanded.merge(
        prev[
            [
                "province",
                "datetime",
                "analog_prevweek_risk_component",
                "analog_prevweek_blast_component",
            ]
        ],
        on=["province", "datetime"],
        how="left",
    )
    current_merge_cols = [
        "province",
        "datetime",
        "analog_host_pressure_component",
        "analog_2w_pressure_component",
        "analog_susceptibility_component",
        "analog_leaf_wet_component",
        "analog_regional_leaf_wet_component",
    ]
    expanded = expanded.merge(current[current_merge_cols], on=["province", "datetime"], how="left")
    expanded = expanded.merge(train_freq, on="province", how="left")

    for col in [
        "analog_prevweek_risk_component",
        "analog_prevweek_blast_component",
        "analog_host_pressure_component",
        "analog_2w_pressure_component",
        "analog_susceptibility_component",
        "analog_leaf_wet_component",
        "analog_regional_leaf_wet_component",
        "analog_train_blast_tplus1_frequency",
    ]:
        expanded[col] = expanded[col] * expanded["combined_similarity"]

    weighted = (
        expanded.groupby(["target_province", "region", "datetime", "year", "week"], dropna=False)
        .agg(
            blast_t_plus_1=("blast_t_plus_1", "first"),
            analog_weight_sum=("combined_similarity", "sum"),
            analog_prevweek_blast=("analog_prevweek_blast_component", "sum"),
            analog_prevweek_risk=("analog_prevweek_risk_component", "sum"),
            analog_2w_pressure=("analog_2w_pressure_component", "sum"),
            analog_host_pressure=("analog_host_pressure_component", "sum"),
            analog_leaf_wet_pressure=("analog_leaf_wet_component", "sum"),
            analog_regional_leaf_wet_pressure=("analog_regional_leaf_wet_component", "sum"),
            analog_outbreak_frequency_train=("analog_train_blast_tplus1_frequency", "sum"),
            analog_count=("province", "nunique"),
        )
        .reset_index()
        .rename(columns={"target_province": "province"})
    )

    for col in [
        "analog_prevweek_blast",
        "analog_prevweek_risk",
        "analog_2w_pressure",
        "analog_host_pressure",
        "analog_leaf_wet_pressure",
        "analog_regional_leaf_wet_pressure",
        "analog_outbreak_frequency_train",
    ]:
        weighted[col] = np.where(
            weighted["analog_weight_sum"] > 0,
            weighted[col] / weighted["analog_weight_sum"],
            np.nan,
        )

    return weighted


def feature_effects(df: pd.DataFrame, year: int, feature_cols: list[str]) -> pd.DataFrame:
    subset = df[df["year"] == year].copy()
    subset["blast_t_plus_1"] = pd.to_numeric(subset["blast_t_plus_1"], errors="coerce")
    rows = []
    for scope, group in [("nationwide", subset)] + [
        (f"region_{region}", region_df) for region, region_df in subset.groupby("region")
    ]:
        for feature in feature_cols:
            values = pd.to_numeric(group[feature], errors="coerce")
            y = group["blast_t_plus_1"]
            disease = values[y == 1]
            no_disease = values[y == 0]
            corr = np.nan
            valid = values.notna() & y.notna()
            if valid.sum() > 2 and y[valid].nunique() > 1 and values[valid].nunique() > 1:
                corr = values[valid].corr(y[valid])
            rows.append(
                {
                    "year": year,
                    "scope": scope,
                    "feature": feature,
                    "rows": len(group),
                    "positive_rows": int((y == 1).sum()),
                    "mean_disease": disease.mean(),
                    "mean_no_disease": no_disease.mean(),
                    "effect_diff": disease.mean() - no_disease.mean(),
                    "effect_ratio": safe_ratio(disease.mean(), no_disease.mean()),
                    "correlation": corr,
                    "coverage_rate": values.notna().mean(),
                }
            )
    return pd.DataFrame(rows)


def safe_ratio(a: float, b: float) -> float:
    if pd.isna(a) or pd.isna(b) or abs(b) < 1e-12:
        return np.nan
    return a / b


def cluster_summary(combined_profile: pd.DataFrame, profile_features: pd.DataFrame) -> pd.DataFrame:
    feature_cols = [col for col in profile_features.columns if col != "province"]
    x = profile_features[feature_cols].apply(pd.to_numeric, errors="coerce")
    x = SimpleImputer(strategy="median").fit_transform(x)
    x = StandardScaler().fit_transform(x)

    rows = []
    for k in [4, 6, 8]:
        model = KMeans(n_clusters=k, random_state=42, n_init=20)
        labels = model.fit_predict(x)
        assigned = profile_features[["province"]].copy()
        assigned["cluster_k"] = k
        assigned["cluster"] = labels
        assigned = assigned.merge(combined_profile, on="province", how="left")

        for cluster, group in assigned.groupby("cluster"):
            rows.append(
                {
                    "cluster_k": k,
                    "cluster": cluster,
                    "province_count": len(group),
                    "provinces": "|".join(sorted(group["province"].tolist())),
                    "dominant_region": group["region"].mode().iloc[0]
                    if "region" in group and not group["region"].mode().empty
                    else "Unknown",
                    "mean_outbreak_frequency_train": group[
                        "outbreak_history_tplus1_frequency"
                    ].mean()
                    if "outbreak_history_tplus1_frequency" in group
                    else np.nan,
                    "mean_susceptibility": group["host_mean_susceptibility_score"].mean()
                    if "host_mean_susceptibility_score" in group
                    else np.nan,
                    "mean_leaf_wet": group["weather_mean_leaf_wet_hours"].mean()
                    if "weather_mean_leaf_wet_hours" in group
                    else np.nan,
                    "mean_neighbor_pressure": group[
                        "pressure_mean_regional_neighbor_pressure_3w"
                    ].mean()
                    if "pressure_mean_regional_neighbor_pressure_3w" in group
                    else np.nan,
                }
            )
    return pd.DataFrame(rows)


def north_failure_analysis(analog_features: pd.DataFrame, top: pd.DataFrame) -> pd.DataFrame:
    failure_path = OUTPUT_DIR / "forward_decision_failure_cases.csv"
    if not failure_path.exists():
        return pd.DataFrame()

    failures = pd.read_csv(failure_path, low_memory=False)
    failures = failures[
        (failures["model_label"] == "DNN no class weight")
        & (failures["policy"] == "global_f1")
        & (failures["error_type"] == "false_negative")
        & (failures["region"] == "North")
    ].copy()

    if failures.empty:
        return pd.DataFrame()

    failures["datetime"] = pd.to_datetime(failures["datetime"], errors="coerce")
    analog_cols = [
        "province",
        "datetime",
        "analog_prevweek_blast",
        "analog_prevweek_risk",
        "analog_2w_pressure",
        "analog_host_pressure",
        "analog_leaf_wet_pressure",
        "analog_outbreak_frequency_train",
    ]
    out = failures.merge(analog_features[analog_cols], on=["province", "datetime"], how="left")

    analog_names = (
        top[top["analog_rank"] <= 5]
        .groupby("province")["analog_province"]
        .apply(lambda values: "|".join(values.tolist()))
        .rename("top5_analog_provinces")
        .reset_index()
    )
    out = out.merge(analog_names, on="province", how="left")
    return out[
        [
            "province",
            "datetime",
            "week",
            "y_score",
            "top5_analog_provinces",
            "analog_prevweek_blast",
            "analog_prevweek_risk",
            "analog_2w_pressure",
            "analog_host_pressure",
            "analog_leaf_wet_pressure",
            "analog_outbreak_frequency_train",
        ]
    ]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = prepare_dataset()
    train = df[df["year"].isin(TRAIN_YEARS)].copy()

    regions = df[["province", "region"]].drop_duplicates("province")

    weather_profile = aggregate_profile(train, WEATHER_FEATURES, "weather")
    host_profile = aggregate_profile(train, HOST_FEATURES, "host")
    pressure_profile = aggregate_profile(train, PRESSURE_FEATURES, "pressure")
    outbreak = outbreak_profile(train)

    profiles = {
        "weather": weather_profile,
        "host": host_profile,
        "pressure": pressure_profile,
        "outbreak_history": outbreak,
    }

    matrices = {}
    manifest_parts = []
    for name, profile in profiles.items():
        matrix, manifest = matrix_from_profile(profile, name)
        matrices[name] = matrix
        manifest_parts.append(manifest)
        save_similarity_matrix(matrix, OUTPUT_DIR / f"province_similarity_matrix_{name}.csv")

    combined = combine_matrices(matrices)
    save_similarity_matrix(combined, OUTPUT_DIR / "province_similarity_matrix_combined.csv")

    distances = load_geographic_distances()
    top = top_analogs(combined, matrices, regions, distances)
    top.to_csv(OUTPUT_DIR / "province_top_analog_neighbors.csv", index=False)

    comparison = analog_vs_geographic(top, distances)
    comparison.to_csv(OUTPUT_DIR / "province_analog_vs_geographic_neighbors.csv", index=False)

    analog_features = build_analog_features(df, top, train)
    analog_feature_cols = [
        "analog_prevweek_blast",
        "analog_prevweek_risk",
        "analog_2w_pressure",
        "analog_host_pressure",
        "analog_leaf_wet_pressure",
        "analog_regional_leaf_wet_pressure",
        "analog_outbreak_frequency_train",
    ]

    validation_effects = feature_effects(analog_features, VALIDATION_YEAR, analog_feature_cols)
    test_effects = feature_effects(analog_features, TEST_YEAR, analog_feature_cols)
    validation_effects.to_csv(OUTPUT_DIR / "analog_feature_effects_validation_2021.csv", index=False)
    test_effects.to_csv(OUTPUT_DIR / "analog_feature_effects_test_2022.csv", index=False)

    combined_profile = (
        regions.merge(weather_profile, on="province", how="left")
        .merge(host_profile, on="province", how="left")
        .merge(pressure_profile, on="province", how="left")
        .merge(outbreak, on="province", how="left")
    )
    cluster_summary(combined_profile, combined_profile.drop(columns=["region"])).to_csv(
        OUTPUT_DIR / "province_similarity_cluster_summary.csv", index=False
    )

    north_failure_analysis(analog_features, top).to_csv(
        OUTPUT_DIR / "north_failure_analog_analysis.csv", index=False
    )

    manifest = pd.concat(manifest_parts, ignore_index=True)
    analog_manifest = pd.DataFrame(
        [
            {
                "feature": "analog_prevweek_blast",
                "definition": "Similarity-weighted mean blast_any among top-5 analog provinces from previous week.",
                "temporal_safety": "Uses analog sets learned from train 2017-2020 and previous-week labels only.",
            },
            {
                "feature": "analog_prevweek_risk",
                "definition": "Similarity-weighted mean risk_score among top-5 analog provinces from previous week.",
                "temporal_safety": "Uses previous-week weather risk only.",
            },
            {
                "feature": "analog_2w_pressure",
                "definition": "Similarity-weighted mean host_weighted_rolling_2w among top-5 analog provinces in the current week.",
                "temporal_safety": "Rolling feature is precomputed from historical weeks.",
            },
            {
                "feature": "analog_host_pressure",
                "definition": "Similarity-weighted mean host_weighted_risk among top-5 analog provinces in the current week.",
                "temporal_safety": "Uses current-week host/weather state, not future labels.",
            },
            {
                "feature": "analog_leaf_wet_pressure",
                "definition": "Similarity-weighted mean leaf_wet_hours among top-5 analog provinces in the current week.",
                "temporal_safety": "Uses current-week weather state, not future labels.",
            },
            {
                "feature": "analog_outbreak_frequency_train",
                "definition": "Similarity-weighted train-year blast_t_plus_1 frequency among top-5 analog provinces.",
                "temporal_safety": "Computed from train years 2017-2020 only.",
            },
        ]
    )
    manifest.to_csv(OUTPUT_DIR / "province_similarity_profile_manifest.csv", index=False)
    analog_manifest.to_csv(OUTPUT_DIR / "analog_feature_manifest.csv", index=False)

    print("=== Analog vs Geographic Summary ===")
    print(comparison.describe(include="all").to_string())
    print("\n=== Validation Effects: Top Positive Diff ===")
    print(validation_effects.sort_values("effect_diff", ascending=False).head(12).to_string(index=False))
    print("\n=== Test Effects: Top Positive Diff ===")
    print(test_effects.sort_values("effect_diff", ascending=False).head(12).to_string(index=False))
    print("\n=== Output files written to ===")
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()
