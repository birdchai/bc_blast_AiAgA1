from __future__ import annotations

import pandas as pd


DEFAULT_SUSCEPTIBILITY = 0.50

SUSCEPTIBILITY_WEIGHTS_V0 = {
    ("offseason", "พิษณุโลก2,60-2"): 0.70,
    ("inseason", "กข15"): 0.65,
    ("inseason", "ขาวดอกมะลิ105"): 0.65,
    ("inseason", "กข6"): 0.50,
    ("offseason", "กข6"): 0.50,
    ("offseason", "พิษณุโลก2,60-2"): 0.70,
    ("inseason", "กข15"): 0.65,
    ("inseason", "ขาวดอกมะลิ105"): 0.65,
    ("inseason", "กข6"): 0.50,
    ("offseason", "กข6"): 0.50,
}


def get_variety_susceptibility(
    season: str,
    variety: str,
    weights: dict[tuple[str, str], float] | None = None,
    default: float = DEFAULT_SUSCEPTIBILITY,
) -> float:
    """Return conservative susceptibility v0 weight for one season-variety."""
    lookup = weights or SUSCEPTIBILITY_WEIGHTS_V0
    return lookup.get((season, variety), default)


def compute_weekly_susceptibility(
    weekly_pov: pd.DataFrame,
    weights: dict[tuple[str, str], float] | None = None,
    default: float = DEFAULT_SUSCEPTIBILITY,
) -> pd.DataFrame:
    """
    Compute province-week host susceptibility from POV area shares.

    The score is an area-weighted average of variety weights. Unknown and
    unstable varieties use the conservative default 0.50.
    """
    required = ["province", "datetime", "season", "variety", "variety_area_mean"]
    missing = [col for col in required if col not in weekly_pov.columns]
    if missing:
        raise ValueError(f"Missing required weekly POV columns: {missing}")

    out = weekly_pov.copy()
    out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce")
    out["variety_area_mean"] = pd.to_numeric(
        out["variety_area_mean"],
        errors="coerce",
    ).fillna(0)
    out = out.dropna(subset=["province", "datetime", "season", "variety"])
    out = out[out["variety_area_mean"] > 0].copy()

    out["variety_susceptibility"] = [
        get_variety_susceptibility(
            season=row.season,
            variety=row.variety,
            weights=weights,
            default=default,
        )
        for row in out.itertuples(index=False)
    ]
    out["weighted_susceptibility_area"] = (
        out["variety_area_mean"] * out["variety_susceptibility"]
    )

    weekly = (
        out.groupby(["province", "datetime"])
        .agg(
            total_pov_area=("variety_area_mean", "sum"),
            weighted_susceptibility_area=("weighted_susceptibility_area", "sum"),
            pov_variety_count=("variety", "nunique"),
        )
        .reset_index()
    )
    weekly["susceptibility_score"] = (
        weekly["weighted_susceptibility_area"] / weekly["total_pov_area"]
    ).fillna(default)

    return weekly[
        [
            "province",
            "datetime",
            "susceptibility_score",
            "total_pov_area",
            "pov_variety_count",
        ]
    ]


def add_host_weighted_scores(
    weekly_risk: pd.DataFrame,
    weekly_susceptibility: pd.DataFrame,
    default: float = DEFAULT_SUSCEPTIBILITY,
) -> pd.DataFrame:
    """
    Join susceptibility into weekly weather risk and create host-weighted scores.

    The modifier is centered on 0.50 so default susceptibility leaves weather
    risk unchanged. A score of 0.70 increases risk by 20%; 0.45 reduces it by 5%.
    """
    required_risk = ["province", "datetime", "risk_score", "rolling_2w_risk", "rolling_3w_risk"]
    missing_risk = [col for col in required_risk if col not in weekly_risk.columns]
    if missing_risk:
        raise ValueError(f"Missing required weekly risk columns: {missing_risk}")

    required_host = ["province", "datetime", "susceptibility_score"]
    missing_host = [col for col in required_host if col not in weekly_susceptibility.columns]
    if missing_host:
        raise ValueError(f"Missing required susceptibility columns: {missing_host}")

    out = weekly_risk.merge(
        weekly_susceptibility,
        on=["province", "datetime"],
        how="left",
    )
    out["susceptibility_score"] = out["susceptibility_score"].fillna(default)
    out["host_modifier"] = 1 + (out["susceptibility_score"] - default)

    out["host_weighted_risk"] = out["risk_score"] * out["host_modifier"]
    out["host_weighted_rolling_2w"] = out["rolling_2w_risk"] * out["host_modifier"]
    out["host_weighted_rolling_3w"] = out["rolling_3w_risk"] * out["host_modifier"]

    return out
