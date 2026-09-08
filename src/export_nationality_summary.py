"""
export_nationality_summary.py
從原始資料中提取並輸出完整的「全台觀光旅館住客國籍分佈總表」CSV 檔
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
from pathlib import Path

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

all_records = []

for year in [2023, 2024, 2025]:
    f = RAW_DIR / f"hotel_{year}.xlsx"
    df_raw = pd.read_excel(f, header=None)

    # 尋找 Part 2 分割點
    split_idx = len(df_raw)
    for idx, row in df_raw.iterrows():
        text = " ".join([str(x) for x in row.values if pd.notna(x)])
        if idx > 50 and ("住客類別統計" in text or "各地區旅客人數統計" in text):
            split_idx = idx
            break

    part2_df = df_raw.iloc[split_idx:].copy()

    # 解析各國籍欄位
    for idx, row in part2_df.iterrows():
        first_val = str(row.iloc[0]).strip()
        # 抓取個別旅館列（排除總計、小計等）
        if (first_val and first_val not in ["旅館名稱", "地區名稱", "總計", "小計", "國際", "一般", "合計", "nan", ""]
            and not first_val.startswith("觀光旅館營運")
            and not first_val.startswith("列印日期")
            and not first_val.startswith("Data for")):

            hname = first_val.lstrip("*# ")
            fit_guests = pd.to_numeric(row.iloc[2], errors="coerce") if len(row) > 2 else 0
            group_guests = pd.to_numeric(row.iloc[3], errors="coerce") if len(row) > 3 else 0
            total_guests = pd.to_numeric(row.iloc[4], errors="coerce") if len(row) > 4 else 0

            domestic = pd.to_numeric(row.iloc[5], errors="coerce") if len(row) > 5 else 0
            china = pd.to_numeric(row.iloc[6], errors="coerce") if len(row) > 6 else 0
            japan = pd.to_numeric(row.iloc[7], errors="coerce") if len(row) > 7 else 0
            korea = pd.to_numeric(row.iloc[8], errors="coerce") if len(row) > 8 else 0
            hk_mo = pd.to_numeric(row.iloc[9], errors="coerce") if len(row) > 9 else 0
            singapore = pd.to_numeric(row.iloc[10], errors="coerce") if len(row) > 10 else 0
            malaysia = pd.to_numeric(row.iloc[11], errors="coerce") if len(row) > 11 else 0
            thailand = pd.to_numeric(row.iloc[12], errors="coerce") if len(row) > 12 else 0
            usa = pd.to_numeric(row.iloc[23], errors="coerce") if len(row) > 23 else 0
            europe = pd.to_numeric(row.iloc[27], errors="coerce") if len(row) > 27 else 0

            all_records.append({
                "年份": year,
                "旅館名稱": hname,
                "散客人數(FIT)": fit_guests,
                "團體客人數(Group)": group_guests,
                "住客總人次": total_guests,
                "本國旅客": domestic,
                "日本": japan,
                "美國": usa,
                "南韓": korea,
                "港澳": hk_mo,
                "新加坡": singapore,
                "馬來西亞": malaysia,
                "泰國": thailand,
                "中國大陸": china,
                "歐洲地區": europe,
            })

df_all = pd.DataFrame(all_records)

# 1. 輸出個別旅館國籍詳細清單
detail_path = PROCESSED_DIR / "hotel_guest_nationality_detail.csv"
df_all.to_csv(detail_path, index=False, encoding="utf-8-sig")

# 2. 彙整各國籍歷年總計與佔比表
nat_cols = ["本國旅客", "日本", "美國", "南韓", "港澳", "新加坡", "馬來西亞", "泰國", "中國大陸", "歐洲地區"]
summary_df = df_all.groupby("年份")[nat_cols].sum().T

# 計算三年總計與佔比
summary_df["三年合計人次"] = summary_df.sum(axis=1)
grand_total = df_all["住客總人次"].sum()
summary_df["全台佔比(%)"] = (summary_df["三年合計人次"] / grand_total * 100).round(2)
summary_df = summary_df.sort_values("三年合計人次", ascending=False)

summary_path = PROCESSED_DIR / "guest_nationality_summary.csv"
summary_df.to_csv(summary_path, encoding="utf-8-sig")

print("=== 全台觀光旅館住客國籍分佈總表 ===")
print(summary_df.to_string())
print(f"\n已匯出檔案：\n1. {summary_path}\n2. {detail_path}")
