import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
from pathlib import Path

df_raw = pd.read_excel("data/raw/hotel_2023.xlsx", header=None)
print(f"Total rows in 2023: {len(df_raw)}")

split_idx = len(df_raw)
for idx, row in df_raw.iterrows():
    text = " ".join([str(x) for x in row.values if pd.notna(x)])
    if idx > 50 and ("住客類別統計" in text or "各地區旅客人數統計" in text):
        print(f"Found split at row {idx}: {text[:60]}")
        split_idx = idx
        break

print(f"split_idx = {split_idx}")
part1 = df_raw.iloc[:split_idx]
print(f"Part 1 length: {len(part1)}")
