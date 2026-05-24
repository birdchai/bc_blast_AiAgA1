from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
WEATHER_DIR = BASE_DIR / "updated data" / "weather_hourly"
UPDATED_DATA_DIR = BASE_DIR / "updated data"
OUTPUT_DIR = BASE_DIR / "experiments" / "outputs"

TERRAIN_KEYWORDS = [
    "elevation",
    "altitude",
    "height",
    "above sea",
    "above_sea",
    "asl",
    "amsl",
    "terrain",
    "slope",
    "dem",
]

PRESSURE_KEYWORDS = [
    "pressure",
    "sealevelpressure",
    "sea_level_pressure",
    "surfacepressure",
    "surface_pressure",
    "stationpressure",
    "station_pressure",
    "barometer",
]

METADATA_KEYWORDS = [
    "station",
    "site",
    "address",
    "resolvedaddress",
    "name",
    "latitude",
    "longitude",
    "lat",
    "lon",
    "info",
]


def parse_year(path: Path) -> int | None:
    for part in path.parts:
        digits = "".join(ch for ch in part if ch.isdigit())
        if len(digits) >= 4:
            year = int(digits[-4:])
            if 2010 <= year <= 2030:
                return year
    return None


def classify_column(column: str) -> dict[str, bool]:
    normalized = column.strip().lower().replace(" ", "_")
    return {
        "is_terrain_candidate": any(keyword.replace(" ", "_") in normalized for keyword in TERRAIN_KEYWORDS),
        "is_pressure_candidate": any(keyword.replace(" ", "_") in normalized for keyword in PRESSURE_KEYWORDS),
        "is_metadata_candidate": any(keyword.replace(" ", "_") in normalized for keyword in METADATA_KEYWORDS),
    }


