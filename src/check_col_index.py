import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

df = pd.read_excel("data/raw/hotel_2023.xlsx", header=None)
print("Row 65 (headers):", [f"Col{i}:{val}" for i, val in enumerate(df.iloc[65]) if pd.notna(val)])
print("Row 66 (values):", [f"Col{i}:{val}" for i, val in enumerate(df.iloc[66]) if pd.notna(val)])
