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


def audit_files() -> pd.DataFrame:
    rows = []
    for path in UPDATED_DIR.rglob("*.csv"):
        rel = path.relative_to(UPDATED_DIR)
        parts = rel.parts
        category = parts[0] if parts else "unknown"
        rows.append(
            {
                "category": category,
                "relative_path": str(rel),
                "year": infer_year(path),
                "size_bytes": path.stat().st_size,
                "parent": str(rel.parent),
            }
        )
    return pd.DataFrame(rows)


def read_sample(path: Path) -> dict:
    result = {
        "sample_file": str(path.relative_to(UPDATED_DIR)),
        "read_ok": False,
        "encoding": None,
        "columns": None,
        "sample_rows": None,
        "error": None,
    }
    for encoding in ["utf-8-sig", "utf-8", "cp874"]:
        try:
            df = pd.read_csv(path, encoding=encoding, nrows=5)
            result.update(
                {
                    "read_ok": True,
                    "encoding": encoding,
                    "columns": "|".join(df.columns.astype(str).tolist()),
                    "sample_rows": len(df),
                    "error": None,
                }
            )
            return result
        except Exception as exc:
            result["error"] = str(exc)
    return result


def sample_schemas(files: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for category, group in files.groupby("category"):
        for year, year_group in group.groupby("year", dropna=False):
            sample_path = UPDATED_DIR / year_group.iloc[0]["relative_path"]
            row = read_sample(sample_path)
            row["category"] = category
            row["year"] = year
            rows.append(row)
    return pd.DataFrame(rows)


def category_summary(files: pd.DataFrame) -> pd.DataFrame:
    return (
        files.groupby(["category", "year"], dropna=False)
        .agg(
            file_count=("relative_path", "count"),
            total_size_mb=("size_bytes", lambda s: round(s.sum() / (1024 * 1024), 3)),
            min_size_bytes=("size_bytes", "min"),
            max_size_bytes=("size_bytes", "max"),
        )
        .reset_index()
        .sort_values(["category", "year"])
    )


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    OUTPUT_DIR.mkdir(exist_ok=True)
    files = audit_files()
    summary = category_summary(files)
    schemas = sample_schemas(files)

    files_path = OUTPUT_DIR / "updated_data_file_inventory.csv"
    summary_path = OUTPUT_DIR / "updated_data_category_summary.csv"
    schemas_path = OUTPUT_DIR / "updated_data_schema_samples.csv"

    files.to_csv(files_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    schemas.to_csv(schemas_path, index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 80)

    print("\n=== UPDATED DATA SUMMARY ===")
    print(summary.to_string(index=False))

    print("\n=== SCHEMA SAMPLES ===")
    print(schemas[["category", "year", "sample_file", "read_ok", "encoding", "columns"]].to_string(index=False))

    print("\n=== OUTPUT FILES ===")
    print(files_path)
    print(summary_path)
    print(schemas_path)


if __name__ == "__main__":
    main()
