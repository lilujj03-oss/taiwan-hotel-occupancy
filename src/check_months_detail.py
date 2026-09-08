import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
from pathlib import Path

df_2023 = pd.read_excel("data/raw/hotel_2023.xlsx", header=None)

# Find all headers containing '年' and '月'
print("Scanning headers in 2023:")
for idx, row in df_2023.iterrows():
    text = " ".join([str(x) for x in row.values if pd.notna(x)])
    if "月" in text and ("1月" in text or "2月" in text or "3月" in text or "4月" in text or "5月" in text or "6月" in text or "7月" in text or "8月" in text or "9月" in text or "10月" in text or "11月" in text or "12月" in text):
        print(f"Row {idx:3d}: {text[:90]}")
