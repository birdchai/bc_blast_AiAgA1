from __future__ import annotations

from pathlib import Path
import re
import sys

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
OLD_WEATHER_DIR = BASE_DIR / "data" / "weather"
OLD_POV_DIR = BASE_DIR / "data" / "plant of variety"
UPDATED_DIR = BASE_DIR / "updated data"
OUTPUT_DIR = BASE_DIR / "experiments" / "outputs"

WEATHER_NUMERIC_COLUMNS = [
    "temp",
    "dew",
    "humidity",
    "wspd",
    "wgust",
    "wdir",
    "precip",
    "cloudcover",
    "sealevelpressure",
]

WEATHER_SAMPLE_PROVINCES = [
    "Amnat Charoen",
    "Chiang Mai",
    "Chai Nat",
    "Nakhon Ratchasima",
    "Songkhla",
    "Suphan Buri",
]
WEATHER_SAMPLE_MONTHS = {1, 4, 8, 12}


def read_csv_fallback(path: Path, nrows: int | None = None) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp874"):
        try:
            return pd.read_csv(path, encoding=encoding, nrows=nrows)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Could not read {path}: {last_error}")


def infer_year(path: Path) -> int | None:
    match = re.search(r"(20\d{2})", str(path))
    return int(match.group(1)) if match else None


def infer_weather_file_key(path: Path) -> dict:
    stem = path.stem
    match = re.match(r"(?P<province>.+?) (?P<date>20\d{2}-\d{2}-\d{2})(?:-\d+)?$", stem)
    if not match:
        return {"province": None, "year": infer_year(path), "month": None}
    date = pd.to_datetime(match.group("date"), errors="coerce")
    return {
        "province": match.group("province"),
        "year": int(date.year) if pd.notna(date) else infer_year(path),
        "month": int(date.month) if pd.notna(date) else None,
    }


def weather_paths(source: str) -> list[Path]:
    if source == "old":
        return sorted(OLD_WEATHER_DIR.rglob("*.csv"))
    if source == "updated":
        return sorted((UPDATED_DIR / "weather_hourly").rglob("*.csv"))
    raise ValueError(source)


