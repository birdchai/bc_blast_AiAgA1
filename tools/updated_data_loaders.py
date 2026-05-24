from __future__ import annotations

from pathlib import Path
import re

import pandas as pd


BUS_CRITICAL_THRESHOLD = 2.25


def _read_csv_fallback(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp874"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Could not read {path}: {last_error}")


def _infer_year(path: Path) -> int | None:
    match = re.search(r"(20\d{2})", str(path))
    return int(match.group(1)) if match else None


def week_ending_sunday(series: pd.Series) -> pd.Series:
    dates = pd.to_datetime(series, errors="coerce")
    return dates.dt.to_period("W-SUN").dt.end_time.dt.normalize()


def load_updated_blast_outbreak_weekly(folder_path: str | Path) -> pd.DataFrame:
    """
    Load updated weekly rice blast outbreak labels.

    The source column `rice_blast_outbreak_area` is treated as the observed
    outbreak severity/area. `blast_any` is 1 when area > 0. Dates are converted
    to the project's week-ending Sunday convention to match weekly weather.
    """
    root = Path(folder_path)
    rows = []
    for path in root.rglob("*.csv"):
        df = _read_csv_fallback(path)
        required = {"date", "address", "rice_blast_outbreak_area"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"{path} missing required columns: {sorted(missing)}")

        out = df[["date", "address", "latitude", "longitude", "rice_blast_outbreak_area"]].copy()
        out["province"] = out["address"].astype(str).str.strip()
        out["datetime"] = week_ending_sunday(out["date"])
        out["source_year"] = _infer_year(path)
        out["blast_area"] = pd.to_numeric(out["rice_blast_outbreak_area"], errors="coerce").fillna(0)
        out["blast_any"] = (out["blast_area"] > 0).astype(int)
        out["source_file"] = path.name
        rows.append(out)

    if not rows:
        raise ValueError(f"No updated blast outbreak CSV files found under {root}")

    combined = pd.concat(rows, ignore_index=True).dropna(subset=["province", "datetime"])
    weekly = (
        combined.groupby(["province", "datetime"], dropna=False)
        .agg(
            blast_any=("blast_any", "max"),
            blast_area=("blast_area", "sum"),
            outbreak_reports=("blast_any", "sum"),
            latitude=("latitude", "first"),
            longitude=("longitude", "first"),
            source_files=("source_file", "nunique"),
            source_year=("source_year", "first"),
        )
        .reset_index()
    )
    weekly["blast_days"] = weekly["blast_any"]
    weekly["year"] = weekly["datetime"].dt.year
    weekly["week"] = weekly["datetime"].dt.isocalendar().week.astype(int)
    return weekly


def load_updated_pov_monthly(folder_path: str | Path) -> pd.DataFrame:
    """
    Load updated monthly POV files into long province-month variety ratios.

    Updated POV is monthly rather than daily-expanded. Ratios are computed
    within each province-month-season file row.
    """
    root = Path(folder_path)
    rows = []
    id_cols = {"date", "address", "latitude", "longitude"}
    for path in root.rglob("*.csv"):
        df = _read_csv_fallback(path)
        missing = id_cols - set(df.columns)
        if missing:
            raise ValueError(f"{path} missing required POV columns: {sorted(missing)}")

        rel = path.relative_to(root)
        rel_text = str(rel).replace("\\", "/").lower()
        if "pov-rice-off" in rel_text:
            season = "offseason"
        elif "pov-rice-in" in rel_text:
            season = "inseason"
        else:
            season = "unknown"

        value_cols = [col for col in df.columns if col not in id_cols]
        long = df.melt(
            id_vars=["date", "address", "latitude", "longitude"],
            value_vars=value_cols,
            var_name="variety",
            value_name="area",
        )
        long["area"] = pd.to_numeric(long["area"], errors="coerce").fillna(0)
        long = long[long["area"] > 0].copy()
        if long.empty:
            continue

        long["province"] = long["address"].astype(str).str.strip()
        long["datetime"] = pd.to_datetime(long["date"], errors="coerce")
        long["month"] = long["datetime"].dt.month
        long["year"] = _infer_year(path)
        long["season"] = season
        total = long.groupby(["province", "datetime", "season"])["area"].transform("sum")
        long["ratio"] = long["area"] / total.replace({0: pd.NA})
        long["source_file"] = path.name
        rows.append(
            long[
                [
                    "province",
                    "datetime",
                    "year",
                    "month",
                    "season",
                    "variety",
                    "area",
                    "ratio",
                    "latitude",
                    "longitude",
                    "source_file",
                ]
            ]
        )

    if not rows:
        raise ValueError(f"No updated POV CSV files found under {root}")
    return pd.concat(rows, ignore_index=True).dropna(subset=["province", "datetime", "variety"])


