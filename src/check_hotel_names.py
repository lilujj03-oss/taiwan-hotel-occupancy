import pandas as pd
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_excel("data/raw/hotel_2023.xlsx", header=None)
print("Previewing Rows 60 to 95 of hotel_2023.xlsx:")
for idx in range(60, 95):
    if idx < len(df):
        vals = [str(x) for x in df.iloc[idx].values if pd.notna(x)]
        print(f"Row {idx:3d}: {' | '.join(vals[:6])}")
