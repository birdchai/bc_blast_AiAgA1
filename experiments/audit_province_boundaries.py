"""Audit local province boundary availability and name matching readiness.

Step 9.16B is governance only:
- scan local files for boundary candidates,
- inspect readable schemas where possible,
- compare available boundary names with project province names,
- recommend external boundary sources if no usable local boundary exists.

No DEM processing, no Google Earth Engine calls, and no model training occur here.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "experiments" / "outputs"
DATASET_PATH = OUTPUT_DIR / "region_temporal_sequence_dataset_updated_labels_2015_2022.csv"
UPDATED_PROVINCE_NAME_PATH = ROOT / "updated data" / "thailand_province_name.csv"
OLD_PROVINCE_NAME_PATH = ROOT / "data" / "thailand_province_name.csv"

BOUNDARY_EXTENSIONS = {".shp", ".shx", ".dbf", ".prj", ".geojson", ".json", ".gpkg", ".kml", ".kmz"}
CSV_EXTENSIONS = {".csv"}
SCAN_DIRS = [ROOT, ROOT / "data", ROOT / "updated data", ROOT / "experiments", ROOT / "tools"]

NAME_COLUMN_PATTERNS = [
    "province",
    "prov",
    "changwat",
    "adm1",
    "name_1",
    "name_en",
    "adm1_en",
    "adm1_name",
    "name",
    "thai",
]
GEOMETRY_COLUMN_PATTERNS = ["geometry", "wkt", "polygon", "multipolygon", "geojson", "coordinates", "geom"]

MANUAL_BOUNDARY_SOURCE_RECOMMENDATIONS = [
    {
        "source": "geoBoundaries",
        "role": "recommended first boundary source if local boundary is missing",
        "reason": "Provides ADM1 boundaries with a reproducible API/download workflow and is commonly used for research boundary preparation.",
    },
    {
        "source": "GADM",
        "role": "strong fallback boundary source",
        "reason": "Provides Thailand administrative boundaries and is widely used, but license/redistribution terms must be checked before publication packaging.",
    },
    {
        "source": "HDX / Humanitarian Data Exchange",
        "role": "candidate source",
        "reason": "May provide humanitarian administrative boundaries; source provenance and update date must be checked.",
    },
    {
        "source": "Thai government GIS / NSO / DOPA / RID / GISTDA",
        "role": "official-source candidate",
        "reason": "Potentially authoritative for Thailand, but access, format, license, and nationwide coverage must be verified.",
    },
    {
        "source": "Natural Earth",
        "role": "not preferred",
        "reason": "Likely too coarse for province-level terrain extraction unless no other boundary is available.",
    },
]


def normalize_name(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


def safe_rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def looks_like_boundary_path(path: Path) -> bool:
    lower = str(path).lower()
    tokens = ["boundary", "boundaries", "admin", "adm", "province", "changwat", "gis", "shape", "geo", "map", "polygon"]
    return any(token in lower for token in tokens)


def find_files() -> list[Path]:
    seen: set[Path] = set()
    results: list[Path] = []
    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for path in scan_dir.rglob("*"):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix in BOUNDARY_EXTENSIONS:
                if path not in seen:
                    seen.add(path)
                    results.append(path)
            elif suffix in CSV_EXTENSIONS and looks_like_boundary_path(path):
                if path not in seen:
                    seen.add(path)
                    results.append(path)
    return sorted(results, key=lambda p: safe_rel(p).lower())


def inspect_csv(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "readable": False,
        "geometry_type_if_readable": "",
        "feature_count_if_readable": "",
        "crs_if_readable": "",
        "candidate_name_columns": "",
        "notes": "",
    }
    try:
        df = read_csv_with_fallback(path, nrows=200)
        result["readable"] = True
        result["feature_count_if_readable"] = len(df)
        columns = list(df.columns)
        lower_cols = {c: c.lower() for c in columns}
        name_cols = [
            c
            for c, lower in lower_cols.items()
            if any(pattern in lower for pattern in NAME_COLUMN_PATTERNS)
        ]
        geom_cols = [
            c
            for c, lower in lower_cols.items()
            if any(pattern in lower for pattern in GEOMETRY_COLUMN_PATTERNS)
        ]
        result["candidate_name_columns"] = "|".join(name_cols)
        if geom_cols:
            result["geometry_type_if_readable"] = "tabular_geometry_candidate"
            result["notes"] = f"CSV has possible geometry columns: {'|'.join(geom_cols)}"
        elif name_cols:
            result["geometry_type_if_readable"] = "none"
            result["notes"] = "CSV has province/name metadata but no geometry column"
        else:
            result["geometry_type_if_readable"] = "none"
            result["notes"] = "CSV readable but no boundary-like schema detected"
    except Exception as exc:  # noqa: BLE001
        result["notes"] = f"CSV read failed: {exc}"
    return result


def read_csv_with_fallback(path: Path, **kwargs: Any) -> pd.DataFrame:
    last_exc: Exception | None = None
    for encoding in ["utf-8", "utf-8-sig", "cp874", "tis-620", "latin1"]:
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    raise last_exc if last_exc else RuntimeError(f"Unable to read CSV: {path}")


def inspect_geojson_or_json(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "readable": False,
        "geometry_type_if_readable": "",
        "feature_count_if_readable": "",
        "crs_if_readable": "",
        "candidate_name_columns": "",
        "notes": "",
    }
    try:
        with path.open("r", encoding="utf-8") as f:
            obj = json.load(f)
        result["readable"] = True
        if isinstance(obj, dict) and obj.get("type") == "FeatureCollection":
            features = obj.get("features") or []
            result["feature_count_if_readable"] = len(features)
            geom_types = sorted(
                {
                    ((feature.get("geometry") or {}).get("type") or "")
                    for feature in features
                    if isinstance(feature, dict)
                }
            )
            result["geometry_type_if_readable"] = "|".join([g for g in geom_types if g])
            props = []
            for feature in features[:20]:
                if isinstance(feature, dict):
                    props.extend(list((feature.get("properties") or {}).keys()))
            unique_props = sorted(set(props))
            name_cols = [
                c
                for c in unique_props
                if any(pattern in c.lower() for pattern in NAME_COLUMN_PATTERNS)
            ]
            result["candidate_name_columns"] = "|".join(name_cols)
            crs = obj.get("crs")
            if crs:
                result["crs_if_readable"] = json.dumps(crs, ensure_ascii=False)
            result["notes"] = "GeoJSON FeatureCollection inspected"
        else:
            result["notes"] = "JSON readable but not a GeoJSON FeatureCollection"
    except Exception as exc:  # noqa: BLE001
        result["notes"] = f"JSON read failed: {exc}"
    return result


def inspect_vector_with_geopandas(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "readable": False,
        "geometry_type_if_readable": "",
        "feature_count_if_readable": "",
        "crs_if_readable": "",
        "candidate_name_columns": "",
        "notes": "",
    }
    try:
        import geopandas as gpd  # type: ignore

        gdf = gpd.read_file(path)
        result["readable"] = True
        result["feature_count_if_readable"] = len(gdf)
        if "geometry" in gdf:
            geom_types = sorted(set(gdf.geometry.geom_type.dropna().astype(str)))
            result["geometry_type_if_readable"] = "|".join(geom_types)
        result["crs_if_readable"] = str(gdf.crs) if gdf.crs else ""
        name_cols = [
            c
            for c in gdf.columns
            if c != "geometry" and any(pattern in c.lower() for pattern in NAME_COLUMN_PATTERNS)
        ]
        result["candidate_name_columns"] = "|".join(name_cols)
        result["notes"] = "Read with geopandas"
    except Exception as exc:  # noqa: BLE001
        result["notes"] = f"Vector read failed or geopandas unavailable: {exc}"
    return result


def inspect_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    row = {
        "file_path": safe_rel(path),
        "file_type": suffix,
        "file_size": path.stat().st_size,
        "likely_boundary_source": classify_source(path),
        "readable": False,
        "geometry_type_if_readable": "",
        "feature_count_if_readable": "",
        "crs_if_readable": "",
        "candidate_name_columns": "",
        "notes": "",
    }
    if suffix == ".csv":
        row.update(inspect_csv(path))
    elif suffix in {".geojson", ".json"}:
        row.update(inspect_geojson_or_json(path))
    elif suffix in {".shp", ".gpkg", ".kml", ".kmz"}:
        row.update(inspect_vector_with_geopandas(path))
    elif suffix in {".shx", ".dbf", ".prj"}:
        row["notes"] = "Shapefile sidecar file; inspect associated .shp if present"
    return row


def classify_source(path: Path) -> str:
    lower = str(path).lower()
    if "thailand_province_name" in lower:
        return "project province-name metadata, not boundary geometry"
    if "gadm" in lower:
        return "GADM candidate"
    if "geoboundaries" in lower:
        return "geoBoundaries candidate"
    if "hdx" in lower:
        return "HDX candidate"
    if any(token in lower for token in ["boundary", "admin", "province", "changwat", "geo", "gis", "shape"]):
        return "local boundary-like candidate"
    return "unknown"


def load_project_provinces() -> list[str]:
    if DATASET_PATH.exists():
        df = pd.read_csv(DATASET_PATH, usecols=["province"])
        return sorted(df["province"].dropna().astype(str).unique())
    if UPDATED_PROVINCE_NAME_PATH.exists():
        df = pd.read_csv(UPDATED_PROVINCE_NAME_PATH)
        return sorted(df["province_name"].dropna().astype(str).unique())
    if OLD_PROVINCE_NAME_PATH.exists():
        df = pd.read_csv(OLD_PROVINCE_NAME_PATH)
        return sorted(df["province_name"].dropna().astype(str).unique())
    raise FileNotFoundError("No project province list source found.")


def extract_boundary_names(path: Path, candidate_cols: str) -> tuple[str, list[str]]:
    if not candidate_cols:
        return "", []
    cols = candidate_cols.split("|")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = read_csv_with_fallback(path)
        for col in cols:
            if col in df.columns:
                values = sorted(df[col].dropna().astype(str).unique())
                if values:
                    return col, values
    if suffix in {".geojson", ".json"}:
        with path.open("r", encoding="utf-8") as f:
            obj = json.load(f)
        features = obj.get("features") if isinstance(obj, dict) else []
        if isinstance(features, list):
            for col in cols:
                values = sorted(
                    {
                        str((feature.get("properties") or {}).get(col))
                        for feature in features
                        if isinstance(feature, dict)
                        and (feature.get("properties") or {}).get(col) is not None
                    }
                )
                if values:
                    return col, values
    return "", []


def choose_usable_boundary_candidate(inventory: pd.DataFrame) -> tuple[str, list[str], str]:
    if inventory.empty:
        return "", [], ""
    for _, row in inventory.iterrows():
        geom = str(row.get("geometry_type_if_readable", ""))
        count = row.get("feature_count_if_readable", "")
        readable = bool(row.get("readable"))
        has_polygon = "Polygon" in geom
        try:
            feature_count = int(count)
        except Exception:  # noqa: BLE001
            feature_count = 0
        if readable and has_polygon and feature_count >= 70:
            path = ROOT / str(row["file_path"]).replace("/", "\\")
            used_col, names = extract_boundary_names(path, str(row.get("candidate_name_columns", "")))
            if names:
                return str(row["file_path"]), names, used_col
    return "", [], ""


def build_name_match_audit(project_provinces: list[str], boundary_file: str, boundary_names: list[str]) -> pd.DataFrame:
    boundary_by_norm = {normalize_name(name): name for name in boundary_names}
    rows = []
    for province in project_provinces:
        norm_project = normalize_name(province)
        boundary_raw = boundary_by_norm.get(norm_project, "")
        rows.append(
            {
                "project_province": province,
                "boundary_province_raw": boundary_raw,
                "normalized_project_name": norm_project,
                "normalized_boundary_name": normalize_name(boundary_raw),
                "match_status": "matched" if boundary_raw else "unmatched_no_local_boundary",
                "match_method": "normalized_exact" if boundary_raw else "none",
                "candidate_boundary_file": boundary_file,
                "notes": "" if boundary_raw else "No usable local polygon boundary candidate available",
            }
        )
    return pd.DataFrame(rows)


def write_boundary_recommendation(has_usable_boundary: bool, match_count: int, total_project: int) -> None:
    decision = "usable local boundary found" if has_usable_boundary else "no usable local boundary found"
    recommendation = OUTPUT_DIR / "province_boundary_data_scout_recommendation.md"
    text = f"""# Province Boundary Data Scout Recommendation

