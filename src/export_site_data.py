"""把三段式模型的預測與驗證結果打包成單一 JSON，給新的網頁版儀表板使用。"""

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from predict import predict_monthly_occupancy

DATA = ROOT / "data" / "processed" / "hotel_monthly.csv"
MODEL = ROOT / "models" / "monthly_model_3way.pkl"
RESULTS = ROOT / "reports" / "model_results_monthly_3way.json"
METADATA = ROOT / "reports" / "monthly_model_3way_metadata.json"
VALIDATION = ROOT / "reports" / "monthly_2026h1_validation_3way.json"
PERMUTATION = ROOT / "reports" / "permutation_importance_monthly_3way.csv"
FIXED = ROOT / "reports" / "monthly_2026h1_fixed_backtest_3way.csv"
OUT = ROOT / "reports" / "site_data_3way.json"

FEATURE_LABELS = {
    "occupancy_roll3": "近 3 月平均住房率",
    "occupancy_lag_1": "前 1 月住房率",
    "occupancy_lag_2": "前 2 月住房率",
    "occupancy_lag_3": "前 3 月住房率",
    "occupancy_lag_12": "去年同月住房率",
    "input_employees": "員工數",
    "input_total_rooms": "客房數",
    "input_avg_price": "平均房價 ADR",
    "input_domestic_ratio": "本國旅客比例",
    "input_international_ratio": "國際旅客比例",
    "input_individual_ratio": "散客比例",
    "month": "月份",
    "month_sin": "月份季節性（sin）",
    "month_cos": "月份季節性（cos）",
    "city": "縣市",
    "star_rating": "星級",
}


def load_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def main():
    raw = pd.read_csv(DATA)
    raw["clean_hotel_name"] = raw["hotel_name"].astype(str).str.split("\n").str[0].str.strip("*# ")
    raw["date"] = pd.to_datetime(dict(year=raw.year, month=raw.month, day=1))
    raw = raw[raw["clean_hotel_name"].ne("")].copy()

    model = joblib.load(MODEL)
    metadata = load_json(METADATA)
    results = load_json(RESULTS)
    validation = load_json(VALIDATION)
    perm = pd.read_csv(PERMUTATION)
    fixed = pd.read_csv(FIXED)
    fixed["date"] = pd.to_datetime(fixed["date"])
    fixed["clean_hotel_name"] = fixed["hotel_name"].astype(str).str.split("\n").str[0].str.strip("*# ")

    latest_date = raw["date"].max()
    latest_rows = raw[raw["date"] == latest_date]
    hotels = sorted(latest_rows["clean_hotel_name"].dropna().unique())

    hotel_payload = {}
    for i, hotel in enumerate(hotels, 1):
        history = raw[raw["clean_hotel_name"] == hotel].sort_values("date")
        if history.empty or history["occupancy_rate"].isna().all():
            continue
        latest = history.iloc[-1]
        try:
            result = predict_monthly_occupancy(
                model, raw, hotel,
                int((latest_date + pd.DateOffset(months=1)).month),
                target_year=int((latest_date + pd.DateOffset(months=1)).year),
            )
        except Exception as exc:
            print(f"跳過 {hotel}：{exc}")
            continue
        trends = result["monthly_trends"]
        back = fixed[fixed["clean_hotel_name"] == hotel].sort_values("date")
        hist_tail = history.tail(24)
        hotel_payload[hotel] = {
            "city": str(latest["city"]),
            "star": str(latest.get("star_rating", "")),
            "rooms": None if pd.isna(latest["total_rooms"]) else int(latest["total_rooms"]),
            "adr": None if pd.isna(latest["avg_price"]) else int(round(float(latest["avg_price"]))),
            "employees": None if pd.isna(latest["employees"]) else int(latest["employees"]),
            "history": [
                {"m": d.strftime("%Y-%m"), "occ": None if pd.isna(o) else round(float(o), 1)}
                for d, o in zip(hist_tail["date"], hist_tail["occupancy_rate"])
            ],
            "forecast": [
                {"m": pd.Timestamp(d).strftime("%Y-%m"), "occ": float(v)}
                for d, v in zip(trends["月份日期"], trends["📅 月平均住房率"])
            ],
            "backtest": [
                {"m": d.strftime("%Y-%m"), "actual": round(float(a), 1), "pred": round(float(p), 1)}
                for d, a, p in zip(back["date"], back["actual_occupancy"], back["predicted_occupancy"])
            ],
            "backtest_mae": round(float(back["absolute_error"].mean()), 2) if not back.empty else None,
            "prev_month": None if pd.isna(result["previous_month_occupancy"]) else float(result["previous_month_occupancy"]),
            "prev_year": None if pd.isna(result["previous_year_occupancy"]) else float(result["previous_year_occupancy"]),
        }
        if i % 25 == 0:
            print(f"  已處理 {i}/{len(hotels)}")

    perm_top = perm.head(10)
    perm_out = [
        {"feature": FEATURE_LABELS.get(r.feature, r.feature), "mae_increase": round(float(r.mae_increase), 3)}
        for r in perm_top.itertuples()
    ]

    city_rows = sorted(
        ({"city": c, **v} for c, v in validation["by_city"].items()),
        key=lambda r: r["mae"], reverse=True,
    )

    monthly_overall = fixed.groupby("date").agg(
        actual=("actual_occupancy", "mean"), pred=("predicted_occupancy", "mean"),
        mae=("absolute_error", "mean"), n=("hotel_name", "nunique")).reset_index()

    payload = {
        "generated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "latest_actual": latest_date.strftime("%Y-%m"),
        "metadata": metadata,
        "candidates_validation": results["validation_selection"],
        "final_test": results["final_test"],
        "validation": {
            "test": validation["rolling_one_month"],
            "baseline": validation["baseline"],
            "improve_pp": validation["improve_pp"],
            "improve_pct": validation["improve_pct"],
            "improve_ci": [validation["improve_ci_lo"], validation["improve_ci_hi"]],
            "horizon": validation["fixed_origin_by_horizon"],
            "fixed_overall": validation["fixed_origin_overall"],
        },
        "by_city": city_rows,
        "permutation": perm_out,
        "monthly_overall": [
            {"m": d.strftime("%Y-%m"), "actual": round(a, 2), "pred": round(p, 2), "mae": round(e, 2), "n": int(n)}
            for d, a, p, e, n in zip(monthly_overall["date"], monthly_overall["actual"],
                                      monthly_overall["pred"], monthly_overall["mae"], monthly_overall["n"])
        ],
        "hotels": hotel_payload,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"寫出 {OUT}，{len(hotel_payload)} 間旅館，{OUT.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
