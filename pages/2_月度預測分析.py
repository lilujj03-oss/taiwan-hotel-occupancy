from pathlib import Path
import json
import sys

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from predict import predict_monthly_occupancy

DATA = ROOT / "data" / "processed" / "hotel_monthly.csv"
MODEL = ROOT / "models" / "monthly_model_through_202606.pkl"
RESULTS = ROOT / "reports" / "model_results_monthly_current.json"
METADATA = ROOT / "reports" / "monthly_model_current_metadata.json"
IMPORTANCE = ROOT / "reports" / "feature_importance_monthly_current.csv"
ROLLING_BACKTEST = ROOT / "reports" / "monthly_2026h1_rolling_backtest.csv"
FIXED_BACKTEST = ROOT / "reports" / "monthly_2026h1_fixed_backtest.csv"
VALIDATION = ROOT / "reports" / "monthly_2026h1_validation.json"
CALENDAR = ROOT / "data" / "processed" / "taiwan_monthly_calendar_features.csv"
HOLIDAY_EXPERIMENT = ROOT / "reports" / "monthly_holiday_experiment_results.json"
FEATURE_LABELS = {
    "num__occupancy_roll3": "近 3 月平均住房率",
    "num__occupancy_lag_1": "前 1 月住房率",
    "num__occupancy_lag_2": "前 2 月住房率",
    "num__occupancy_lag_3": "前 3 月住房率",
    "num__occupancy_lag_12": "去年同月住房率",
    "num__input_employees": "預測前員工數",
    "num__input_total_rooms": "預測前客房數",
    "num__input_avg_price": "預測前／規劃平均房價",
    "num__input_domestic_ratio": "預測前本國旅客比例",
    "num__input_international_ratio": "預測前國際旅客比例",
    "num__input_individual_ratio": "預測前散客比例",
    "num__month": "月份",
    "num__month_sin": "月份季節性（sin）",
    "num__month_cos": "月份季節性（cos）",
}

st.set_page_config(page_title="月度住房率預測", page_icon="🗓️", layout="wide")
st.title("🗓️ 月度住房率預測分析")


@st.cache_data
def load_monthly_data():
    data = pd.read_csv(DATA)
    data["clean_hotel_name"] = data["hotel_name"].astype(str).str.split("\n").str[0].str.strip("*# ")
    data["hotel_key"] = data["hotel_name"].map(
        lambda value: "".join(str(value).splitlines()[0].split()).strip("*#")
    )
    data["date"] = pd.to_datetime(dict(year=data.year, month=data.month, day=1))
    return data[data["hotel_key"].ne("")].copy()


@st.cache_resource
def load_monthly_model():
    loaded = joblib.load(MODEL)
    # 單筆遞迴預測使用單執行緒較快，避免每個月份反覆建立平行工作池。
    estimator = loaded.named_steps.get("model") if hasattr(loaded, "named_steps") else None
    if estimator is not None and hasattr(estimator, "n_jobs"):
        estimator.n_jobs = 1
    return loaded


@st.cache_data
def load_json(path):
    if not path.exists():
        return {}
    with open(path, encoding="utf-8-sig") as file:
        return json.load(file)


@st.cache_data
def load_calendar_data():
    if not CALENDAR.exists():
        return pd.DataFrame()
    return pd.read_csv(CALENDAR, encoding="utf-8-sig")


if not DATA.exists() or not MODEL.exists():
    st.error("找不到月度資料或月度模型。")
    st.stop()

source_df = load_monthly_data()
model = load_monthly_model()
results = load_json(RESULTS)
metadata = load_json(METADATA)
validation = load_json(VALIDATION)
holiday_experiment = load_json(HOLIDAY_EXPERIMENT)
calendar_df = load_calendar_data()
model_start = pd.Timestamp(f"{metadata.get('data_start', '2023-01')}-01")
model_end = pd.Timestamp(f"{metadata.get('data_end', '2026-06')}-01")
df = source_df[source_df["date"].between(model_start, model_end)].copy()
latest_date = pd.Timestamp(df["date"].max())
latest_rows = df[df["date"] == latest_date].copy()
official_latest_date = pd.Timestamp(source_df["date"].max())