def updated_pov_to_weekly_variety_ratio(pov_monthly_long: pd.DataFrame) -> pd.DataFrame:
    """
    Expand monthly updated POV composition to weekly province-variety ratios.

    Each monthly row is forward-filled to the weeks in that month. This preserves
    monthly source granularity while producing weekly features for the sequence
    dataset.
    """
    required = ["province", "datetime", "season", "variety", "area", "ratio"]
    missing = [col for col in required if col not in pov_monthly_long.columns]
    if missing:
        raise ValueError(f"Updated POV dataframe missing required columns: {missing}")

    rows = []
    for row in pov_monthly_long.itertuples(index=False):
        start = pd.Timestamp(row.datetime)
        if pd.isna(start):
            continue
        month_end = start + pd.offsets.MonthEnd(0)
        week_dates = pd.date_range(start=start, end=month_end, freq="W-SUN")
        if len(week_dates) == 0:
            week_dates = pd.DatetimeIndex([month_end.to_period("W-SUN").end_time.normalize()])
        for week_date in week_dates:
            rows.append(
                {
                    "province": row.province,
                    "datetime": week_date.normalize(),
                    "season": row.season,
                    "variety": row.variety,
                    "variety_area_mean": float(row.area),
                    "variety_ratio_mean": float(row.ratio) if pd.notna(row.ratio) else 0.0,
                    "pov_source_month": start,
                }
            )
    if not rows:
        raise ValueError("No weekly POV rows could be created from updated monthly POV")
    return pd.DataFrame(rows)


def load_bus_daily(folder_path: str | Path) -> pd.DataFrame:
    """Load updated daily BUS files from rice research/seed centers."""
    root = Path(folder_path)
    rows = []
    for path in root.rglob("*.csv"):
        df = _read_csv_fallback(path)
        required = {"date", "address", "latitude", "longitude", "maxbus", "minbus", "avgbus"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"{path} missing required columns: {sorted(missing)}")
        rel_parts = path.relative_to(root).parts
        center_type = rel_parts[0] if rel_parts else "unknown"
        out = df[["date", "address", "latitude", "longitude", "maxbus", "minbus", "avgbus"]].copy()
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out["location"] = out["address"].astype(str).str.strip()
        out["center_type"] = center_type
        out["year"] = _infer_year(path)
        for col in ["maxbus", "minbus", "avgbus", "latitude", "longitude"]:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        out["bus_critical_day"] = (out["avgbus"] >= BUS_CRITICAL_THRESHOLD).astype(int)
        out["source_file"] = path.name
        rows.append(out)

    if not rows:
        raise ValueError(f"No BUS CSV files found under {root}")
    return pd.concat(rows, ignore_index=True).dropna(subset=["date", "location"])


def bus_to_weekly_features(bus_daily: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate BUS daily values to center-week features.

    This intentionally keeps center/location identity. Province-level use should
    be a later explicit spatial join decision because BUS coverage is center-based.
    """
    required = {"date", "location", "center_type", "maxbus", "minbus", "avgbus", "bus_critical_day"}
    missing = required - set(bus_daily.columns)
    if missing:
        raise ValueError(f"BUS dataframe missing required columns: {sorted(missing)}")

    out = bus_daily.copy()
    out["datetime"] = week_ending_sunday(out["date"])
    weekly = (
        out.groupby(["location", "center_type", "datetime"], dropna=False)
        .agg(
            bus_observed_days=("avgbus", "count"),
            avgbus_mean=("avgbus", "mean"),
            avgbus_max=("avgbus", "max"),
            maxbus_max=("maxbus", "max"),
            minbus_min=("minbus", "min"),
            bus_critical_days=("bus_critical_day", "sum"),
            bus_critical_any=("bus_critical_day", "max"),
            latitude=("latitude", "first"),
            longitude=("longitude", "first"),
        )
        .reset_index()
    )
    weekly["bus_critical_ratio"] = weekly["bus_critical_days"] / weekly["bus_observed_days"]
    weekly["year"] = weekly["datetime"].dt.year
    weekly["week"] = weekly["datetime"].dt.isocalendar().week.astype(int)
    return weekly
