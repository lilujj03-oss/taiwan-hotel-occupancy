"""
predict.py
單筆預測函式：輸入旅館屬性、月份、平日/假日情境，預測住房率、財務指標與 3 大營運方案範例
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
import joblib
from pathlib import Path

from features import get_feature_columns

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

# 台灣觀光業月度季節性指數 (1~12月)
MONTH_FACTORS = {
    1: 0.98,   # 寒假前期 / 尾牙
    2: 1.18,   # 農曆春節 / 寒假高峰
    3: 0.88,   # 年後淡季
    4: 1.04,   # 清明連假 / 春季出遊
    5: 0.92,   # 報稅月 / 梅雨淡季
    6: 0.98,   # 端午節 / 暑假前夕
    7: 1.22,   # 暑假大旺季 (上半年高峰)
    8: 1.25,   # 暑假大旺季
    9: 0.86,   # 開學淡季
    10: 1.10,  # 國慶中秋連假 / 秋季出遊
    11: 0.90,  # 傳統淡季
    12: 1.15,  # 聖誕跨年 / 冬季溫泉
}


def load_model(model_name: str = "decision_tree"):
    model_path = MODELS_DIR / f"{model_name}.pkl"
    if not model_path.exists():
        for p in MODELS_DIR.glob("*.pkl"):
            return joblib.load(p)
        raise FileNotFoundError(f"找不到模型：{model_path}")
    return joblib.load(model_path)


def predict_occupancy(
    model,
    hotel_name: str = "自訂飯店",
    star_rank: int = 4,
    total_rooms: int = 200,
    city: str = "台北市",
    avg_price: float = 4500,
    domestic_ratio: float = 0.65,
    individual_ratio: float = 0.60,
    employees: int = 80,
    month: int = 7,
    day_type: str = "📅 全月常態平均",
    **kwargs
) -> dict:
    star_rank_filled = star_rank if star_rank > 0 else 0
    has_star = 1 if star_rank > 0 else 0
    intl_ratio = 1.0 - domestic_ratio

    # 判斷是否為主要休閒度假觀光縣市
    is_resort_city = city in ["宜蘭縣", "花蓮縣", "南投縣", "屏東縣", "台東縣", "澎湖縣", "金門縣", "嘉義縣"]

    # 平日／假日乘數與房價調整
    if "平日" in day_type:
        occ_mult = 0.82 if is_resort_city else 0.95
        price_adj = avg_price * (0.88 if is_resort_city else 0.96)
        scenario_tag = "平日時段（週日～週四）"
    elif "假日" in day_type:
        occ_mult = 1.28 if is_resort_city else 1.12
        price_adj = avg_price * (1.25 if is_resort_city else 1.12)
        scenario_tag = "週末假日時段（週五～週六）"
    elif "連假" in day_type or "旺季" in day_type:
        occ_mult = 1.38 if is_resort_city else 1.20
        price_adj = avg_price * (1.35 if is_resort_city else 1.20)
        scenario_tag = "連續假期 / 國定假日大旺季"
    else:
        occ_mult = 1.0
        price_adj = avg_price
        scenario_tag = "全月常態平均"

    # 月份季節性因子
    m_factor = MONTH_FACTORS.get(int(month), 1.0)

    row_dict = {
        "avg_price": price_adj,
        "total_rooms": total_rooms,
        "star_rank_filled": star_rank_filled,
        "has_star": has_star,
        "is_5star_plus": 1 if star_rank >= 5 else 0,
        "is_4star": 1 if star_rank == 4 else 0,
        "is_3star": 1 if star_rank == 3 else 0,
        "is_non_star": 1 if star_rank == 0 else 0,
        "domestic_ratio": domestic_ratio,
        "international_ratio": intl_ratio,
        "individual_ratio": individual_ratio,
        "room_rev_ratio": 0.60,
        "rooms_per_employee": total_rooms / max(1, employees),
        "is_luxury_price": 1 if price_adj >= 6000 else 0,
        "is_budget_price": 1 if price_adj < 3000 else 0,
        "is_large_hotel": 1 if total_rooms >= 300 else 0,
        "is_台北市": 1 if city == "台北市" else 0,
        "is_新北市": 1 if city == "新北市" else 0,
        "is_台中市": 1 if city == "台中市" else 0,
        "is_高雄市": 1 if city == "高雄市" else 0,
        "is_宜蘭縣": 1 if city == "宜蘭縣" else 0,
        "is_花蓮縣": 1 if city == "花蓮縣" else 0,
        "is_南投縣": 1 if city == "南投縣" else 0,
        "is_屏東縣": 1 if city == "屏東縣" else 0,
    }

    feature_cols = get_feature_columns()
    X = pd.DataFrame([row_dict])[feature_cols]
    base_pred = model.predict(X)[0]

    # 套用月份季節性與平日/假日調整
    adjusted_pred = base_pred * m_factor * occ_mult
    final_pred = max(8.0, min(98.5, adjusted_pred))

    # 預估 RevPAR
    revpar_val = round(price_adj * final_pred / 100, 0)

    # 決策建議與 3 大方案範例
    if final_pred >= 75:
        level = "🟢 供不應求（高住房率 / 旺季榮景）"
        advice = f"在【{month}月 - {scenario_tag}】預估住房率達到 {final_pred:.1f}%。市場需求強勁，當前策略核心為「收益極大化（Yield Maximization）」與「動態溢價管制」。"
        packages = [
            {
                "tag": "方案 1：動態階梯溢價管制 (Surge Pricing)",
                "icon": "📈",
                "color": "#38bdf8",
                "desc": "監控即時訂房進度，實施階梯式溢價以極大化 RevPAR 收益。",
                "example": f"• 實戰範例：當全館預訂率達 75% 時即刻調升房價 15%（由 NT${price_adj:,.0f} 調至 NT${price_adj*1.15:,.0f}）；達 90% 時調升 25%，全面關閉早鳥與低價代碼。",
                "benefit": "預估提升客房總營收 +12% ~ +18%，推升 RevPAR 創下波段新高。"
            },
            {
                "tag": "方案 2：最低連住天數管制 (MLOS Strategy)",
                "icon": "🔒",
                "color": "#f59e0b",
                "desc": "針對週六或連假峰值，強制實施最低入住 2 晚以上管制 (Minimum Length of Stay)。",
                "example": "• 實戰範例：週六入住強制鎖定『週五+週六』或『週六+週日』雙宿專案，杜絕單日零散空房導致前後相鄰日期滯銷。",
                "benefit": "拉升週五與週日之離峰住房率 +20%~30%，徹底消除零散空房損失。"
            },
            {
                "tag": "方案 3：頂級奢華尊榮專案 (VIP Luxury Bundle)",
                "icon": "👑",
                "color": "#a855f7",
                "desc": "鎖定高預算度假客與商務菁英，推出高單價附加價值套裝，突破房價天花板。",
                "example": f"• 實戰範例：包裝『頂級景觀套房＋雙人米其林星級晚餐＋奢華 SPA 水療＋專車接送』高價專案（定價 NT${max(12000.0, price_adj*2.2):,.0f}）。",
                "benefit": "有效拉高 ADR 平均房價，提升高單價房型坪效與餐飲延伸收益。"
            }
        ]
    elif final_pred >= 55:
        level = "🟡 營運穩健（中等住房率 / 常規表現）"
        advice = f"在【{month}月 - {scenario_tag}】預估住房率約 {final_pred:.1f}%。營運維持常態，策略核心為「強化散客直訂、減少 OTA 抽成並延伸住宿週期」。"
        packages = [
            {
                "tag": "方案 1：官網直訂尊榮升等 (Direct Booking Perks)",
                "icon": "🎁",
                "color": "#38bdf8",
                "desc": "提供專屬禮遇吸引旅客由 Agoda/Booking 轉向官網直訂，省下高額平台佣金。",
                "example": "• 實戰範例：官網直訂即享『免費延遲退房至 14:00＋迎賓無酒精特調＋館內餐飲 85 折』，贈送低成本高感知之附加服務。",
                "benefit": "省下 15%~18% OTA 抽成手續費，並將顧客沉澱為飯店忠誠私域會員。"
            },
            {
                "tag": "方案 2：多晚連住 Staycation (Multi-Night Stay)",
                "icon": "🏖️",
                "color": "#22c55e",
                "desc": "針對自由行旅客推出續住折扣，填補週四與週日的離峰空窗期。",
                "example": f"• 實戰範例：推出『連住 2 晚享第 2 晚 6 折』或『住 3 晚付 2 晚』，吸引國旅渡假客與遠距工作者延長停留天數。",
                "benefit": "有效提升平日與週日連帶住房率 +10%~15%，降低頻繁翻房之清潔人力成本。"
            },
            {
                "tag": "方案 3：高階房型動態加價升級 (Upsell Engine)",
                "icon": "✨",
                "color": "#f59e0b",
                "desc": "在入住前 48 小時主動行銷，引導已訂購標準房之旅客升級高價房型。",
                "example": "• 實戰範例：入住前發送簡訊/Email：『加價 NT$ 999 即可享行政樓層免費升等含 Lounge 貴賓廊下午茶』。",
                "benefit": "釋出低價標準房重新販售，同時提升全館客單價與顧客住宿體驗。"
            }
        ]
    else:
        level = "🔴 預警警戒（低住房率風險 / 淡季低谷）"
        advice = f"在【{month}月 - {scenario_tag}】受淡季或平日影響，住房率預估降至 {final_pred:.1f}%。策略核心為「跨界餐飲包套、活化日間閒置資產並啟動企業團客防線」。"
        packages = [
            {
                "tag": "方案 1：一泊二食＋餐飲全額抵用 (F&B Credit Package)",
                "icon": "🍽️",
                "color": "#38bdf8",
                "desc": "將未售出之客房邊際成本包裝為餐飲吸引力，主攻美食國旅客群。",
                "example": f"• 實戰範例：推出『平日入住每房 NT${price_adj:,.0f}，加碼贈送 NT$ 1,500 館內餐廳抵用券（或雙人自助晚餐）』，吸引在地居民美食微度假。",
                "benefit": "將空房機會成本轉化為餐飲實質業績，預估可帶動平日住房率 +15%~25%。"
            },
            {
                "tag": "方案 2：企業會議與日間辦公 Day-Use (MICE / Day-Pass)",
                "icon": "💼",
                "color": "#f59e0b",
                "desc": "將日間 (09:00–18:00) 閒置客房與會議室包裝為日間商務與共享辦公空間。",
                "example": "• 實戰範例：推出『日間微辦公專案（09:00-18:00 使用客房＋免費高速 WiFi＋雙人咖啡下午茶組，定價 NT$ 1,600）』或『企業 20 人包套會議專案』。",
                "benefit": "在不影響夜間住宿前提下活化白天閒置空間，每日額外創造數萬元非客房收益。"
            },
            {
                "tag": "方案 3：高鐵聯票與在地遊程早鳥跨界 (Early-Bird Tie-up)",
                "icon": "🚄",
                "color": "#ec4899",
                "desc": "提前鎖定跨縣市計畫型自由行散客，異業結合交通與觀光門票。",
                "example": "• 實戰範例：與台灣高鐵合作『加購高鐵車票享 7 折』，並搭贈在地熱門展覽／風景區門票，限提前 21 天早鳥預訂。",
                "benefit": "提前 3~4 週鎖定基本盤客源，降低臨時未成行之棄單風險。"
            }
        ]

    # 產出全年 12 個月份的預測走勢 (平日 vs 假日)
    monthly_trends = []
    for m in range(1, 13):
        mf = MONTH_FACTORS.get(m, 1.0)
        # 平日
        w_mult = 0.82 if is_resort_city else 0.95
        p_weekday = max(8.0, min(98.5, base_pred * mf * w_mult))
        # 假日
        h_mult = 1.28 if is_resort_city else 1.12
        p_weekend = max(8.0, min(98.5, base_pred * mf * h_mult))
        # 平均
        p_avg = max(8.0, min(98.5, base_pred * mf))

        monthly_trends.append({
            "月份": f"{m}月",
            "月份數值": m,
            "☀️ 平日預估住房率": round(p_weekday, 1),
            "🎉 假日預估住房率": round(p_weekend, 1),
            "📅 月平均住房率": round(p_avg, 1),
        })

    return {
        "hotel_name": hotel_name,
        "month": month,
        "day_type": day_type,
        "scenario_tag": scenario_tag,
        "adjusted_price": round(price_adj, 0),
        "predicted_occupancy": round(final_pred, 1),
        "level": level,
        "advice": advice,
        "packages": packages,
        "revpar_estimate": revpar_val,
        "monthly_trends": pd.DataFrame(monthly_trends),
    }


def predict_monthly_occupancy(model, monthly_df, hotel_name, target_month,
                              target_year=None, day_type="📅 全月常態平均",
                              avg_price=None, total_rooms=None, employees=None,
                              domestic_ratio=None, individual_ratio=None,
                              star_rank=None, city=None):
    """依指定旅館的已知歷史，遞迴預測未來月份住房率。"""
    data = monthly_df.copy()
    if "clean_hotel_name" not in data.columns:
        data["clean_hotel_name"] = data["hotel_name"].astype(str).str.split("\n").str[0].str.strip("*# ")
    subset = data[data["clean_hotel_name"] == hotel_name].copy()
    if subset.empty:
        subset = data[data["hotel_name"] == hotel_name].copy()
    if subset.empty:
        raise ValueError(f"找不到旅館月度資料：{hotel_name}")

    subset["date"] = pd.to_datetime(dict(year=subset.year, month=subset.month, day=1))
    subset = subset.sort_values("date").drop_duplicates("date", keep="last")
    latest = subset.iloc[-1]
    latest_date = pd.Timestamp(latest["date"])
    target_month = int(target_month)
    if target_year is None:
        target_year = latest_date.year + int(target_month <= latest_date.month)
    target_date = pd.Timestamp(year=int(target_year), month=target_month, day=1)
    if target_date <= latest_date:
        raise ValueError(
            f"預測月份必須晚於最新實際月份 {latest_date:%Y-%m}，目前選擇 {target_date:%Y-%m}"
        )

    actual_city = city if city else latest.get("city", "未知")
    actual_star = star_rank if star_rank is not None else latest.get("star_rank", 0)
    actual_star = 0 if pd.isna(actual_star) else int(actual_star)
    actual_price = avg_price if avg_price is not None else latest.get("avg_price", np.nan)
    actual_rooms = total_rooms if total_rooms is not None else latest.get("total_rooms", np.nan)
    actual_employees = employees if employees is not None else latest.get("employees", np.nan)
    actual_domestic = domestic_ratio if domestic_ratio is not None else latest.get("domestic_ratio", np.nan)
    actual_fit = individual_ratio if individual_ratio is not None else latest.get("individual_ratio", np.nan)
    star_label = {6: "卓越五星", 5: "五星級", 4: "四星級", 3: "三星級"}.get(actual_star, "無星等/未評鑑")

    known_occupancy = {
        pd.Timestamp(row.date): float(row.occupancy_rate)
        for row in subset[["date", "occupancy_rate"]].itertuples(index=False)
        if pd.notna(row.occupancy_rate)
    }

    def history_value(forecast_date, months):
        return known_occupancy.get(forecast_date - pd.DateOffset(months=months), np.nan)

    def make_input(forecast_date):
        lags = [history_value(forecast_date, months) for months in (1, 2, 3)]
        return {
            "month": forecast_date.month,
            "month_sin": np.sin(2 * np.pi * forecast_date.month / 12),
            "month_cos": np.cos(2 * np.pi * forecast_date.month / 12),
            "total_rooms": actual_rooms,
            "employees": actual_employees,
            "avg_price": actual_price,
            "domestic_ratio": actual_domestic,
            "international_ratio": 1 - actual_domestic if pd.notna(actual_domestic) else np.nan,
            "individual_ratio": actual_fit,
            # v2 月度模型以預測前可取得／使用者規劃的營運值為輸入，
            # 避免在回測時使用預測當月結束後才知道的實際資料。
            "input_total_rooms": actual_rooms,
            "input_employees": actual_employees,
            "input_avg_price": actual_price,
            "input_domestic_ratio": actual_domestic,
            "input_international_ratio": 1 - actual_domestic if pd.notna(actual_domestic) else np.nan,
            "input_individual_ratio": actual_fit,
            "occupancy_lag_1": lags[0],
            "occupancy_lag_2": lags[1],
            "occupancy_lag_3": lags[2],
            "occupancy_lag_12": history_value(forecast_date, 12),
            "occupancy_roll3": np.nanmean(lags) if any(pd.notna(value) for value in lags) else np.nan,
            "city": actual_city,
            "star_rating": star_label,
        }

    # 至少建立未來 12 個月，讓趨勢圖每個月份使用各自正確的 lag。
    forecast_end = max(target_date, latest_date + pd.DateOffset(months=12))
    trends = []
    forecast_date = latest_date + pd.DateOffset(months=1)
    while forecast_date <= forecast_end:
        value = float(np.clip(model.predict(pd.DataFrame([make_input(forecast_date)]))[0], 0, 100))
        known_occupancy[forecast_date] = value
        trends.append({
            "月份": forecast_date.strftime("%Y-%m"),
            "月份日期": forecast_date,
            "月份數值": forecast_date.month,
            "📅 月平均住房率": round(value, 1),
        })
        forecast_date += pd.DateOffset(months=1)

    pred = known_occupancy[target_date]

    # 保留相容參數；月模型沒有日型特徵，不以日型任意改動住房率。
    price_factor = 1.0
    if "平日" in day_type:
        price_factor = 0.92
    elif "假日" in day_type:
        price_factor = 1.12
    elif "連假" in day_type or "旺季" in day_type:
        price_factor = 1.20
    adjusted_price = float(actual_price) * price_factor if pd.notna(actual_price) else 0.0

    if pred >= 75:
        level = "🟢 高住房率"
        advice = f"月度模型預估 {target_date:%Y-%m} 住房率為 {pred:.1f}%，可優先採取收益最大化與房價分級策略。"
    elif pred >= 55:
        level = "🟡 中等住房率"
        advice = f"月度模型預估 {target_date:%Y-%m} 住房率為 {pred:.1f}%，建議維持基本房價並加強直訂與連住方案。"
    else:
        level = "🔴 低住房率預警"
        advice = f"月度模型預估 {target_date:%Y-%m} 住房率為 {pred:.1f}%，建議提早啟動平日促銷與團體客源方案。"

    days_in_month = target_date.days_in_month
    sold_room_nights = float(actual_rooms) * days_in_month * pred / 100 if pd.notna(actual_rooms) else np.nan
    room_revenue_estimate = sold_room_nights * adjusted_price if pd.notna(sold_room_nights) else np.nan
    previous_month = history_value(target_date, 1)
    previous_year = history_value(target_date, 12)
    recent_three = [history_value(target_date, months) for months in (1, 2, 3)]
    recent_three = np.nanmean(recent_three) if any(pd.notna(value) for value in recent_three) else np.nan

    return {
        "hotel_name": hotel_name,
        "month": target_month,
        "year": int(target_date.year),
        "target_date": target_date,
        "latest_actual_date": latest_date,
        "latest_actual_occupancy": round(float(latest["occupancy_rate"]), 1),
        "previous_month_occupancy": round(float(previous_month), 1) if pd.notna(previous_month) else np.nan,
        "previous_year_occupancy": round(float(previous_year), 1) if pd.notna(previous_year) else np.nan,
        "recent_three_occupancy": round(float(recent_three), 1) if pd.notna(recent_three) else np.nan,
        "predicted_occupancy": round(pred, 1),
        "level": level,
        "advice": advice,
        "packages": [],
        "adjusted_price": round(adjusted_price, 0),
        "revpar_estimate": round(adjusted_price * pred / 100, 0),
        "sold_room_nights": round(sold_room_nights, 0) if pd.notna(sold_room_nights) else np.nan,
        "room_revenue_estimate": round(room_revenue_estimate, 0) if pd.notna(room_revenue_estimate) else np.nan,
        "monthly_trends": pd.DataFrame(trends),
        "model_note": "住房率使用前 1、2、3、12 個月與近 3 月平均等特徵；超過下一個月的結果會遞迴使用前期預測值，距離越遠不確定性越高。",
    }


if __name__ == "__main__":
    model = load_model("decision_tree")
    res = predict_occupancy(model, "台北君悅酒店", star_rank=5, total_rooms=850, city="台北市", avg_price=6800, month=8, day_type="🎉 週末假日時段（週五～週六）")
    print("預測測試：", res["predicted_occupancy"], res["level"])
    print("方案範例：", len(res["packages"]))
