"""
features.py
特徵工程：為每間觀光旅館建立預測特徵（星等、客房規模、旅客結構、營收結構等）
"""

import pandas as pd
import numpy as np
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def build_all_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1. 旅館規模分類
    if "total_rooms" in df.columns:
        df["total_rooms"] = pd.to_numeric(df["total_rooms"], errors="coerce").fillna(df["total_rooms"].median())
        df["is_large_hotel"] = (df["total_rooms"] >= 300).astype(int)
        df["is_small_hotel"] = (df["total_rooms"] < 100).astype(int)

    # 2. 星級特徵
    df["star_rank_filled"] = df["star_rank"].fillna(0)
    df["is_5star_plus"] = (df["star_rank_filled"] >= 5).astype(int)
    df["is_4star"] = (df["star_rank_filled"] == 4).astype(int)
    df["is_3star"] = (df["star_rank_filled"] == 3).astype(int)
    df["is_non_star"] = (df["has_star"] == 0).astype(int)

    # 3. 旅客結構補值
    for col in ["domestic_ratio", "international_ratio", "individual_ratio"]:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    # 4. 營收特徵
    if "room_revenue" in df.columns and "total_revenue" in df.columns:
        df["room_rev_ratio"] = np.where(df["total_revenue"] > 0, df["room_revenue"] / df["total_revenue"], 0.6)
    else:
        df["room_rev_ratio"] = 0.6

    # 5. 每員工服務客房數 (人效比)
    if "total_rooms" in df.columns and "employees" in df.columns:
        emp = df["employees"].fillna(50).replace(0, 50)
        df["rooms_per_employee"] = df["total_rooms"] / emp

    # 6. 房價分級
    if "avg_price" in df.columns:
        df["avg_price"] = pd.to_numeric(df["avg_price"], errors="coerce").fillna(df["avg_price"].median())
        df["is_luxury_price"] = (df["avg_price"] >= 6000).astype(int)
        df["is_budget_price"] = (df["avg_price"] < 3000).astype(int)

    # 7. 地區特徵（主要觀光都市 One-Hot）
    for city in ["台北市", "新北市", "台中市", "高雄市", "宜蘭縣", "花蓮縣", "南投縣", "屏東縣"]:
        df[f"is_{city}"] = (df["city"] == city).astype(int)

    return df


def get_feature_columns() -> list[str]:
    return [
        "avg_price", "total_rooms", "star_rank_filled", "has_star",
        "is_5star_plus", "is_4star", "is_3star", "is_non_star",
        "domestic_ratio", "international_ratio", "individual_ratio",
        "room_rev_ratio", "rooms_per_employee",
        "is_luxury_price", "is_budget_price", "is_large_hotel",
        "is_台北市", "is_新北市", "is_台中市", "is_高雄市",
        "is_宜蘭縣", "is_花蓮縣", "is_南投縣", "is_屏東縣",
    ]


if __name__ == "__main__":
    df_raw = pd.read_csv(PROCESSED_DIR / "hotel_combined.csv")
    df_feat = build_all_features(df_raw)
    out_path = PROCESSED_DIR / "hotel_features.csv"
    df_feat.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"特徵工程完成！儲存至：{out_path}")
    print(f"可用特徵數：{len(get_feature_columns())}")
