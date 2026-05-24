import pandas as pd


def weather_to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # drop rows with invalid datetime
    df = df.dropna(subset=["datetime"])

    # numeric conversion
    for col in ["temperature", "humidity", "rainfall"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["province", "temperature", "humidity", "rainfall"])

    df = df.set_index("datetime")

    weekly = (
        df.groupby("province")
        .resample("W")
        .agg(
            {
                "temperature": "mean",
                "humidity": "mean",
                "rainfall": "sum",
            }
        )
        .reset_index()
    )

    return weekly