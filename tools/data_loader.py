import glob
import os
import pandas as pd


def load_weather_data(folder_path: str) -> pd.DataFrame:
    files = glob.glob(os.path.join(folder_path, "**", "*.csv"), recursive=True)
    
    print(f"\n=== TOTAL FILES FOUND: {len(files)} ===")
    print("Example files:", files[:5])

    dfs = []

    for file_path in files:
        try:
            df = pd.read_csv(file_path)

            # keep needed weather columns if they exist
            required_cols = [
                "address",
                "datetime",
                "temp",
                "humidity",
                "precip",
                "wspd",
                "wgust",
                "wdir",
                "dew",
                "cloudcover",
                "sealevelpressure",
            ]
            available_cols = [c for c in required_cols if c in df.columns]
            df = df[available_cols].copy()

            # rename to standard schema
            df = df.rename(
                columns={
                    "address": "province",
                    "temp": "temperature",
                    "precip": "rainfall",
                }
            )

            # attach source file for debugging
            df["source_file"] = os.path.basename(file_path)

            dfs.append(df)

        except Exception as e:
            print(f"Failed to read {file_path}: {e}")

    if not dfs:
        raise ValueError("No weather CSV files could be loaded.")

    combined = pd.concat(dfs, ignore_index=True)

    return combined
