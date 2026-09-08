from pathlib import Path
import calendar
import json
import sys

import joblib
import numpy as np
import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from features import get_feature_columns


ANNUAL_DATA = ROOT / "data" / "processed" / "hotel_combined_corrected.csv"
MONTHLY_DATA = ROOT / "data" / "processed" / "hotel_monthly.csv"
MODEL = ROOT / "models" / "decision_tree.pkl"
RESULTS = ROOT / "reports" / "model_results.json"


st.set_page_config(page_title="年度預測分析", page_icon="📆", layout="wide")
st.title("📆 年度預測分析：明年可能如何")
st.caption(
    "以官方月度資料彙整的年度模型進行情境估算；本頁不會改寫原始資料、月度模型或每日模型。"
)


def normalize_hotel_name(value: object) -> str:
    # 2025 年年度檔使用「中文名稱換行英文名稱」，配對時只取第一行中文名稱。
    first_line = str(value).splitlines()[0]
    return "".join(first_line.split()).strip("*#")


@st.cache_data
def load_annual_prediction_data() -> pd.DataFrame:
    data = pd.read_csv(ANNUAL_DATA)
    data["display_hotel_name"] = (
        data["hotel_name"].astype(str).str.split("\n").str[0].str.strip("*# ")
    )
    data["hotel_key"] = data["hotel_name"].map(normalize_hotel_name)
    return data


@st.cache_data
def load_monthly_history_data() -> pd.DataFrame:
    data = pd.read_csv(MONTHLY_DATA)
    data["hotel_key"] = data["hotel_name"].map(normalize_hotel_name)
    data["date"] = pd.to_datetime(
        dict(year=data["year"].astype(int), month=data["month"].astype(int), day=1)
    )
    data["days_in_month"] = data["date"].dt.days_in_month
    data["available_room_nights"] = (
        pd.to_numeric(data["total_rooms"], errors="coerce") * data["days_in_month"]
    )
    data["sold_room_nights"] = pd.to_numeric(data["rooms_used"], errors="coerce")
    data["room_revenue"] = pd.to_numeric(data["room_revenue"], errors="coerce")
    return data


@st.cache_resource
def load_annual_prediction_model():
    return joblib.load(MODEL)


def aggregate_hotel_history(monthly_rows: pd.DataFrame) -> pd.DataFrame:
    history = (
        monthly_rows.groupby("year", as_index=False)
        .agg(
            available_room_nights=("available_room_nights", "sum"),
            sold_room_nights=("sold_room_nights", "sum"),
            room_revenue=("room_revenue", "sum"),
            months=("month", "nunique"),
        )
        .sort_values("year")
    )
    history["unsold_room_nights"] = (
        history["available_room_nights"] - history["sold_room_nights"]
    ).clip(lower=0)
    history["occupancy_rate"] = np.where(
        history["available_room_nights"] > 0,
        history["sold_room_nights"] / history["available_room_nights"] * 100,
        np.nan,
    )
    history["adr"] = np.where(
        history["sold_room_nights"] > 0,
        history["room_revenue"] / history["sold_room_nights"],
        np.nan,
    )
    history["revpar"] = np.where(
        history["available_room_nights"] > 0,
        history["room_revenue"] / history["available_room_nights"],
        np.nan,
    )
    return history


def make_model_input(
    star_rank: int,
    actual_rooms: int,
    city: str,
    price: float,
    domestic: float,
    individual: float,
    employees: int,
    room_revenue_ratio: float,
) -> pd.DataFrame:
    # 舊年度訓練資料的 total_rooms 是 12 個月房間數加總，不是實際房間數。
    # 畫面顯示實際房間數；送入既有模型時轉回原訓練尺度，以維持模型相容性。
    annual_room_units = actual_rooms * 12
    columns = get_feature_columns()
    row = {column: 0.0 for column in columns}
    row.update(
        {
            "avg_price": price,
            "total_rooms": annual_room_units,
            "star_rank_filled": star_rank,
            "has_star": int(star_rank > 0),
            "is_5star_plus": int(star_rank >= 5),
            "is_4star": int(star_rank == 4),
            "is_3star": int(star_rank == 3),
            "is_non_star": int(star_rank == 0),
            "domestic_ratio": domestic,
            "international_ratio": 1 - domestic,
            "individual_ratio": individual,
            "room_rev_ratio": room_revenue_ratio,
            "rooms_per_employee": annual_room_units / max(1, employees),
            "is_luxury_price": int(price >= 6000),
            "is_budget_price": int(price < 3000),
            "is_large_hotel": int(annual_room_units >= 300),
        }
    )

    # 城市欄位若存在於既有模型特徵中，依欄名動態對應。
    city_feature = f"is_{city}"
    if city_feature in row:
        row[city_feature] = 1
    return pd.DataFrame([row], columns=columns)