st.caption(
    f"正式模型使用 {model_start:%Y-%m}～{model_end:%Y-%m}，共 {len(df):,} 筆；"
    f"官方資料更新至 {official_latest_date:%Y-%m}，未來預測由下一個月份開始。"
)

target_dates = pd.date_range(latest_date + pd.DateOffset(months=1), periods=12, freq="MS")
hotel = st.selectbox("選擇旅館", sorted(latest_rows["clean_hotel_name"].dropna().unique()))

hotel_history = df[df["clean_hotel_name"] == hotel].sort_values("date").copy()
latest = hotel_history.iloc[-1]
default_price = int(round(float(latest["avg_price"]))) if pd.notna(latest["avg_price"]) else 4500
default_rooms = int(round(float(latest["total_rooms"]))) if pd.notna(latest["total_rooms"]) else 100
default_employees = int(round(float(latest["employees"]))) if pd.notna(latest["employees"]) else 80
default_star = int(latest["star_rank"]) if pd.notna(latest["star_rank"]) else 0

st.subheader("月度情境輸入")
i1, i2, i3 = st.columns(3)
with i1:
    target_date = st.selectbox(
        "預測目標月份",
        target_dates,
        format_func=lambda value: pd.Timestamp(value).strftime("%Y 年 %m 月"),
    )
    city = st.text_input("縣市", str(latest["city"]), key=f"monthly_city_{hotel}")
    star_rank = st.number_input(
        "星級（0 表示未評鑑）", 0, 6, default_star, 1, key=f"monthly_star_{hotel}"
    )

# 未來旅客結構沒有實際值，依既有歷史相同月份的住客人次加權平均帶入。
seasonal_rows = hotel_history[hotel_history["month"] == pd.Timestamp(target_date).month]
seasonal_guests = pd.to_numeric(seasonal_rows["total_guests"], errors="coerce").sum(min_count=1)
seasonal_domestic = pd.to_numeric(seasonal_rows["domestic_guests"], errors="coerce").sum(min_count=1)
seasonal_individual = pd.to_numeric(seasonal_rows["individual_guests"], errors="coerce").sum(min_count=1)
latest_domestic = float(np.clip(latest["domestic_ratio"], 0, 1)) if pd.notna(latest["domestic_ratio"]) else 0.6
latest_individual = float(np.clip(latest["individual_ratio"], 0, 1)) if pd.notna(latest["individual_ratio"]) else 0.6
default_domestic = (
    float(np.clip(seasonal_domestic / seasonal_guests, 0, 1))
    if pd.notna(seasonal_guests) and seasonal_guests > 0 and pd.notna(seasonal_domestic)
    else latest_domestic
)
default_individual = (
    float(np.clip(seasonal_individual / seasonal_guests, 0, 1))
    if pd.notna(seasonal_guests) and seasonal_guests > 0 and pd.notna(seasonal_individual)
    else latest_individual
)
period_key = pd.Timestamp(target_date).strftime("%Y%m")

with i2:
    total_rooms = st.number_input(
        "實際客房數", 1, 5000, default_rooms, 1, key=f"monthly_rooms_{hotel}"
    )
    employees = st.number_input(
        "員工數", 1, 5000, default_employees, 1, key=f"monthly_employees_{hotel}"
    )
    avg_price = st.number_input(
        "預期平均房價（ADR）", 500, 50000, default_price, 100, key=f"monthly_adr_{hotel}"
    )
with i3:
    domestic_ratio = st.slider(
        "本國旅客比例", 0.0, 1.0, default_domestic, 0.01,
        key=f"monthly_domestic_{hotel}_{period_key}",
    )
    individual_ratio = st.slider(
        "散客比例", 0.0, 1.0, default_individual, 0.01,
        key=f"monthly_individual_{hotel}_{period_key}",
    )
    st.caption(f"國際旅客比例：{1 - domestic_ratio:.0%}")
    st.caption(f"預設值：歷史 {pd.Timestamp(target_date).month} 月住客人次加權平均")

calendar_match = calendar_df[
    calendar_df["year"].eq(pd.Timestamp(target_date).year)
    & calendar_df["month"].eq(pd.Timestamp(target_date).month)
]
if not calendar_match.empty:
    calendar_row = calendar_match.iloc[0]
    holiday_status = (
        f"官方：放假 {int(calendar_row['day_off_days'])} 日、"
        f"3 日以上連假 {int(calendar_row['long_weekend_count'])} 個"
    )
