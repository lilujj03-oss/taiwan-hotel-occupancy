"""用三段式新模型的 2026H1 滾動回測，重算旅館進出面板穩健性檢查（取代舊版 panel_stability_check.json）。"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed" / "hotel_monthly.csv"
ROLLING = ROOT / "reports" / "monthly_2026h1_rolling_backtest_3way.csv"
FIXED = ROOT / "reports" / "monthly_2026h1_fixed_backtest_3way.csv"
OUT = ROOT / "reports" / "panel_stability_check_3way.json"

HOTEL_NAME_ALIASES = {"礁溪老爺大酒店": "礁溪老爺酒店", "寒舍艾麗酒店": "台北艾麗酒店"}


def summarize(frame):
    a, p = frame["actual_occupancy"], frame["predicted_occupancy"]
    err = p - a
    ss_res = (err ** 2).sum()
    ss_tot = ((a - a.mean()) ** 2).sum()
    return {
        "n": int(len(frame)),
        "hotels": int(frame["hotel_name"].nunique()),
        "MAE": round(float(err.abs().mean()), 2),
        "RMSE": round(float((err ** 2).mean() ** 0.5), 2),
        "bias": round(float(err.mean()), 2),
        "R2": round(float(1 - ss_res / ss_tot), 4) if ss_tot > 0 else None,
    }


def main():
    raw = pd.read_csv(DATA)
    raw["clean_hotel_name"] = raw["hotel_name"].str.strip().replace(HOTEL_NAME_ALIASES)
    by_year = raw.groupby(["year", "clean_hotel_name"]).size().reset_index()
    present = {y: set(by_year.loc[by_year["year"] == y, "clean_hotel_name"]) for y in (2023, 2024, 2025)}
    balanced_set = present[2023] & present[2024] & present[2025]

    rolling = pd.read_csv(ROLLING)
    rolling["clean_hotel_name"] = rolling["hotel_name"].str.strip().replace(HOTEL_NAME_ALIASES)
    fixed = pd.read_csv(FIXED)
    fixed["clean_hotel_name"] = fixed["hotel_name"].str.strip().replace(HOTEL_NAME_ALIASES)

    rolling_balanced = rolling[rolling["clean_hotel_name"].isin(balanced_set)]
    rolling_unbalanced = rolling[~rolling["clean_hotel_name"].isin(balanced_set)]

    by_city = {
        city: summarize(group)
        for city, group in rolling.groupby("city")
    }
    by_room_size = {}
    if "total_rooms" in raw.columns:
        latest_rooms = raw.sort_values(["clean_hotel_name", "year", "month"]).groupby(
            "clean_hotel_name")["total_rooms"].last()
        rolling2 = rolling.copy()
        rolling2["room_bin"] = pd.cut(
            rolling2["clean_hotel_name"].map(latest_rooms),
            bins=[0, 80, 150, 250, 10000], labels=["<80", "80-150", "150-250", "250+"],
        )
        by_room_size = {str(k): summarize(g) for k, g in rolling2.groupby("room_bin", observed=True)}

    fixed_by_city = {city: summarize(group) for city, group in fixed.groupby("city")}

    payload = {
        "presence": {
            "hotels_per_year": {str(y): len(present[y]) for y in (2023, 2024, 2025)},
            "present_all_three_years": len(balanced_set),
        },
        "backtests": {
            "rolling_one_month": {
                "all": summarize(rolling),
                "balanced_panel": summarize(rolling_balanced),
                "unbalanced_only": summarize(rolling_unbalanced),
                "by_city": by_city,
                "by_room_size": by_room_size,
            },
            "fixed_six_month": {
                "by_city": fixed_by_city,
            },
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"寫出 {OUT}")
    print(f"  balanced={payload['backtests']['rolling_one_month']['balanced_panel']}")
    print(f"  unbalanced={payload['backtests']['rolling_one_month']['unbalanced_only']}")


if __name__ == "__main__":
    main()
