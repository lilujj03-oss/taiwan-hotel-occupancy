r"""
check_panel_stability.py
檢查「涵蓋旅館數逐年變動（122→120→117）」是否影響月度模型的驗證指標。

三項檢查：
  1. 逐年旅館清單比對 —— 消失／新增的旅館是真的歇業，還是改名／改品牌／延遲申報
  2. 平衡樣本對照 —— 只取「2023–2025 三年都在」的旅館，重算 2026 上半年回測 MAE/RMSE/R²，
     與全樣本比較，看指標是否被樣本變動灌水
  3. 分層誤差 —— 依客房規模、縣市拆分 2026 上半年回測誤差

輸出：reports/panel_stability_check.json，並在終端機列印摘要。
執行：.\venv\Scripts\python.exe src\check_panel_stability.py
"""

from pathlib import Path
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MONTHLY = ROOT / "data" / "processed" / "hotel_monthly.csv"
ROLLING = ROOT / "reports" / "monthly_2026h1_rolling_backtest.csv"
FIXED = ROOT / "reports" / "monthly_2026h1_fixed_backtest.csv"
OUT = ROOT / "reports" / "panel_stability_check.json"


def norm(name: object) -> str:
    return "".join(str(name).splitlines()[0].split()).strip("*#")


def metrics(frame: pd.DataFrame) -> dict:
    err = frame["error"].to_numpy(dtype=float)
    actual = frame["actual_occupancy"].to_numpy(dtype=float)
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((actual - actual.mean()) ** 2))
    return {
        "n": int(len(err)),
        "hotels": int(frame["key"].nunique()),
        "MAE": round(float(np.mean(np.abs(err))), 2),
        "RMSE": round(float(np.sqrt(np.mean(err ** 2))), 2),
        "bias": round(float(np.mean(err)), 2),
        "R2": round(1 - ss_res / ss_tot, 4) if ss_tot else None,
    }


def main() -> None:
    monthly = pd.read_csv(MONTHLY)
    monthly["key"] = monthly["hotel_name"].map(norm)
    year_sets = {y: set(monthly.loc[monthly["year"] == y, "key"]) for y in (2023, 2024, 2025)}
    balanced = year_sets[2023] & year_sets[2024] & year_sets[2025]
    room_median = monthly.groupby("key")["total_rooms"].median()

    presence = {
        "hotels_per_year": {str(y): len(s) for y, s in year_sets.items()},
        "left_2023_to_2024": sorted(year_sets[2023] - year_sets[2024]),
        "left_2024_to_2025": sorted(year_sets[2024] - year_sets[2025]),
        "new_in_2025_vs_2023": sorted(year_sets[2025] - year_sets[2023]),
        "present_all_three_years": len(balanced),
    }

    report: dict = {"presence": presence, "backtests": {}}

    for path, label in ((ROLLING, "rolling_one_month"), (FIXED, "fixed_six_month")):
        data = pd.read_csv(path)
        data["key"] = data["hotel_name"].map(norm)
        data["in_balanced"] = data["key"].isin(balanced)
        data["rooms"] = data["key"].map(room_median)

        block = {
            "all": metrics(data),
            "balanced_panel": metrics(data[data["in_balanced"]]),
            "unbalanced_only": (
                metrics(data[~data["in_balanced"]]) if (~data["in_balanced"]).any() else None
            ),
            "by_room_size": {},
            "by_city": {},
        }

        data["size_group"] = pd.qcut(data["rooms"], 3, labels=["小型", "中型", "大型"])
        for group, sub in data.groupby("size_group", observed=True):
            stats = metrics(sub)
            stats["median_rooms"] = round(float(sub["rooms"].median()), 0)
            block["by_room_size"][str(group)] = stats

        for city, sub in data.groupby("city"):
            if len(sub) >= 20:
                block["by_city"][str(city)] = metrics(sub)

        report["backtests"][label] = block

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # 終端摘要
    print(f"逐年旅館數：{presence['hotels_per_year']}  三年都在：{presence['present_all_three_years']} 間")
    for label, block in report["backtests"].items():
        print(f"\n[{label}]")
        print(f"  全樣本      MAE {block['all']['MAE']}  RMSE {block['all']['RMSE']}  R2 {block['all']['R2']}  (hotels {block['all']['hotels']})")
        print(f"  平衡樣本    MAE {block['balanced_panel']['MAE']}  RMSE {block['balanced_panel']['RMSE']}  R2 {block['balanced_panel']['R2']}  (hotels {block['balanced_panel']['hotels']})")
        if block["unbalanced_only"]:
            u = block["unbalanced_only"]
            print(f"  中途進出者  MAE {u['MAE']}  RMSE {u['RMSE']}  (hotels {u['hotels']}, n {u['n']})")
        print("  按規模:", {k: v["MAE"] for k, v in block["by_room_size"].items()})
        worst = sorted(block["by_city"].items(), key=lambda kv: kv[1]["MAE"], reverse=True)[:3]
        print("  誤差最大縣市:", [(c, m["MAE"]) for c, m in worst])
    print(f"\n已寫出 {OUT}")


if __name__ == "__main__":
    main()
