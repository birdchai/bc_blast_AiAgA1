import pandas as pd


def transform_pov(df):

    id_cols = ["date", "address", "latitude", "longitude"]
    value_cols = [c for c in df.columns if c not in id_cols]

    df_long = df.melt(
        id_vars=id_cols,
        value_vars=value_cols,
        var_name="variety",
        value_name="area"
    )

    df_long = df_long[df_long["area"] > 0]

    return df_long


def compute_variety_ratio(df_long):

    df_long = df_long.copy()

    total = df_long.groupby(["date", "address"])["area"].transform("sum")

    df_long["ratio"] = df_long["area"] / total

    return df_long