def summarize_weather_source(source: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    file_rows = []
    aggregate_rows = []
    for path in weather_paths(source):
        key = infer_weather_file_key(path)
        is_sample_key = (
            key["province"] in WEATHER_SAMPLE_PROVINCES
            and key["month"] in WEATHER_SAMPLE_MONTHS
        )
        if not is_sample_key:
            file_rows.append(
                {
                    "source": source,
                    "relative_path": str(path.relative_to(BASE_DIR)),
                    **key,
                    "read_ok": None,
                    "rows": None,
                    "columns": None,
                    "error": "metadata_only_not_sampled",
                }
            )
            continue
        try:
            columns = read_csv_fallback(path, nrows=0).columns.tolist()
            usecols = [col for col in ["datetime", "address", *WEATHER_NUMERIC_COLUMNS] if col in columns]
            df = read_csv_fallback(path, nrows=None)[usecols]
        except Exception as exc:
            file_rows.append(
                {
                    "source": source,
                    "relative_path": str(path.relative_to(BASE_DIR)),
                    **key,
                    "read_ok": False,
                    "rows": 0,
                    "columns": None,
                    "error": str(exc),
                }
            )
            continue

        if "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
            key["year"] = int(df["datetime"].dt.year.dropna().mode().iloc[0]) if df["datetime"].notna().any() else key["year"]
            key["month"] = int(df["datetime"].dt.month.dropna().mode().iloc[0]) if df["datetime"].notna().any() else key["month"]
        if "address" in df.columns and df["address"].notna().any():
            key["province"] = str(df["address"].dropna().iloc[0])

        file_rows.append(
            {
                "source": source,
                "relative_path": str(path.relative_to(BASE_DIR)),
                **key,
                "read_ok": True,
                "rows": len(df),
                "columns": "|".join(df.columns.astype(str)),
                "error": None,
            }
        )

        row = {"source": source, **key, "rows": len(df)}
        for col in WEATHER_NUMERIC_COLUMNS:
            if col in df.columns:
                values = pd.to_numeric(df[col], errors="coerce")
                row[f"{col}_value_sum"] = values.sum()
                row[f"{col}_value_count"] = int(values.notna().sum())
                row[f"{col}_sum"] = values.sum() if col == "precip" else None
                row[f"{col}_missing"] = int(values.isna().sum())
        aggregate_rows.append(row)

    files = pd.DataFrame(file_rows)
    aggregates = pd.DataFrame(aggregate_rows)
    if aggregates.empty:
        return files, aggregates

    agg_spec = {"rows": ("rows", "sum")}
    for col in WEATHER_NUMERIC_COLUMNS:
        value_sum_col = f"{col}_value_sum"
        value_count_col = f"{col}_value_count"
        sum_col = f"{col}_sum"
        missing_col = f"{col}_missing"
        if value_sum_col in aggregates.columns:
            agg_spec[value_sum_col] = (value_sum_col, "sum")
        if value_count_col in aggregates.columns:
            agg_spec[value_count_col] = (value_count_col, "sum")
        if sum_col in aggregates.columns:
            agg_spec[sum_col] = (sum_col, "sum")
        if missing_col in aggregates.columns:
            agg_spec[missing_col] = (missing_col, "sum")

    monthly = (
        aggregates.groupby(["source", "province", "year", "month"], dropna=False)
        .agg(**agg_spec)
        .reset_index()
    )
    for col in WEATHER_NUMERIC_COLUMNS:
        value_sum_col = f"{col}_value_sum"
        value_count_col = f"{col}_value_count"
        if value_sum_col in monthly.columns and value_count_col in monthly.columns:
            monthly[f"{col}_mean"] = monthly[value_sum_col] / monthly[value_count_col].replace({0: pd.NA})
    return files, monthly


def compare_weather() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    old_files, old_monthly = summarize_weather_source("old")
    updated_files, updated_monthly = summarize_weather_source("updated")
    file_summary = (
        pd.concat([old_files, updated_files], ignore_index=True)
        .groupby(["source", "year"], dropna=False)
        .agg(
            file_count=("relative_path", "count"),
            sampled_files=("read_ok", lambda s: int(s.notna().sum())),
            readable_sampled_files=("read_ok", lambda s: int(s.fillna(False).sum())),
            rows=("rows", "sum"),
            provinces=("province", "nunique"),
            months=("month", "nunique"),
        )
        .reset_index()
        .sort_values(["source", "year"])
    )

    merged = old_monthly.merge(
        updated_monthly,
        on=["province", "year", "month"],
        how="outer",
        suffixes=("_old", "_updated"),
        indicator=True,
    )
    merged["row_diff"] = merged["rows_updated"].fillna(0) - merged["rows_old"].fillna(0)
    for col in WEATHER_NUMERIC_COLUMNS:
        old_col = f"{col}_mean_old"
        new_col = f"{col}_mean_updated"
        if old_col in merged.columns and new_col in merged.columns:
            merged[f"{col}_mean_abs_diff"] = (merged[new_col] - merged[old_col]).abs()
    diff_cols = [col for col in merged.columns if col.endswith("_mean_abs_diff")]
    merged["any_numeric_diff"] = merged[diff_cols].fillna(0).gt(1e-9).any(axis=1) if diff_cols else False

    comparison_summary = pd.DataFrame(
        [
            {
                "matched_monthly_keys": int((merged["_merge"] == "both").sum()),
                "old_only_monthly_keys": int((merged["_merge"] == "left_only").sum()),
                "updated_only_monthly_keys": int((merged["_merge"] == "right_only").sum()),
                "keys_with_row_diff": int(merged["row_diff"].fillna(0).ne(0).sum()),
                "keys_with_numeric_diff": int(merged["any_numeric_diff"].sum()),
                "max_temp_mean_abs_diff": merged.get("temp_mean_abs_diff", pd.Series(dtype=float)).max(),
                "max_humidity_mean_abs_diff": merged.get("humidity_mean_abs_diff", pd.Series(dtype=float)).max(),
                "max_precip_mean_abs_diff": merged.get("precip_mean_abs_diff", pd.Series(dtype=float)).max(),
            }
        ]
    )
    return file_summary, comparison_summary, merged.sort_values(["year", "month", "province"])


def pov_paths(source: str) -> list[Path]:
    if source == "old":
        return sorted(OLD_POV_DIR.rglob("*.csv"))
    if source == "updated":
        return sorted((UPDATED_DIR / "pov_rice_monthly").rglob("*.csv"))
    raise ValueError(source)


def infer_pov_key(path: Path, source: str) -> dict:
    year = infer_year(path)
    text = str(path)
    if source == "old":
        season = "inseason" if "InSeason" in text else "offseason" if "OffSeason" in text else "unknown"
    else:
        season = "inseason" if "Pov-Rice-In" in text else "offseason" if "Pov-Rice-Off" in text else "unknown"
    return {"year": year, "season": season}


def summarize_pov_source(source: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    file_rows = []
    variety_rows = []
    for path in pov_paths(source):
        key = infer_pov_key(path, source)
        try:
            df = read_csv_fallback(path)
        except Exception as exc:
            file_rows.append(
                {
                    "source": source,
                    "relative_path": str(path.relative_to(BASE_DIR)),
                    **key,
                    "province": None,
                    "read_ok": False,
                    "rows": 0,
                    "variety_count": 0,
                    "total_area": 0,
                    "error": str(exc),
                }
            )
            continue
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        province = str(df["address"].dropna().iloc[0]) if "address" in df.columns and df["address"].notna().any() else None
        id_cols = {"date", "address", "latitude", "longitude"}
        variety_cols = [col for col in df.columns if col not in id_cols]
        numeric = df[variety_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        totals = numeric.sum()
        file_rows.append(
            {
                "source": source,
                "relative_path": str(path.relative_to(BASE_DIR)),
                **key,
                "province": province,
                "read_ok": True,
                "rows": len(df),
                "variety_count": len(variety_cols),
                "total_area": float(totals.sum()),
                "date_min": df["date"].min() if "date" in df.columns else None,
                "date_max": df["date"].max() if "date" in df.columns else None,
                "columns": "|".join(df.columns.astype(str)),
                "error": None,
            }
        )
        for variety, area in totals.items():
            variety_rows.append(
                {
                    "source": source,
                    **key,
                    "province": province,
                    "variety": variety,
                    "area": float(area),
                }
            )
    files = pd.DataFrame(file_rows)
    varieties = pd.DataFrame(variety_rows)
    return files, varieties


def compare_pov() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    old_files, old_varieties = summarize_pov_source("old")
    updated_files, updated_varieties = summarize_pov_source("updated")
    file_summary = (
        pd.concat([old_files, updated_files], ignore_index=True)
        .groupby(["source", "year", "season"], dropna=False)
        .agg(
            file_count=("relative_path", "count"),
            readable_files=("read_ok", "sum"),
            rows=("rows", "sum"),
            provinces=("province", "nunique"),
            mean_variety_count=("variety_count", "mean"),
            total_area=("total_area", "sum"),
            date_min=("date_min", "min"),
            date_max=("date_max", "max"),
        )
        .reset_index()
        .sort_values(["source", "year", "season"])
    )

    old_total = old_varieties.groupby(["year", "season", "province", "variety"], dropna=False)["area"].sum().reset_index()
    updated_total = updated_varieties.groupby(["year", "season", "province", "variety"], dropna=False)["area"].sum().reset_index()
    merged = old_total.merge(
        updated_total,
        on=["year", "season", "province", "variety"],
        how="outer",
        suffixes=("_old", "_updated"),
        indicator=True,
    )
    merged["area_diff"] = merged["area_updated"].fillna(0) - merged["area_old"].fillna(0)
    merged["area_abs_diff"] = merged["area_diff"].abs()

    comparison_summary = (
        merged.groupby(["year", "season"], dropna=False)
        .agg(
            matched_variety_keys=("area_abs_diff", lambda s: int((merged.loc[s.index, "_merge"] == "both").sum())),
            old_only_variety_keys=("area_abs_diff", lambda s: int((merged.loc[s.index, "_merge"] == "left_only").sum())),
            updated_only_variety_keys=("area_abs_diff", lambda s: int((merged.loc[s.index, "_merge"] == "right_only").sum())),
            keys_with_area_diff=("area_abs_diff", lambda s: int(s.gt(1e-9).sum())),
            total_abs_area_diff=("area_abs_diff", "sum"),
            max_area_abs_diff=("area_abs_diff", "max"),
        )
        .reset_index()
        .sort_values(["year", "season"])
    )
    return file_summary, comparison_summary, merged.sort_values(["year", "season", "province", "variety"])


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    OUTPUT_DIR.mkdir(exist_ok=True)

    weather_file_summary, weather_comparison_summary, weather_monthly_comparison = compare_weather()
    pov_file_summary, pov_comparison_summary, pov_variety_comparison = compare_pov()

    outputs = {
        "updated_vs_old_weather_file_summary.csv": weather_file_summary,
        "updated_vs_old_weather_comparison_summary.csv": weather_comparison_summary,
        "updated_vs_old_weather_monthly_comparison.csv": weather_monthly_comparison,
        "updated_vs_old_pov_file_summary.csv": pov_file_summary,
        "updated_vs_old_pov_comparison_summary.csv": pov_comparison_summary,
        "updated_vs_old_pov_variety_comparison.csv": pov_variety_comparison,
    }
    for filename, df in outputs.items():
        df.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 80)
    print("\n=== WEATHER FILE SUMMARY ===")
    print(weather_file_summary.to_string(index=False))
    print("\n=== WEATHER COMPARISON SUMMARY ===")
    print(weather_comparison_summary.to_string(index=False))
    print("\n=== POV FILE SUMMARY ===")
    print(pov_file_summary.to_string(index=False))
    print("\n=== POV COMPARISON SUMMARY ===")
    print(pov_comparison_summary.to_string(index=False))
    print("\n=== OUTPUT FILES ===")
    for filename in outputs:
        print(OUTPUT_DIR / filename)


if __name__ == "__main__":
    main()