def load_evaluation_results() -> tuple[dict, pd.DataFrame]:
    if not RESULTS.exists():
        return {}, pd.DataFrame()
    with open(RESULTS, encoding="utf-8") as file:
        raw = json.load(file)
    table = pd.DataFrame(raw).T.reset_index().rename(
        columns={"index": "模型", "mae": "MAE", "rmse": "RMSE", "r2": "R²"}
    )
    return raw, table


required = [ANNUAL_DATA, MONTHLY_DATA, MODEL]
missing = [str(path) for path in required if not path.exists()]
if missing:
    st.error("缺少年度預測所需檔案：" + "、".join(missing))
    st.stop()


annual_df = load_annual_prediction_data()
monthly_df = load_monthly_history_data()
model = load_annual_prediction_model()
evaluation_raw, evaluation_table = load_evaluation_results()

monthly_hotel_keys = set(monthly_df["hotel_key"].dropna().unique())
all_annual_hotel_count = annual_df["hotel_key"].nunique()
annual_df = annual_df[annual_df["hotel_key"].isin(monthly_hotel_keys)].copy()
excluded_hotel_count = all_annual_hotel_count - annual_df["hotel_key"].nunique()

hotel_options = (
    annual_df[["display_hotel_name", "hotel_key"]]
    .drop_duplicates()
    .sort_values("display_hotel_name")
)
if hotel_options.empty:
    st.error("年度資料中沒有任何可與月度資料配對的旅館。")
    st.stop()

if excluded_hotel_count:
    st.caption(
        f"僅顯示可與官方月度資料配對的旅館；已排除 {excluded_hotel_count:,} 間無月度配對紀錄的旅館。"
    )
else:
    st.caption("年度旅館已全部成功配對官方月度資料。")
selected_name = st.selectbox("選擇旅館", hotel_options["display_hotel_name"].tolist())
selected_key = hotel_options.loc[
    hotel_options["display_hotel_name"] == selected_name, "hotel_key"
].iloc[0]

annual_rows = annual_df[annual_df["hotel_key"] == selected_key].sort_values("year")
latest_annual = annual_rows.iloc[-1]
hotel_monthly = monthly_df[monthly_df["hotel_key"] == selected_key].copy()
historical = aggregate_hotel_history(hotel_monthly)
latest_monthly = hotel_monthly.sort_values(["year", "month"]).iloc[-1]
actual_rooms_default = max(1, int(round(float(latest_monthly["total_rooms"]))))
latest_actual_occupancy = float(historical.iloc[-1]["occupancy_rate"])
latest_history_year = int(historical.iloc[-1]["year"])


