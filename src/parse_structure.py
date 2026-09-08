import pandas as pd
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

for year in [2023, 2024, 2025]:
    f = Path(f"data/raw/hotel_{year}.xlsx")
    df = pd.read_excel(f, header=None)
    print(f"\n==================== {f.name} (Shape: {df.shape}) ====================")
    # Check rows that contain '月' or month markers or hotel names
    for idx, row in df.iloc[:40].iterrows():
        r_str = [str(x) for x in row.values if pd.notna(x)]
        if len(r_str) > 0:
            print(f"Row {idx:2d}: {' | '.join(r_str[:8])}")