## Purpose

This recommendation supports Step 9.16B: Province Boundary and Name Matching Audit.

No DEM processing, Google Earth Engine processing, terrain feature creation, or model training was performed.

## Local Boundary Decision

- Local boundary status: {decision}
- Project provinces: {total_project}
- Matched provinces: {match_count}

## Interpretation

The local project folders were scanned for boundary-ready GIS files:

- `.shp`
- `.shx`
- `.dbf`
- `.prj`
- `.geojson`
- `.json`
- `.gpkg`
- `.kml`
- `.kmz`
- boundary-like `.csv` files with geometry/WKT/polygon indicators

No usable Thailand province polygon boundary was found locally.

The available `thailand_province_name.csv` file is useful as project province-name metadata, but it is not a polygon boundary source.

## Step 9.17 Readiness

Step 9.17 should not start DEM extraction until a province boundary file is approved and audited.

A usable boundary source must satisfy:

- polygon or multipolygon geometry,
- province-level Thailand coverage,
- 77 province features or equivalent,
- English or mappable province names,
- known or recoverable CRS,
- documented license/source,
- 77/77 project province-name match or near-complete match with documented manual mapping.

## Recommended Boundary Source Order

1. geoBoundaries
   - Recommended first source if local boundary remains missing.
   - Rationale: reproducible research-oriented administrative boundary access.

