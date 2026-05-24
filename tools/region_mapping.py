from __future__ import annotations

import pandas as pd


PROVINCE_REGION = {
    # North
    "Chiang Mai": "North",
    "Chiang Rai": "North",
    "Lampang": "North",
    "Lamphun": "North",
    "Mae Hong Son": "North",
    "Nan": "North",
    "Phayao": "North",
    "Phrae": "North",
    "Uttaradit": "North",
    "Tak": "North",
    "Sukhothai": "North",
    "Phitsanulok": "North",
    "Phichit": "North",
    "Kamphaeng Phet": "North",
    "Phetchabun": "North",
    "Nakhon Sawan": "North",
    "Uthai Thani": "North",
    # Northeast
    "Amnat Charoen": "Northeast",
    "Bueng Kan": "Northeast",
    "Buri Ram": "Northeast",
    "Chaiyaphum": "Northeast",
    "Kalasin": "Northeast",
    "Khon Kaen": "Northeast",
    "Loei": "Northeast",
    "Maha Sarakham": "Northeast",
    "Mukdahan": "Northeast",
    "Nakhon Phanom": "Northeast",
    "Nakhon Ratchasima": "Northeast",
    "Nong Bua Lam Phu": "Northeast",
    "Nong Khai": "Northeast",
    "Roi Et": "Northeast",
    "Sakon Nakhon": "Northeast",
    "Si Sa Ket": "Northeast",
    "Surin": "Northeast",
    "Ubon Ratchathani": "Northeast",
    "Udon Thani": "Northeast",
    "Yasothon": "Northeast",
    # Central
    "Ang Thong": "Central",
    "Bangkok": "Central",
    "Chai Nat": "Central",
    "Lop Buri": "Central",
    "Nakhon Pathom": "Central",
    "Nonthaburi": "Central",
    "Pathum Thani": "Central",
    "Phra Nakhon Si Ayutthaya": "Central",
    "Samut Prakarn": "Central",
    "Samut Sakhon": "Central",
    "Samut Songkhram": "Central",
    "Saraburi": "Central",
    "Sing Buri": "Central",
    "Suphan Buri": "Central",
    # East
    "Chachoengsao": "East",
    "Chanthaburi": "East",
    "Chon Buri": "East",
    "Nakhon Nayok": "East",
    "Prachin Buri": "East",
    "Rayong": "East",
    "Sa kaeo": "East",
    "Trat": "East",
    # West
    "Kanchanaburi": "West",
    "Phetchaburi": "West",
    "Prachuap Khiri Khan": "West",
    "Ratchaburi": "West",
    # South
    "Chumphon": "South",
    "Krabi": "South",
    "Nakhon Si Thammarat": "South",
    "Narathiwat": "South",
    "Pattani": "South",
    "Phang-nga": "South",
    "Phatthalung": "South",
    "Phuket": "South",
    "Ranong": "South",
    "Satun": "South",
    "Songkhla": "South",
    "Surat Thani": "South",
    "Trang": "South",
    "Yala": "South",
}


def add_region(df: pd.DataFrame, province_col: str = "province") -> pd.DataFrame:
    """Attach broad Thai region labels to a dataframe with province names."""
    if province_col not in df.columns:
        raise ValueError(f"Missing province column: {province_col}")

    out = df.copy()
    out["region"] = out[province_col].map(PROVINCE_REGION).fillna("Unknown")
    return out


def region_table() -> pd.DataFrame:
    return pd.DataFrame(
        [{"province": province, "region": region} for province, region in PROVINCE_REGION.items()]
    ).sort_values(["region", "province"])