else:
    holiday_status = "尚無該月官方辦公日曆"

event1, event2 = st.columns(2)
with event1:
    st.selectbox(
        "連假情境",
        [holiday_status],
        disabled=True,
    )
with event2:
    st.selectbox(
        "重大活動情境",
        ["尚未納入模型（待補日期、縣市與活動規模）"],
        disabled=True,
    )
st.caption(
    "連假資料來自行政院人事行政總處。假日特徵已完成回測，但尚未通過正式模型切換門檻；"
    "重大活動仍未納入，兩者都不會以任意係數改動住房率。"
)

result = predict_monthly_occupancy(
    model,
    df,
    hotel,
    int(pd.Timestamp(target_date).month),
    target_year=int(pd.Timestamp(target_date).year),
    avg_price=float(avg_price),
    total_rooms=float(total_rooms),
    employees=float(employees),
    domestic_ratio=float(domestic_ratio),
    individual_ratio=float(individual_ratio),
    star_rank=int(star_rank),
    city=str(city),
)

selected_model = metadata.get("selected_model", "Random Forest")
selected_metrics = results.get(selected_model, {})
previous_month = result["previous_month_occupancy"]
previous_year = result["previous_year_occupancy"]
forecast_horizon = (
    (pd.Timestamp(target_date).year - latest_date.year) * 12
    + pd.Timestamp(target_date).month
    - latest_date.month
)
horizon_validation = validation.get("fixed_origin_by_horizon", {})
validated_horizon = min(max(1, int(forecast_horizon)), 6)
horizon_metrics = horizon_validation.get(str(validated_horizon), {})
planning_error = float(horizon_metrics.get("planning_rmse", 8.0))
if forecast_horizon > 6:
    planning_note = (
        f"目前只有 1～6 個月實績驗證；第 {forecast_horizon} 個月暫沿用第 6 個月以上的"
        f"保守誤差下限 ±{planning_error:.2f} 個百分點。"
    )
else:
    planning_note = (
        f"此為從 {latest_date:%Y-%m} 起第 {forecast_horizon} 個月預測，"
        f"採2026上半年相同預測距離的累積最大RMSE ±{planning_error:.2f}個百分點。"
    )
conservative = max(0.0, result["predicted_occupancy"] - planning_error)
optimistic = min(100.0, result["predicted_occupancy"] + planning_error)
yoy_change = result["predicted_occupancy"] - previous_year if pd.notna(previous_year) else np.nan

seasonal_available = (
    pd.to_numeric(seasonal_rows["total_rooms"], errors="coerce")
    * seasonal_rows["date"].dt.days_in_month
).sum(min_count=1)
seasonal_sold = pd.to_numeric(seasonal_rows["rooms_used"], errors="coerce").sum(min_count=1)
same_month_average = (
    seasonal_sold / seasonal_available * 100
    if pd.notna(seasonal_available) and seasonal_available > 0 and pd.notna(seasonal_sold)
    else np.nan
)

target_days = pd.Timestamp(target_date).days_in_month
available_room_nights = float(total_rooms) * target_days

st.subheader(f"{hotel}｜{pd.Timestamp(target_date):%Y-%m} 基準預測")
m1, m2, m3, m4 = st.columns(4)
m1.metric(
    "月度住房率",
    f"{result['predicted_occupancy']:.1f}%",
    f"{yoy_change:+.1f} 個百分點 vs 去年同月" if pd.notna(yoy_change) else None,
)
m2.metric("合理規劃範圍", f"{conservative:.1f}%–{optimistic:.1f}%")
m3.metric("預期月度 ADR", f"NT${avg_price:,.0f}")
m4.metric("預期月度 RevPAR", f"NT${result['revpar_estimate']:,.0f}")

o1, o2, o3 = st.columns(3)
o1.metric("預計售出客房間夜", f"{result['sold_room_nights']:,.0f}")
o2.metric("預期月度客房收入", f"NT${result['room_revenue_estimate']:,.0f}")
o3.metric(
    "與去年同月相比",
    f"{yoy_change:+.1f} 個百分點" if pd.notna(yoy_change) else "無去年同月資料",
)

