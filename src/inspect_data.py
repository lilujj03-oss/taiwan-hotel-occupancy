import pandas as pd
from pathlib import Path
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

raw_dir = Path("data/raw")
for f in sorted(raw_dir.glob("hotel_*.xlsx")):
    if f.name.startswith("~"):
        continue
    print(f"\n{'='*30} {f.name} {'='*30}")
    # Read first 10 rows without header
    df_preview = pd.read_excel(f, header=None, nrows=8)
    for idx, row in df_preview.iterrows():
        non_nulls = [f"Col{i}:{str(val).strip()}" for i, val in enumerate(row) if pd.notna(val)]
        print(f"Row {idx}: {', '.join(non_nulls[:10])}")