st.subheader("歷史基準（供預測比較）")
if not historical.empty:
    recent = historical.tail(3)
    first_occupancy = float(recent.iloc[0]["occupancy_rate"])
    trend_change = latest_actual_occupancy - first_occupancy
    h1, h2, h3, h4 = st.columns(4)
    h1.metric(f"{latest_history_year} 實際住房率", f"{latest_actual_occupancy:.1f}%")
    h2.metric("近三年加權平均住房率", f"{recent['sold_room_nights'].sum() / recent['available_room_nights'].sum() * 100:.1f}%")
    h3.metric("近三年住房率變化", f"{trend_change:+.1f} 個百分點")
    h4.metric("最新實際客房數", f"{actual_rooms_default:,} 間")

    display_history = recent.copy()
    display_history["住房率"] = display_history["occupancy_rate"].map(lambda x: f"{x:.1f}%")
    display_history["ADR"] = display_history["adr"].map(lambda x: f"NT${x:,.0f}")
    display_history["RevPAR"] = display_history["revpar"].map(lambda x: f"NT${x:,.0f}")
    display_history["客房收入"] = display_history["room_revenue"].map(lambda x: f"NT${x:,.0f}")
    st.dataframe(
        display_history[["year", "months", "住房率", "ADR", "RevPAR", "客房收入"]].rename(
            columns={"year": "年度", "months": "涵蓋月份"}
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.caption("無月度歷史可顯示。")


st.subheader("明年情境輸入")
default_target_year = latest_history_year + 1
default_star = latest_monthly.get("star_rank", latest_annual.get("star_rank", 0))
default_star = int(default_star) if pd.notna(default_star) else 0
default_employees = latest_monthly.get("employees", latest_annual.get("employees", 80))
default_employees = int(default_employees) if pd.notna(default_employees) else 80
default_price = latest_monthly.get("avg_price", latest_annual.get("avg_price", 4500))
default_price = int(round(float(default_price))) if pd.notna(default_price) else 4500
default_domestic = latest_monthly.get(
    "domestic_ratio", latest_annual.get("domestic_ratio", 0.6)
)
default_domestic = float(np.clip(default_domestic, 0, 1)) if pd.notna(default_domestic) else 0.6
default_individual = latest_monthly.get(
    "individual_ratio", latest_annual.get("individual_ratio", 0.6)
)
default_individual = float(np.clip(default_individual, 0, 1)) if pd.notna(default_individual) else 0.6
default_city = str(latest_monthly.get("city", latest_annual.get("city", "台北市")))

input_col1, input_col2, input_col3 = st.columns(3)
with input_col1:
    target_year = st.number_input(
        "預測目標年度", min_value=latest_history_year + 1, max_value=latest_history_year + 10,
        value=default_target_year, step=1,
    )
    city = st.text_input("縣市", default_city)
    star_rank = st.number_input("星級（0 表示未評鑑）", 0, 6, default_star, step=1)
with input_col2:
    actual_rooms = st.number_input(
        "實際客房數", min_value=1, max_value=5000, value=actual_rooms_default, step=1
    )
    employees = st.number_input(
        "員工數", min_value=1, max_value=5000, value=default_employees, step=1
    )
    expected_adr = st.number_input(
        "預期平均房價（ADR）", min_value=500, max_value=50000, value=default_price, step=100
    )
with input_col3:
    domestic_ratio = st.slider(
        "本國旅客比例", 0.0, 1.0, default_domestic, 0.01
    )
    individual_ratio = st.slider(
        "散客比例", 0.0, 1.0, default_individual, 0.01
    )
    st.caption(f"國際旅客比例：{1 - domestic_ratio:.0%}")

room_revenue = float(latest_annual.get("room_revenue", 0) or 0)
total_revenue = float(latest_annual.get("total_revenue", 0) or 0)
room_revenue_ratio = room_revenue / total_revenue if total_revenue > 0 else 0.60

model_input = make_model_input(
    int(star_rank), int(actual_rooms), city, float(expected_adr), float(domestic_ratio),
    default_individual if individual_ratio is None else float(individual_ratio),
    int(employees), room_revenue_ratio,
)
prediction = float(np.clip(model.predict(model_input)[0], 0, 100))

tree_metrics = evaluation_raw.get("Decision Tree", {})
mae = float(tree_metrics.get("mae", np.nan))
rmse = float(tree_metrics.get("rmse", np.nan))
r2 = float(tree_metrics.get("r2", np.nan))
error_span = rmse if np.isfinite(rmse) else 15.0
conservative = float(np.clip(prediction - error_span, 0, 100))
optimistic = float(np.clip(prediction + error_span, 0, 100))

days_in_year = 366 if calendar.isleap(int(target_year)) else 365
available_room_nights = int(actual_rooms) * days_in_year
sold_room_nights = available_room_nights * prediction / 100
unsold_room_nights = available_room_nights - sold_room_nights
revpar = float(expected_adr) * prediction / 100
room_revenue_forecast = sold_room_nights * float(expected_adr)
yoy_change = prediction - latest_actual_occupancy if np.isfinite(latest_actual_occupancy) else np.nan


st.subheader(f"{int(target_year)} 年基準預測")
m1, m2, m3, m4 = st.columns(4)
m1.metric(
    "年度平均住房率",
    f"{prediction:.1f}%",
    f"{yoy_change:+.1f} 個百分點 vs {latest_history_year}" if np.isfinite(yoy_change) else None,
)
m2.metric("預期 ADR", f"NT${expected_adr:,.0f}")
m3.metric("預期 RevPAR", f"NT${revpar:,.0f}")
m4.metric("預期客房收入", f"NT${room_revenue_forecast:,.0f}")

o1, o2, o3 = st.columns(3)
o1.metric("可售房晚", f"{available_room_nights:,.0f}")
o2.metric("預計售出房晚", f"{sold_room_nights:,.0f}")
o3.metric("預計空置房晚", f"{unsold_room_nights:,.0f}")

scenario_table = pd.DataFrame(
    {
        "情境": ["保守", "基準", "樂觀"],
        "住房率": [conservative, prediction, optimistic],
    }
)
scenario_table["RevPAR"] = scenario_table["住房率"] / 100 * float(expected_adr)
scenario_table["預計售出房晚"] = scenario_table["住房率"] / 100 * available_room_nights
scenario_table["預期客房收入"] = scenario_table["預計售出房晚"] * float(expected_adr)
scenario_display = scenario_table.copy()
scenario_display["住房率"] = scenario_display["住房率"].map(lambda x: f"{x:.1f}%")
scenario_display["RevPAR"] = scenario_display["RevPAR"].map(lambda x: f"NT${x:,.0f}")
scenario_display["預計售出房晚"] = scenario_display["預計售出房晚"].map(lambda x: f"{x:,.0f}")
scenario_display["預期客房收入"] = scenario_display["預期客房收入"].map(lambda x: f"NT${x:,.0f}")
st.dataframe(scenario_display, use_container_width=True, hide_index=True)
st.caption(
    f"保守／樂觀情境以測試集 RMSE ±{error_span:.2f} 個百分點估算，"
    "用於營運壓力測試，並非統計信賴區間。"
)


with st.expander("🧪 模型評估：這個預測有多可信", expanded=True):
    if tree_metrics:
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("測試 MAE", f"{mae:.2f} 個百分點")
        e2.metric("測試 RMSE", f"{rmse:.2f} 個百分點")
        e3.metric("測試 R²", f"{r2:.4f}")
        e4.metric("可信度判讀", "有限")
        st.warning(
            "目前年度模型的 R² 約為 0.40，且 RMSE 約 15 個百分點。"
            "適合做年度情境規劃與風險範圍估算，不宜當作精確營運承諾。"
        )
    else:
        st.warning("找不到年度模型評估結果，無法量化本次預測誤差。")

    st.markdown(
        "**使用限制：** 既有年度模型使用房價、規模、星級、旅客結構與人力等欄位；"
        "目標年度、前一年住房率、節假日與活動尚未納入模型，所以這些因素目前不能直接改變預測。"
    )
    st.caption(
        "畫面顯示的是實際客房數；為相容既有模型，系統只在內部轉為 12 個月房間單位，原始資料不會被修改。"
    )

    if hasattr(model, "feature_importances_"):
        feature_labels = {
            "avg_price": "平均房價",
            "total_rooms": "旅館規模（年度房間單位）",
            "star_rank_filled": "星級",
            "domestic_ratio": "本國旅客比例",
            "international_ratio": "國際旅客比例",
            "individual_ratio": "散客比例",
            "room_rev_ratio": "客房收入占比",
            "rooms_per_employee": "每位員工對應房間單位",
            "is_luxury_price": "高價旅館指標",
            "is_budget_price": "平價旅館指標",
            "is_large_hotel": "大型旅館指標",
        }
        importance = pd.DataFrame(
            {"內部特徵": get_feature_columns(), "重要度": model.feature_importances_}
        ).sort_values("重要度", ascending=False)
        importance = importance[importance["重要度"] > 0].head(8)
        importance["影響因素"] = importance["內部特徵"].map(feature_labels).fillna("其他類別特徵")
        st.markdown("**模型主要影響因素**")
        st.dataframe(
            importance[["影響因素", "重要度"]], use_container_width=True, hide_index=True
        )

    if not evaluation_table.empty:
        st.markdown("**年度候選模型測試結果**")
        shown_models = evaluation_table[evaluation_table["R²"] > -1]
        st.dataframe(shown_models, use_container_width=True, hide_index=True)
        hidden_models = evaluation_table.loc[evaluation_table["R²"] <= -1, "模型"].tolist()
        if hidden_models:
            st.caption(
                "已隱藏 " + "、".join(hidden_models) + "：這些線性模型未對年度特徵"
                "（total_rooms 為 12 個月加總、rooms_per_employee 等）做標準化，"
                "R² 為極大負值、不具比較意義。正式年度模型採 Decision Tree。"
            )


st.info(
    "若要提升年度預測可信度，下一版應重新訓練年度模型，正式加入前一年住房率、三年趨勢、"
    "節假日與活動彙整特徵；每日資料則維持在獨立每日頁，不覆蓋年度與月度分析。"
)
