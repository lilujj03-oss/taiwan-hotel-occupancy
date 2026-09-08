from pathlib import Path
import json

import joblib
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed" / "hotel_daily_features.csv"
MONTHLY_DATA = ROOT / "data" / "processed" / "hotel_monthly.csv"
MODEL = ROOT / "models" / "daily_gradient_boosting.pkl"
REPORT = ROOT / "reports" / "daily_model_readiness.json"

st.set_page_config(page_title="每日住房率預測", page_icon="📅", layout="wide")
st.title("📅 每日住房率預測分析")
st.caption("每日模型與年度、月度模型完全分開；只有取得實際每日住房率並通過驗證後才啟用預測。")

if not DATA.exists() or not MONTHLY_DATA.exists():
    st.warning("每日特徵資料尚未建立。請先於專案根目錄執行：python src/build_daily_features.py")
    st.stop()

df = pd.read_csv(DATA)
monthly_df = pd.read_csv(MONTHLY_DATA, usecols=["hotel_name"])
normalize_hotel_name = lambda value: "".join(str(value).splitlines()[0].split()).strip("*#")
monthly_hotel_keys = set(monthly_df["hotel_name"].map(normalize_hotel_name).dropna().unique())
df["hotel_key"] = df["hotel_name"].map(normalize_hotel_name)
daily_hotel_count_before = df["hotel_key"].nunique()
df = df[df["hotel_key"].isin(monthly_hotel_keys)].copy()
excluded_daily_hotels = daily_hotel_count_before - df["hotel_key"].nunique()
if df.empty:
    st.warning("每日特徵資料中沒有任何可與月度資料配對的旅館。")
    st.stop()

st.caption(
    f"僅顯示可與官方月度資料配對的旅館；已排除 {excluded_daily_hotels:,} 間無月度配對紀錄的旅館。"
)
df["date"] = pd.to_datetime(df["date"], errors="coerce")
has_signal = df["has_daily_signal"].astype(str).str.lower().eq("true")
actual_count = int(pd.to_numeric(df["occupancy_rate"], errors="coerce").notna().sum())
c1, c2, c3, c4 = st.columns(4)
c1.metric("旅館數", f"{df['hotel_name'].nunique():,}")
c2.metric("日期數", f"{df['date'].nunique():,}")
c3.metric("需求訊號", f"{int(has_signal.sum()):,}")
c4.metric("實際每日住房率", f"{actual_count:,}")

quality = df["data_quality"].value_counts().rename_axis("資料狀態").reset_index(name="筆數")
st.dataframe(quality, use_container_width=True)

if not MODEL.exists():
    st.warning("目前尚無足夠的實際每日住房率，因此不產生每日預測，避免把 OTA 房況誤當成住房率。")
    st.markdown("每日房價、可訂狀態、假日與活動資料仍可持續累積，月度與年度模型不受影響。")
    if REPORT.exists():
        with open(REPORT, encoding="utf-8") as f:
            st.json(json.load(f))
    st.stop()

model = joblib.load(MODEL)
st.success("每日模型已啟用")
if REPORT.exists():
    with open(REPORT, encoding="utf-8") as f:
        st.json(json.load(f))

valid = df[has_signal].copy()
if valid.empty:
    st.info("已有模型，但目前沒有可顯示的每日需求訊號。")
    st.stop()

hotel = st.selectbox("選擇旅館", sorted(valid["hotel_name"].dropna().unique()))
latest = valid[valid["hotel_name"] == hotel].sort_values("date").iloc[-1]
features = ["weekday", "is_weekend", "is_holiday", "event_level", "avg_price", "price_log", "availability_pressure", "rooms_available", "city", "star_rating", "availability_status"]
pred = float(model.predict(pd.DataFrame([latest[features].to_dict()]))[0])
st.metric("下一日住房率預測", f"{max(0, min(100, pred)):.1f}%")
st.caption(f"最新需求訊號日期：{latest['date'].date()}")
