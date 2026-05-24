from __future__ import annotations

from pathlib import Path
import re
import sys

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
UPDATED_DIR = BASE_DIR / "updated data"
OUTPUT_DIR = BASE_DIR / "experiments" / "outputs"


def infer_year(path: Path) -> int | None:
    match = re.search(r"(20\d{2})", str(path))
    return int(match.group(1)) if match else None


def read_csv(path: Path, nrows: int | None = None) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp874"):
        try:
            return pd.read_csv(path, encoding=encoding, nrows=nrows)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Could not read {path}: {last_error}")


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    if "date" in df.columns:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["year"] = df["date"].dt.year
        df["week"] = df["date"].dt.isocalendar().week.astype("Int64")
        df["month"] = df["date"].dt.month
    return df


def summarize_outbreaks() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    province_rows = []
    for path in (UPDATED_DIR / "rice_blast_outbreak_weekly").rglob("*.csv"):
        df = parse_dates(read_csv(path))
        if df.empty:
            continue
        year = infer_year(path)
        area = pd.to_numeric(df.get("rice_blast_outbreak_area"), errors="coerce").fillna(0)
        address = df.get("address", pd.Series(dtype=object)).astype(str)
        rows.append(
            {
                "year": year,
                "file": str(path.relative_to(UPDATED_DIR)),
                "rows": len(df),
                "province": address.iloc[0] if len(address) else None,
                "date_min": df["date"].min(),
                "date_max": df["date"].max(),
                "positive_rows": int((area > 0).sum()),
                "total_outbreak_area": float(area.sum()),
                "mean_outbreak_area": float(area.mean()) if len(area) else 0.0,
            }
        )
        province_rows.append(
            {
                "year": year,
                "province": address.iloc[0] if len(address) else None,
                "rows": len(df),
                "positive_rows": int((area > 0).sum()),
                "total_outbreak_area": float(area.sum()),
                "date_min": df["date"].min(),
                "date_max": df["date"].max(),
            }
        )

    detail = pd.DataFrame(rows)
    province = pd.DataFrame(province_rows)
    if detail.empty:
        return detail, province

    summary = (
        detail.groupby("year", dropna=False)
        .agg(
            file_count=("file", "count"),
            rows=("rows", "sum"),
            provinces=("province", "nunique"),
            date_min=("date_min", "min"),
            date_max=("date_max", "max"),
            positive_rows=("positive_rows", "sum"),
            total_outbreak_area=("total_outbreak_area", "sum"),
            mean_file_outbreak_area=("total_outbreak_area", "mean"),
        )
        .reset_index()
        .sort_values("year")
    )
    return summary, province.sort_values(["year", "province"])