b1, b2, b3, b4, b5 = st.columns(5)
b1.metric(f"最新實際值（{result['latest_actual_date']:%Y-%m}）", f"{result['latest_actual_occupancy']:.1f}%")
b2.metric("預測前月基準", f"{previous_month:.1f}%" if pd.notna(previous_month) else "無資料")
b3.metric(
    "去年同月基準",
    f"{previous_year:.1f}%" if pd.notna(previous_year) else "無資料",
)
b4.metric(
    "歷史同月加權平均",
    f"{same_month_average:.1f}%" if pd.notna(same_month_average) else "無資料",
)
b5.metric(
    "近 3 月基準",
    f"{result['recent_three_occupancy']:.1f}%" if pd.notna(result["recent_three_occupancy"]) else "無資料",
)

scenario_table = pd.DataFrame(
    {
        "情境": ["保守", "基準", "樂觀"],
        "住房率數值": [conservative, result["predicted_occupancy"], optimistic],
    }
)
scenario_table["RevPAR數值"] = scenario_table["住房率數值"] / 100 * float(avg_price)
scenario_table["售出房晚數值"] = scenario_table["住房率數值"] / 100 * available_room_nights
scenario_table["客房收入數值"] = scenario_table["售出房晚數值"] * float(avg_price)
scenario_table["年增數值"] = scenario_table["住房率數值"] - previous_year if pd.notna(previous_year) else np.nan
scenario_display = scenario_table.copy()
scenario_display["住房率"] = scenario_display["住房率數值"].map(lambda value: f"{value:.1f}%")
scenario_display["月度 ADR"] = f"NT${avg_price:,.0f}"
scenario_display["月度 RevPAR"] = scenario_display["RevPAR數值"].map(lambda value: f"NT${value:,.0f}")
scenario_display["預計售出房晚"] = scenario_display["售出房晚數值"].map(lambda value: f"{value:,.0f}")
scenario_display["預期客房收入"] = scenario_display["客房收入數值"].map(lambda value: f"NT${value:,.0f}")
scenario_display["較去年同月"] = scenario_display["年增數值"].map(
    lambda value: f"{value:+.1f} 個百分點" if pd.notna(value) else "—"
)
st.markdown("**保守／基準／樂觀情境**")
st.dataframe(
    scenario_display[["情境", "住房率", "月度 ADR", "月度 RevPAR", "預計售出房晚", "預期客房收入", "較去年同月"]],
    width="stretch",
    hide_index=True,
)
st.caption(
    planning_note + " 屬營運壓力測試範圍，並非統計信賴區間。"
)

# ── 年度彙總：由月度模型遞迴預測未來 12 個月再加總（取代獨立年度模型的推薦作法）──
annual_window = result["monthly_trends"].copy()
annual_window["月份日期"] = pd.to_datetime(annual_window["月份日期"])
annual_window = annual_window.sort_values("月份日期").head(12)
if len(annual_window) == 12:
    annual_window["當月天數"] = annual_window["月份日期"].dt.days_in_month
    annual_window["可售房晚"] = float(total_rooms) * annual_window["當月天數"]
    annual_window["售出房晚"] = annual_window["可售房晚"] * annual_window["📅 月平均住房率"] / 100
    total_available = float(annual_window["可售房晚"].sum())
    total_sold = float(annual_window["售出房晚"].sum())
    annual_occ = total_sold / total_available * 100 if total_available > 0 else np.nan
    annual_adr = float(avg_price)
    annual_revpar = annual_occ / 100 * annual_adr if pd.notna(annual_occ) else np.nan
    annual_room_revenue = total_sold * annual_adr
    window_start = annual_window["月份日期"].min().strftime("%Y-%m")
    window_end = annual_window["月份日期"].max().strftime("%Y-%m")

    st.subheader(f"未來 12 個月年度彙總（{window_start} ~ {window_end}）")
    st.caption(
        "推薦作法：不另訓練年度模型，改由本月度模型**遞迴預測未來 12 個月再加總**。"
        "月度模型有 2026 上半年時間外驗證，但第 7～12 個月已超出已驗證距離，屬情境規劃、誤差較大。"
    )
    ya1, ya2, ya3, ya4 = st.columns(4)
    ya1.metric("年度平均住房率", f"{annual_occ:.1f}%" if pd.notna(annual_occ) else "—")
    ya2.metric("年度 ADR（沿用輸入）", f"NT${annual_adr:,.0f}")
    ya3.metric("年度 RevPAR", f"NT${annual_revpar:,.0f}" if pd.notna(annual_revpar) else "—")
    ya4.metric("年度客房營收", f"NT${annual_room_revenue:,.0f}")
    yb1, yb2 = st.columns(2)
    yb1.metric("年度可售客房間夜", f"{total_available:,.0f}")
    yb2.metric("年度預計售出客房間夜", f"{total_sold:,.0f}")
    st.caption(
        "年度平均住房率＝12 個月售出房晚合計 ÷ 可售房晚合計（依當月天數加權）；"
        "ADR 沿用上方輸入值、假設全年一致；未考慮連假、活動與房價季節性調整。"
        "「📆 年度預測分析」分頁的獨立 Decision Tree 模型（R² 約 0.40）僅供對照。"
    )

