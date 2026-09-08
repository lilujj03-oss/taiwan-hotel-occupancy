import pandas as pd
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

for f in sorted(Path("data/raw").glob("hotel_*.xlsx")):
    if f.name.startswith("~"):
        continue
    df = pd.read_excel(f, header=3)
    print(f"\n{'='*20} {f.name} (Total rows: {len(df)}) {'='*20}")
    print("Columns:", df.columns.tolist()[:10])
    # Show first 15 unique values of first column
    col0 = df.columns[0]
    print(f"Col 0 ({col0}) sample unique values:")
    print(df[col0].dropna().unique()[:20])
    # Check if there are hotel names in other columns
    for c in df.columns:
        sample_vals = df[c].dropna().astype(str).tolist()[:5]
        # print non-numeric samples
        if any(not v.replace('.','',1).isdigit() for v in sample_vals):
            print(f"  Col '{c}' sample non-num:", sample_vals[:3])