def scan_headers(files: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    file_rows = []
    column_rows = []

    for file_path in files:
        year = parse_year(file_path)
        try:
            with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                columns = next(reader)
        except UnicodeDecodeError:
            with file_path.open("r", encoding="cp874", newline="") as handle:
                reader = csv.reader(handle)
                columns = next(reader)
        except Exception as exc:
            file_rows.append(
                {
                    "file_path": str(file_path.relative_to(BASE_DIR)),
                    "year": year,
                    "read_ok": False,
                    "error": str(exc),
                    "column_count": None,
                    "columns": None,
                }
            )
            continue

        cleaned = [column.strip() for column in columns]
        file_rows.append(
            {
                "file_path": str(file_path.relative_to(BASE_DIR)),
                "year": year,
                "read_ok": True,
                "error": "",
                "column_count": len(cleaned),
                "columns": "|".join(cleaned),
            }
        )
        for column in cleaned:
            flags = classify_column(column)
            column_rows.append(
                {
                    "column": column,
                    "year": year,
                    "file_path": str(file_path.relative_to(BASE_DIR)),
                    **flags,
                }
            )

    file_scan = pd.DataFrame(file_rows)
    column_scan = pd.DataFrame(column_rows)
    unique_columns = (
        column_scan.groupby("column", dropna=False)
        .agg(
            file_count=("file_path", "nunique"),
            year_count=("year", "nunique"),
            years=("year", lambda values: "|".join(map(str, sorted(set(v for v in values if pd.notna(v)))))),
            is_terrain_candidate=("is_terrain_candidate", "max"),
            is_pressure_candidate=("is_pressure_candidate", "max"),
            is_metadata_candidate=("is_metadata_candidate", "max"),
        )
        .reset_index()
        .sort_values(["is_terrain_candidate", "is_pressure_candidate", "is_metadata_candidate", "column"], ascending=[False, False, False, True])
    )

    return file_scan, column_scan, unique_columns


def audit_pressure(files: list[Path], pressure_cols: list[str]) -> pd.DataFrame:
    rows = []
    if not pressure_cols:
        return pd.DataFrame(rows)

    for file_path in files:
        year = parse_year(file_path)
        try:
            header = pd.read_csv(file_path, nrows=0, encoding="utf-8-sig").columns.tolist()
        except UnicodeDecodeError:
            header = pd.read_csv(file_path, nrows=0, encoding="cp874").columns.tolist()
        except Exception:
            continue

        available = [col for col in pressure_cols if col in header]
        usecols = [col for col in ["address", "datetime", "latitude", "longitude"] if col in header] + available
        if not available:
            continue

        try:
            df = pd.read_csv(file_path, usecols=usecols, encoding="utf-8-sig", low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, usecols=usecols, encoding="cp874", low_memory=False)
        except Exception:
            continue

        province = df["address"].dropna().iloc[0] if "address" in df.columns and df["address"].notna().any() else file_path.stem
        for col in available:
            values = pd.to_numeric(df[col], errors="coerce")
            rows.append(
                {
                    "file_path": str(file_path.relative_to(BASE_DIR)),
                    "year": year,
                    "province": province,
                    "pressure_column": col,
                    "rows": len(df),
                    "non_missing_rows": int(values.notna().sum()),
                    "coverage_rate": float(values.notna().mean()) if len(values) else None,
                    "mean": float(values.mean()) if values.notna().any() else None,
                    "min": float(values.min()) if values.notna().any() else None,
                    "max": float(values.max()) if values.notna().any() else None,
                    "latitude": pd.to_numeric(df.get("latitude"), errors="coerce").mean() if "latitude" in df.columns else None,
                    "longitude": pd.to_numeric(df.get("longitude"), errors="coerce").mean() if "longitude" in df.columns else None,
                }
            )

    detail = pd.DataFrame(rows)
    if detail.empty:
        return detail

    return (
        detail.groupby(["pressure_column", "year"], dropna=False)
        .agg(
            files=("file_path", "nunique"),
            provinces=("province", "nunique"),
            rows=("rows", "sum"),
            non_missing_rows=("non_missing_rows", "sum"),
            mean_coverage_rate=("coverage_rate", "mean"),
            mean_pressure=("mean", "mean"),
            min_pressure=("min", "min"),
            max_pressure=("max", "max"),
        )
        .reset_index()
    )


def audit_metadata_values(files: list[Path], metadata_cols: list[str]) -> pd.DataFrame:
    rows = []
    sample_files = files[:: max(1, len(files) // 400)]
    for file_path in sample_files:
        year = parse_year(file_path)
        try:
            header = pd.read_csv(file_path, nrows=0, encoding="utf-8-sig").columns.tolist()
        except UnicodeDecodeError:
            header = pd.read_csv(file_path, nrows=0, encoding="cp874").columns.tolist()
        except Exception:
            continue

        available = [col for col in metadata_cols if col in header]
        if not available:
            continue

        try:
            df = pd.read_csv(file_path, usecols=available, nrows=50, encoding="utf-8-sig", low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, usecols=available, nrows=50, encoding="cp874", low_memory=False)
        except Exception:
            continue

        for col in available:
            values = df[col].dropna().astype(str).unique().tolist()
            rows.append(
                {
                    "file_path": str(file_path.relative_to(BASE_DIR)),
                    "year": year,
                    "metadata_column": col,
                    "sample_unique_values": "|".join(values[:8]),
                    "sample_unique_count": len(values),
                }
            )

    return pd.DataFrame(rows)


def scan_standalone_metadata_files() -> pd.DataFrame:
    rows = []
    keywords = ["station", "metadata", "province", "weather", "location", "name", "center"]
    for file_path in UPDATED_DATA_DIR.rglob("*"):
        if not file_path.is_file():
            continue
        normalized = file_path.name.lower()
        if any(keyword in normalized for keyword in keywords):
            rows.append(
                {
                    "file_path": str(file_path.relative_to(BASE_DIR)),
                    "file_name": file_path.name,
                    "size_bytes": file_path.stat().st_size,
                    "category": file_path.relative_to(UPDATED_DATA_DIR).parts[0],
                }
            )
    return pd.DataFrame(rows).sort_values(["category", "file_path"]) if rows else pd.DataFrame(rows)


def terrain_template() -> pd.DataFrame:
    provinces = []
    province_file = UPDATED_DATA_DIR / "thailand_province_name.csv"
    if province_file.exists():
        try:
            names = pd.read_csv(province_file)
        except UnicodeDecodeError:
            names = pd.read_csv(province_file, encoding="cp874")
        try:
            first_col = names.columns[0]
            provinces = sorted(names[first_col].dropna().astype(str).unique().tolist())
        except Exception:
            provinces = []

    return pd.DataFrame(
        {
            "province": provinces,
            "elevation_mean": pd.NA,
            "elevation_min": pd.NA,
            "elevation_max": pd.NA,
            "elevation_range": pd.NA,
            "elevation_std": pd.NA,
            "terrain_roughness": pd.NA,
            "source": pd.NA,
            "notes": pd.NA,
        }
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(WEATHER_DIR.rglob("*.csv"))
    file_scan, column_scan, unique_columns = scan_headers(files)

    pressure_cols = unique_columns.loc[unique_columns["is_pressure_candidate"], "column"].tolist()
    metadata_cols = unique_columns.loc[unique_columns["is_metadata_candidate"], "column"].tolist()

    pressure_summary = audit_pressure(files, pressure_cols)
    metadata_samples = audit_metadata_values(files, metadata_cols)
    standalone_metadata = scan_standalone_metadata_files()
    template = terrain_template()

    file_scan.to_csv(OUTPUT_DIR / "weather_hourly_schema_file_scan.csv", index=False, encoding="utf-8-sig")
    unique_columns.to_csv(OUTPUT_DIR / "weather_hourly_unique_columns.csv", index=False, encoding="utf-8-sig")
    pressure_summary.to_csv(OUTPUT_DIR / "weather_hourly_pressure_column_summary.csv", index=False, encoding="utf-8-sig")
    metadata_samples.to_csv(OUTPUT_DIR / "weather_hourly_metadata_sample_values.csv", index=False, encoding="utf-8-sig")
    standalone_metadata.to_csv(OUTPUT_DIR / "weather_source_metadata_file_inventory.csv", index=False, encoding="utf-8-sig")
    template.to_csv(OUTPUT_DIR / "province_terrain_table_template.csv", index=False, encoding="utf-8-sig")

    terrain_cols = unique_columns[unique_columns["is_terrain_candidate"]]
    pressure_found = unique_columns[unique_columns["is_pressure_candidate"]]
    metadata_found = unique_columns[unique_columns["is_metadata_candidate"]]

    print("=== WEATHER TERRAIN METADATA AUDIT ===")
    print(f"weather files scanned: {len(files)}")
    print(f"unique columns: {len(unique_columns)}")
    print("\n=== UNIQUE COLUMNS ===")
    print(unique_columns[["column", "file_count", "years", "is_terrain_candidate", "is_pressure_candidate", "is_metadata_candidate"]].to_string(index=False))
    print("\n=== TERRAIN CANDIDATE COLUMNS ===")
    print(terrain_cols.to_string(index=False) if not terrain_cols.empty else "None")
    print("\n=== PRESSURE CANDIDATE COLUMNS ===")
    print(pressure_found.to_string(index=False) if not pressure_found.empty else "None")
    print("\n=== METADATA CANDIDATE COLUMNS ===")
    print(metadata_found.to_string(index=False) if not metadata_found.empty else "None")
    print("\n=== PRESSURE SUMMARY ===")
    print(pressure_summary.to_string(index=False) if not pressure_summary.empty else "No pressure columns found.")
    print("\n=== OUTPUT FILES ===")
    for filename in [
        "weather_hourly_schema_file_scan.csv",
        "weather_hourly_unique_columns.csv",
        "weather_hourly_pressure_column_summary.csv",
        "weather_hourly_metadata_sample_values.csv",
        "weather_source_metadata_file_inventory.csv",
        "province_terrain_table_template.csv",
    ]:
        print(OUTPUT_DIR / filename)


if __name__ == "__main__":
    main()