if IMPORTANCE.exists():
    importance_raw = pd.read_csv(IMPORTANCE)
    factor_values = {
        "num__occupancy_lag_1": f"{previous_month:.1f}%" if pd.notna(previous_month) else "無資料",
        "num__occupancy_roll3": f"{result['recent_three_occupancy']:.1f}%" if pd.notna(result["recent_three_occupancy"]) else "無資料",
        "num__occupancy_lag_12": f"{previous_year:.1f}%" if pd.notna(previous_year) else "無資料",
        "num__month": f"{pd.Timestamp(target_date).month} 月",
        "num__month_sin": f"{pd.Timestamp(target_date).month} 月季節位置",
        "num__month_cos": f"{pd.Timestamp(target_date).month} 月季節位置",
        "num__input_employees": f"{employees:,} 人",
        "num__input_total_rooms": f"{total_rooms:,} 間",
        "num__input_avg_price": f"NT${avg_price:,.0f}",
        "num__input_domestic_ratio": f"{domestic_ratio:.0%}",
        "num__input_international_ratio": f"{1 - domestic_ratio:.0%}",
        "num__input_individual_ratio": f"{individual_ratio:.0%}",
    }
    current_factors = importance_raw[importance_raw["feature"].isin(factor_values)].head(5).copy()
    current_factors["主要影響因素"] = current_factors["feature"].map(FEATURE_LABELS)
    current_factors["本次輸入／基準"] = current_factors["feature"].map(factor_values)
    current_factors["全域重要度"] = current_factors["importance"].map(lambda value: f"{value:.1%}")
    st.markdown("**本次預測主要影響因素**")
    st.dataframe(
        current_factors[["主要影響因素", "本次輸入／基準", "全域重要度"]],
        width="stretch",
        hide_index=True,
    )
    st.caption("重要度表示模型整體依賴程度，不代表該因素對本次預測的正向或負向因果效果。")
    st.caption(
        "⚠️ 輸入敏感度：前 1 月、近 3 月、去年同月住房率合計佔模型重要度約 94%；"
        "上方可調的預期房價、旅客結構、員工數等營運輸入合計影響 < 3%，"
        "調整這些數值時，預測住房率通常只會小幅變動。"
    )

st.info(f"{result['level']}　{result['advice']}")
st.caption(result["model_note"])

st.subheader("實際趨勢與未來 12 個月預測")
actual_chart = hotel_history.tail(18)[["date", "occupancy_rate"]].rename(
    columns={"occupancy_rate": "實際住房率"}
)
forecast_chart = result["monthly_trends"][["月份日期", "📅 月平均住房率"]].rename(
    columns={"月份日期": "date", "📅 月平均住房率": "預測住房率"}
)
trend_chart = actual_chart.merge(forecast_chart, on="date", how="outer").sort_values("date").set_index("date")
st.line_chart(trend_chart, y=["實際住房率", "預測住房率"], y_label="住房率（%）")