def summarize_pov() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    variety_rows = []
    root = UPDATED_DIR / "pov_rice_monthly"
    for path in root.rglob("*.csv"):
        df = parse_dates(read_csv(path))
        if df.empty:
            continue
        rel = path.relative_to(root)
        season = rel.parts[0] if rel.parts else "unknown"
        year = infer_year(path)
        id_cols = {"date", "address", "latitude", "longitude", "year", "week", "month"}
        variety_cols = [col for col in df.columns if col not in id_cols]
        numeric = df[variety_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        totals = numeric.sum(axis=0).sort_values(ascending=False)
        address = df.get("address", pd.Series(dtype=object)).astype(str)
        rows.append(
            {
                "year": year,
                "season": season,
                "file": str(path.relative_to(UPDATED_DIR)),
                "rows": len(df),
                "province": address.iloc[0] if len(address) else None,
                "date_min": df["date"].min(),
                "date_max": df["date"].max(),
                "variety_count": len(variety_cols),
                "total_area": float(totals.sum()),
            }
        )
        for variety, area in totals.head(8).items():
            variety_rows.append(
                {
                    "year": year,
                    "season": season,
                    "province": address.iloc[0] if len(address) else None,
                    "variety": variety,
                    "area": float(area),
                }
            )

    detail = pd.DataFrame(rows)
    varieties = pd.DataFrame(variety_rows)
    if detail.empty:
        return detail, varieties

    summary = (
        detail.groupby(["year", "season"], dropna=False)
        .agg(
            file_count=("file", "count"),
            rows=("rows", "sum"),
            provinces=("province", "nunique"),
            date_min=("date_min", "min"),
            date_max=("date_max", "max"),
            mean_variety_count=("variety_count", "mean"),
            total_area=("total_area", "sum"),
        )
        .reset_index()
        .sort_values(["year", "season"])
    )

    top_varieties = (
        varieties.groupby(["year", "season", "variety"], dropna=False)["area"]
        .sum()
        .reset_index()
        .sort_values(["year", "season", "area"], ascending=[True, True, False])
    )
    top_varieties = top_varieties.groupby(["year", "season"], as_index=False).head(10)
    return summary, top_varieties


def summarize_bus() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    root = UPDATED_DIR / "bus_value_dayly"
    for path in root.rglob("*.csv"):
        df = parse_dates(read_csv(path))
        if df.empty:
            continue
        rel = path.relative_to(root)
        center_type = rel.parts[0] if rel.parts else "unknown"
        year = infer_year(path)
        for col in ("maxbus", "minbus", "avgbus"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        address = df.get("address", pd.Series(dtype=object)).astype(str)
        rows.append(
            {
                "year": year,
                "center_type": center_type,
                "file": str(path.relative_to(UPDATED_DIR)),
                "rows": len(df),
                "location": address.iloc[0] if len(address) else None,
                "date_min": df["date"].min(),
                "date_max": df["date"].max(),
                "mean_avgbus": df["avgbus"].mean() if "avgbus" in df.columns else None,
                "max_maxbus": df["maxbus"].max() if "maxbus" in df.columns else None,
            }
        )

    detail = pd.DataFrame(rows)
    if detail.empty:
        return detail, detail

    summary = (
        detail.groupby(["year", "center_type"], dropna=False)
        .agg(
            file_count=("file", "count"),
            rows=("rows", "sum"),
            locations=("location", "nunique"),
            date_min=("date_min", "min"),
            date_max=("date_max", "max"),
            mean_avgbus=("mean_avgbus", "mean"),
            max_maxbus=("max_maxbus", "max"),
        )
        .reset_index()
        .sort_values(["year", "center_type"])
    )
    return summary, detail.sort_values(["year", "center_type", "location"])


def summarize_province_mapping() -> pd.DataFrame:
    path = UPDATED_DIR / "thailand_province_name.csv"
    df = read_csv(path)
    return pd.DataFrame(
        [
            {
                "rows": len(df),
                "province_name_unique": df["province_name"].nunique() if "province_name" in df.columns else None,
                "province_thai_unique": df["province_thai"].nunique() if "province_thai" in df.columns else None,
                "columns": "|".join(df.columns.astype(str)),
            }
        ]
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    OUTPUT_DIR.mkdir(exist_ok=True)

    outbreak_summary, outbreak_province = summarize_outbreaks()
    pov_summary, pov_top_varieties = summarize_pov()
    bus_summary, bus_detail = summarize_bus()
    province_mapping = summarize_province_mapping()

    outputs = {
        "updated_outbreak_weekly_summary.csv": outbreak_summary,
        "updated_outbreak_weekly_by_province.csv": outbreak_province,
        "updated_pov_monthly_summary.csv": pov_summary,
        "updated_pov_top_varieties.csv": pov_top_varieties,
        "updated_bus_daily_summary.csv": bus_summary,
        "updated_bus_daily_detail.csv": bus_detail,
        "updated_province_mapping_summary.csv": province_mapping,
    }

    for filename, df in outputs.items():
        df.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 180)
    pd.set_option("display.max_columns", 60)

    print("\n=== OUTBREAK WEEKLY SUMMARY ===")
    print(outbreak_summary.to_string(index=False))
    print("\n=== POV MONTHLY SUMMARY ===")
    print(pov_summary.to_string(index=False))
    print("\n=== BUS DAILY SUMMARY ===")
    print(bus_summary.to_string(index=False))
    print("\n=== PROVINCE MAPPING ===")
    print(province_mapping.to_string(index=False))
    print("\n=== OUTPUT FILES ===")
    for filename in outputs:
        print(OUTPUT_DIR / filename)


if __name__ == "__main__":
    main()