2. GADM
   - Strong fallback.
   - Rationale: widely used administrative boundaries.
   - Caveat: license and redistribution terms must be checked before thesis/project packaging.

3. HDX / Humanitarian Data Exchange
   - Candidate source.
   - Rationale: may provide administrative boundaries with humanitarian provenance.
   - Caveat: source freshness and provenance must be checked.

4. Thai government GIS / NSO / DOPA / RID / GISTDA
   - Official-source candidate.
   - Rationale: potentially authoritative Thailand boundary data.
   - Caveat: access, license, and reproducibility may require manual review.

5. Natural Earth
   - Not preferred.
   - Rationale: likely too coarse for province-level terrain extraction.

## Required Approved Boundary Schema

Minimum required fields:

- province name in English, or a stable province code plus mapping table,
- polygon or multipolygon geometry,
- CRS metadata,
- source name,
- source version or download date,
- license/terms note.

Preferred fields:

- province English name,
- province Thai name,
- province code,
- region if available,
- geometry validity flag after audit.

## Manual Name-Mapping Needs

After acquiring a boundary source:

- normalize province names conservatively,
- run exact normalized matching first,
- flag uncertain matches for manual review,
- do not silently force ambiguous matches,
- save manual mapping decisions in a tracked mapping table.

## Recommendation

