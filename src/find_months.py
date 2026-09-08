import pandas as pd
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

for year in [2023, 2024, 2025]:
    f = Path(f"data/raw/hotel_{year}.xlsx")
    df = pd.read_excel(f, header=None)
    # Find all rows containing '月' in first 15 columns
    month_rows = []
    for idx, row in df.iterrows():
        text = " ".join([str(x) for x in row.values if pd.notna(x)])
        if "資料期間" in text or "Data for" in text or "月份" in text:
            month_rows.append((idx, text[:80]))
    print(f"\n{year} Month headers found ({len(month_rows)}):")
    for r in month_rows[:15]:
        print(f"  Row {r[0]:3d}: {r[1]}")
