import pandas as pd


def parse_datetime(df: pd.DataFrame, datetime_col: str = "datetime") -> pd.DataFrame:
    df = df.copy()
    df[datetime_col] = pd.to_datetime(
        df[datetime_col],
        format="%m/%d/%Y %H:%M:%S",   # 👈 สำคัญมาก
        errors="coerce"
    )

    return df