Acquire or approve a province-level Thailand boundary dataset before Step 9.17.

The next technical action should be:

1. obtain a boundary candidate,
2. rerun the boundary/name audit,
3. verify 77/77 province matching,
4. only then proceed to SRTM/GEE terrain extraction.
"""
    recommendation.write_text(text, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = find_files()
    inventory_rows = [inspect_file(path) for path in files]
    inventory = pd.DataFrame(
        inventory_rows,
        columns=[
            "file_path",
            "file_type",
            "file_size",
            "likely_boundary_source",
            "readable",
            "geometry_type_if_readable",
            "feature_count_if_readable",
            "crs_if_readable",
            "candidate_name_columns",
            "notes",
        ],
    )
    inventory.to_csv(OUTPUT_DIR / "province_boundary_inventory.csv", index=False)

    project_provinces = load_project_provinces()
    boundary_file, boundary_names, used_name_col = choose_usable_boundary_candidate(inventory)
    match_audit = build_name_match_audit(project_provinces, boundary_file, boundary_names)
    match_audit.to_csv(OUTPUT_DIR / "province_boundary_name_match_audit.csv", index=False)

    unmatched_project = match_audit[match_audit["match_status"] != "matched"][
        ["project_province", "normalized_project_name", "candidate_boundary_file", "notes"]
    ]
    unmatched_project.to_csv(OUTPUT_DIR / "province_boundary_unmatched_project_names.csv", index=False)

    matched_boundary_norms = set(match_audit["normalized_boundary_name"].dropna())
    unmatched_boundary_rows = []
    for name in boundary_names:
        norm = normalize_name(name)
        if norm and norm not in matched_boundary_norms:
            unmatched_boundary_rows.append(
                {
                    "boundary_province_raw": name,
                    "normalized_boundary_name": norm,
                    "candidate_boundary_file": boundary_file,
                    "candidate_name_column": used_name_col,
                    "notes": "Boundary name not matched to project province list",
                }
            )
    pd.DataFrame(
        unmatched_boundary_rows,
        columns=[
            "boundary_province_raw",
            "normalized_boundary_name",
            "candidate_boundary_file",
            "candidate_name_column",
            "notes",
        ],
    ).to_csv(OUTPUT_DIR / "province_boundary_unmatched_boundary_names.csv", index=False)

    match_count = int((match_audit["match_status"] == "matched").sum())
    has_usable_boundary = bool(boundary_file and match_count >= 70)
    write_boundary_recommendation(has_usable_boundary, match_count, len(project_provinces))

    summary = {
        "files_scanned": len(files),
        "gis_boundary_files_found": int(sum(Path(row["file_path"]).suffix.lower() in BOUNDARY_EXTENSIONS for row in inventory_rows)),
        "usable_boundary_file": boundary_file,
        "project_province_count": len(project_provinces),
        "matched_project_province_count": match_count,
        "unmatched_project_province_count": len(project_provinces) - match_count,
    }
    print(summary)


if __name__ == "__main__":
    main()
