from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from tools.blast_model_v1 import blast_to_weekly, load_blast_data
from tools.updated_data_loaders import (
    BUS_CRITICAL_THRESHOLD,
    bus_to_weekly_features,
    load_bus_daily,
    load_updated_blast_outbreak_weekly,
)


OUTPUT_DIR = BASE_DIR / "experiments" / "outputs"


def load_old_weekly_labels(year: int) -> pd.DataFrame:
    folder = BASE_DIR / "data" / "blast disease" / f"Blast_data_{year}"
    blast = load_blast_data(str(folder))
    weekly = blast_to_weekly(blast)
    weekly["year"] = weekly["datetime"].dt.year
    weekly["week"] = weekly["datetime"].dt.isocalendar().week.astype(int)
    return weekly


def compare_labels() -> tuple[pd.DataFrame, pd.DataFrame]:
    updated = load_updated_blast_outbreak_weekly(UPDATED_BLAST_DIR)
    frames = []
    for year in range(2016, 2022):
        old = load_old_weekly_labels(year)
        old = old[["province", "datetime", "blast_any", "blast_days"]].rename(
            columns={"blast_any": "blast_any_old", "blast_days": "blast_days_old"}
        )
        new = updated.loc[updated["source_year"] == year, ["province", "datetime", "blast_any", "blast_area", "outbreak_reports", "source_year"]].rename(
            columns={"blast_any": "blast_any_updated"}
        )
        joined = old.merge(new, on=["province", "datetime"], how="outer", indicator=True)
        joined["year"] = year
        joined["blast_any_old"] = joined["blast_any_old"].fillna(0).astype(int)
        joined["blast_any_updated"] = joined["blast_any_updated"].fillna(0).astype(int)
        joined["label_agree"] = joined["blast_any_old"] == joined["blast_any_updated"]
        joined["old_positive_updated_negative"] = (joined["blast_any_old"] == 1) & (joined["blast_any_updated"] == 0)
        joined["old_negative_updated_positive"] = (joined["blast_any_old"] == 0) & (joined["blast_any_updated"] == 1)
        frames.append(joined)

    comparison = pd.concat(frames, ignore_index=True)
    summary = (
        comparison.groupby("year")
        .agg(
            joined_rows=("province", "count"),
            old_positive=("blast_any_old", "sum"),
            updated_positive=("blast_any_updated", "sum"),
            agreed_rows=("label_agree", "sum"),
            old_positive_updated_negative=("old_positive_updated_negative", "sum"),
            old_negative_updated_positive=("old_negative_updated_positive", "sum"),
            old_only_rows=("_merge", lambda s: int((s == "left_only").sum())),
            updated_only_rows=("_merge", lambda s: int((s == "right_only").sum())),
        )
        .reset_index()
    )
    summary["agreement_rate"] = summary["agreed_rows"] / summary["joined_rows"]
    return summary, comparison.sort_values(["year", "province", "datetime"])


def summarize_bus() -> tuple[pd.DataFrame, pd.DataFrame]:
    bus_root = BASE_DIR / "updated data" / "bus_value_daily"
    if not bus_root.exists():
        bus_root = BASE_DIR / "updated data" / "bus_value_dayly"
    bus = load_bus_daily(bus_root)
    weekly = bus_to_weekly_features(bus)
    summary = (
        weekly.groupby(["year", "center_type"], dropna=False)
        .agg(
            rows=("location", "count"),
            locations=("location", "nunique"),
            date_min=("datetime", "min"),
            date_max=("datetime", "max"),
            mean_avgbus=("avgbus_mean", "mean"),
            max_avgbus=("avgbus_max", "max"),
            critical_weeks=("bus_critical_any", "sum"),
            mean_critical_ratio=("bus_critical_ratio", "mean"),
        )
        .reset_index()
        .sort_values(["year", "center_type"])
    )
    summary["critical_threshold"] = BUS_CRITICAL_THRESHOLD
    return summary, weekly.sort_values(["year", "location", "datetime"])


UPDATED_BLAST_DIR = BASE_DIR / "updated data" / "rice_blast_outbreak_weekly"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    OUTPUT_DIR.mkdir(exist_ok=True)

    label_summary, label_comparison = compare_labels()
    bus_summary, bus_weekly = summarize_bus()

    outputs = {
        "updated_vs_old_blast_label_summary.csv": label_summary,
        "updated_vs_old_blast_label_comparison.csv": label_comparison,
        "bus_weekly_feature_summary.csv": bus_summary,
        "bus_weekly_features.csv": bus_weekly,
    }
    for filename, df in outputs.items():
        df.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 80)
    print("\n=== LABEL COMPARISON SUMMARY ===")
    print(label_summary.to_string(index=False))
    print("\n=== BUS WEEKLY SUMMARY ===")
    print(bus_summary.to_string(index=False))
    print("\n=== OUTPUT FILES ===")
    for filename in outputs:
        print(OUTPUT_DIR / filename)


if __name__ == "__main__":
    main()
