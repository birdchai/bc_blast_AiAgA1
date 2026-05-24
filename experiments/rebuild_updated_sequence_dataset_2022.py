from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from experiments.rebuild_updated_sequence_dataset import (
    OUTPUT_DIR,
    SEQUENCE_COLUMNS,
    build_year_sequence,
    bus_feature_summary,
    feature_integrity,
    label_distribution,
    old_new_label_comparison_with_region,
    pov_ratio_summary,
    prepare_updated_sources,
    summarize_sequence,
    susceptibility_summary,
)


YEARS = list(range(2015, 2023))


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    OUTPUT_DIR.mkdir(exist_ok=True)

    sources = prepare_updated_sources()

    frames = []
    for year in YEARS:
        print(f"\n=== BUILD UPDATED 2022 SEQUENCE {year} ===")
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
        "region_temporal_sequence_dataset_updated_labels_2015_2022.csv": sequences,
        "updated_2022_sequence_dataset_summary.csv": summarize_sequence(sequences),
        "updated_2022_label_distribution_summary.csv": label_distribution(sequences),
        "updated_2022_feature_integrity_summary.csv": feature_integrity(sequences),
        "updated_2022_old_vs_new_label_comparison.csv": old_new_label_comparison_with_region(),
        "updated_2022_pov_variety_ratio_summary.csv": pov_ratio_summary(sources["pov_monthly"]),
        "updated_2022_susceptibility_summary.csv": susceptibility_summary(sources["weekly_susceptibility"]),
        "updated_2022_bus_feature_summary.csv": bus_feature_summary(sequences),
    }
    for filename, df in outputs.items():
        df.to_csv(OUTPUT_DIR / filename, index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 80)
    print("\n=== UPDATED 2022 SEQUENCE SUMMARY ===")
    print(outputs["updated_2022_sequence_dataset_summary.csv"].to_string(index=False))
    print("\n=== UPDATED 2022 BUS FEATURE SUMMARY ===")
    print(outputs["updated_2022_bus_feature_summary.csv"].to_string(index=False))
    print("\n=== OUTPUT FILES ===")
    for filename in outputs:
        print(OUTPUT_DIR / filename)


if __name__ == "__main__":
    main()