rolling_backtest = pd.DataFrame()
fixed_backtest = pd.DataFrame()
if ROLLING_BACKTEST.exists() and FIXED_BACKTEST.exists():
    rolling_backtest = pd.read_csv(ROLLING_BACKTEST)
    fixed_backtest = pd.read_csv(FIXED_BACKTEST)
    for frame in (rolling_backtest, fixed_backtest):
        frame["date"] = pd.to_datetime(frame["date"])
        frame["clean_hotel_name"] = (
            frame["hotel_name"].astype(str).str.split("\n").str[0].str.strip("*# ")
        )

    st.subheader("2026-01～2026-06｜預測與官方實績比較")
    st.caption(
        "回測模型只使用2023-01～2025-12訓練。滾動預測每月使用前月已知資料；"
        "固定起點預測則站在2025-12一次遞迴預測六個月，沒有使用2026實績修正後續月份。"
    )
    rolling_metrics = validation.get("rolling_one_month", {})
    fixed_metrics = validation.get("fixed_origin_overall", {})
    v1, v2, v3, v4 = st.columns(4)
    v1.metric("滾動一個月 MAE", f"{rolling_metrics.get('mae', np.nan):.2f} 個百分點")
    v2.metric("滾動一個月 R²", f"{rolling_metrics.get('r2', np.nan):.4f}")
    v3.metric("固定六個月 MAE", f"{fixed_metrics.get('mae', np.nan):.2f} 個百分點")
    v4.metric("固定六個月 R²", f"{fixed_metrics.get('r2', np.nan):.4f}")

    monthly_comparison = fixed_backtest.groupby("date", as_index=False).agg(
        實際平均住房率=("actual_occupancy", "mean"),
        預測平均住房率=("predicted_occupancy", "mean"),
        平均絕對誤差=("absolute_error", "mean"),
        平均偏差=("error", "mean"),
        旅館數=("hotel_name", "nunique"),
    )
    monthly_comparison["月份"] = monthly_comparison["date"].dt.strftime("%Y-%m")
    monthly_display = monthly_comparison.copy()
    for column in ["實際平均住房率", "預測平均住房率", "平均絕對誤差", "平均偏差"]:
        monthly_display[column] = monthly_display[column].map(lambda value: f"{value:.2f}")
    st.markdown("**固定起點六個月整體比較**")
    st.dataframe(
        monthly_display[["月份", "實際平均住房率", "預測平均住房率", "平均絕對誤差", "平均偏差", "旅館數"]],
        width="stretch",
        hide_index=True,
    )
    horizon_display = pd.DataFrame.from_dict(
        validation.get("fixed_origin_by_horizon", {}), orient="index"
    ).reset_index().rename(
        columns={"index": "預測距離（月）", "mae": "MAE", "rmse": "RMSE", "r2": "R²", "bias": "平均偏差", "n": "筆數", "planning_rmse": "規劃採用誤差"}
    )
    if not horizon_display.empty:
        st.markdown("**預測距離與誤差**")
        st.dataframe(horizon_display, width="stretch", hide_index=True)

    hotel_backtest = fixed_backtest[fixed_backtest["clean_hotel_name"] == hotel].sort_values("date")
    if not hotel_backtest.empty:
        h1, h2, h3 = st.columns(3)
        hotel_mae = hotel_backtest["absolute_error"].mean()
        hotel_bias = hotel_backtest["error"].mean()
        h1.metric("此旅館回測 MAE", f"{hotel_mae:.2f} 個百分點")
        h2.metric("此旅館平均偏差", f"{hotel_bias:+.2f} 個百分點")
        h3.metric("固定起點回測月份數", f"{len(hotel_backtest)}")
        hotel_chart = hotel_backtest.set_index("date")[["actual_occupancy", "predicted_occupancy"]].rename(
            columns={"actual_occupancy": "實際住房率", "predicted_occupancy": "回測預測住房率"}
        )
        st.line_chart(hotel_chart, y_label="住房率（%）")
    else:
        st.caption("此旅館在時間外測試期間沒有完整回測紀錄。")

    st.markdown("**縣市 × 月份固定起點平均絕對誤差（MAE）**")
    heatmap = fixed_backtest.pivot_table(
        index="city", columns="month", values="absolute_error", aggfunc="mean"
    ).reindex(columns=range(1, 7))
    heatmap = heatmap.loc[heatmap.mean(axis=1).sort_values(ascending=False).index]
    heatmap.columns = [f"{month}月" for month in heatmap.columns]
    heatmap_fig = px.imshow(
        heatmap,
        text_auto=".1f",
        aspect="auto",
        color_continuous_scale="YlOrRd",
        labels={"x": "月份", "y": "縣市", "color": "MAE"},
    )
    heatmap_fig.update_layout(height=max(480, 30 * len(heatmap)), margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(heatmap_fig, width="stretch")
    st.caption("顏色越深代表該縣市在該月份的平均預測誤差越大；固定起點預測距離越遠，通常不確定性越高。")

with st.expander("最近 12 個月官方實績", expanded=False):
    history_table = hotel_history.tail(12).copy()
    history_table["月份"] = history_table["date"].dt.strftime("%Y-%m")
    history_table["住房率"] = history_table["occupancy_rate"].map(lambda value: f"{value:.1f}%")
    history_table["ADR"] = history_table["avg_price"].map(lambda value: f"NT${value:,.0f}" if pd.notna(value) else "—")
    history_table["RevPAR"] = history_table["revpar"].map(lambda value: f"NT${value:,.0f}" if pd.notna(value) else "—")
    history_table["客房收入"] = history_table["room_revenue"].map(lambda value: f"NT${value:,.0f}")
    st.dataframe(
        history_table[["月份", "住房率", "ADR", "RevPAR", "rooms_used", "客房收入"]].rename(
            columns={"rooms_used": "已售房晚"}
        ),
        width="stretch",
        hide_index=True,
    )

with st.expander("模型評估：這個預測有多可信", expanded=True):
    model_version = metadata.get("model_version", "monthly-through-202606-v2")
    model_updated = pd.Timestamp(MODEL.stat().st_mtime, unit="s").strftime("%Y-%m-%d %H:%M")
    quality_labels = {
        "total_rooms": "客房數",
        "employees": "員工數",
        "avg_price": "平均房價",
        "domestic_ratio": "本國旅客比例",
        "international_ratio": "國際旅客比例",
        "individual_ratio": "散客比例",
        "city": "縣市",
        "star_rating": "星級",
        "occupancy_rate": "住房率",
    }
    quality = pd.DataFrame(
        {
            "欄位": [quality_labels[column] for column in quality_labels],
            "缺失筆數": [int(df[column].isna().sum()) for column in quality_labels],
            "缺失率數值": [float(df[column].isna().mean() * 100) for column in quality_labels],
        }
    )
    overall_missing = quality["缺失筆數"].sum() / (len(df) * len(quality_labels)) * 100

    if selected_metrics:
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("2026滾動測試 MAE", f"{selected_metrics['mae']:.2f} 個百分點")
        e2.metric("2026滾動測試 RMSE", f"{selected_metrics['rmse']:.2f} 個百分點")
        e3.metric("2026滾動測試 R²", f"{selected_metrics['r2']:.4f}")
        e4.metric("正式採用模型", selected_model)

        st.caption(
            "註：本頁上方「2026-01～2026-06 預測與官方實績比較」的滾動一個月數字、此處的"
            "「2026滾動測試」、以及下方「候選模型比較」中採用模型那一列，皆為**同一份 "
            "2026 上半年滾動驗證**（n≈694），並非三次獨立測試。"
        )

        v1, v2, v3, v4 = st.columns(4)
        v1.metric("模型版本", model_version)
        v2.metric("模型更新時間", model_updated)
        v3.metric("正式訓練期間", f"{metadata.get('data_start', '2023-01')}～{metadata.get('data_end', '2026-06')}")
        v4.metric("原始輸入整體缺失率", f"{overall_missing:.2f}%")
        st.caption(
            f"時間外測試期間：{metadata.get('holdout_start', '2026-01')}～"
            f"{metadata.get('holdout_end', '2026-06')}；正式模型資料截止："
            f"{metadata.get('data_end', latest_date.strftime('%Y-%m'))}。"
        )
        st.caption(metadata.get("test_input_policy", "回測只使用預測前可取得的資料。"))

    if IMPORTANCE.exists():
        importance = pd.read_csv(IMPORTANCE).head(10).copy()
        importance["影響因素"] = importance["feature"].map(FEATURE_LABELS).fillna(
            importance["feature"].str.replace("cat__city_", "縣市：", regex=False).str.replace(
                "cat__star_rating_", "星級：", regex=False
            )
        )
        importance["重要度"] = importance["importance"].map(lambda value: f"{value:.1%}")
        st.markdown("**正式模型主要影響因素**")
        st.dataframe(importance[["影響因素", "重要度"]], width="stretch", hide_index=True)

    if results:
        comparison = pd.DataFrame(results).T.reset_index().rename(
            columns={"index": "模型", "mae": "MAE", "rmse": "RMSE", "r2": "R²", "n": "測試筆數"}
        )
        st.markdown(
            f"**候選模型比較（{metadata.get('holdout_start', '最近 12 個月')} 至 "
            f"{metadata.get('holdout_end', latest_date.strftime('%Y-%m'))}）**"
        )
        st.dataframe(comparison, width="stretch", hide_index=True)

    if holiday_experiment:
        fixed_experiment = holiday_experiment.get("fixed_origin_2025_12", {})
        experiment_rows = []
        for key, label in [
            ("seasonal_naive", "Seasonal Naive（去年同月）"),
            ("base_model", "現行基礎模型"),
            ("holiday_model", "加入官方假日特徵"),
        ]:
            item = fixed_experiment.get(key, {})
            if item:
                experiment_rows.append(
                    {
                        "方法": label,
                        "MAE": item.get("mae"),
                        "RMSE": item.get("rmse"),
                        "R²": item.get("r2"),
                        "平均偏差": item.get("bias"),
                        "測試筆數": item.get("n"),
                    }
                )
        if experiment_rows:
            st.markdown("**官方假日特徵實驗（固定於 2025-12 預測 2026 上半年）**")
            st.dataframe(pd.DataFrame(experiment_rows), width="stretch", hide_index=True)
            if holiday_experiment.get("adopt_holiday_model"):
                st.success(holiday_experiment.get("decision", "假日模型通過採用門檻。"))
            else:
                st.warning(
                    holiday_experiment.get("decision", "假日模型未通過採用門檻。")
                    + " 雖然 RMSE 略有改善，但 MAE 未改善，因此不覆蓋現行正式模型。"
                )
            st.caption(
                "資料依據：行政院人事行政總處 2023–2027 政府行政機關辦公日曆。"
                "這是官方假日與旅館月住房率的月度關聯測試；官方資料沒有旅館逐日住房率，"
                "所以不能解讀為連假當日的因果效果。"
            )

    st.markdown("**月度原始輸入資料缺失率**")
    quality["缺失率"] = quality["缺失率數值"].map(lambda value: f"{value:.2f}%")
    st.dataframe(quality[["欄位", "缺失筆數", "缺失率"]], width="stretch", hide_index=True)

    if not fixed_backtest.empty:
        st.markdown("**2026 上半年固定起點回測誤差分布**")
        error_figure = px.histogram(
            fixed_backtest,
            x="error",
            nbins=35,
            labels={"error": "預測誤差（預測－實際，百分點）", "count": "筆數"},
            color_discrete_sequence=["#ff4b4b"],
        )
        error_figure.add_vline(x=0, line_dash="dash", line_color="white")
        error_figure.update_layout(showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(error_figure, width="stretch")
        st.caption("誤差大於 0 代表高估住房率，小於 0 代表低估住房率。")

    coverage = pd.DataFrame(
        {
            "待補特徵": ["連假", "重大活動", "即時訂房進度", "取消率"],
            "目前狀態": ["已取得並完成實驗；未正式採用", "未納入模型", "未納入模型", "未納入模型"],
            "啟用條件": [
                "取得更多年度或旅館逐日住房率，並通過時間外驗證",
                "取得日期、縣市與活動規模",
                "取得各旅館每日訂房快照",
                "取得各旅館取消日期與入住月份",
            ],
        }
    )
    st.markdown("**尚未納入模型的真實資料**")
    st.dataframe(coverage, width="stretch", hide_index=True)

    st.caption(
        "此模型適合月度營運規劃；正式模型尚未採用假日特徵，也不含即時訂房進度、活動規模與天氣，"
        "因此不應解讀成每日住房率承諾。"
    )
