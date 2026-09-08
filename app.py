"""
app.py
Streamlit 儀表板：台灣星級觀光旅館住房率預測與分析
兼論星級認證與住房率之關聯（2023–2025 年觀光旅館營運統計）
啟動方式：streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# 加入 src 路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

# ── 頁面設定 ────────────────────────────────────────────
st.set_page_config(
    page_title="台灣觀光旅館住房率分析與預測",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 自訂 CSS ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans TC', sans-serif;
}

.main-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 2rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    text-align: center;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}

.main-header h1 {
    color: #ffffff;
    font-size: 2.1rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: 0.05em;
}

.main-header p {
    color: #cbd5e1;
    margin: 0.5rem 0 0 0;
    font-size: 1rem;
    font-weight: 500;
}

.metric-card {
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
    box-shadow: 0 4px 16px rgba(0,0,0,0.2);
    min-height: 130px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.metric-value {
    font-size: 1.9rem;
    font-weight: 700;
    color: #38bdf8;
}

.metric-label {
    color: #ffffff;
    font-size: 0.9rem;
    font-weight: 600;
    margin-top: 0.3rem;
}

.prediction-highlight-card {
    background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
    border: 2px solid #38bdf8;
    border-radius: 16px;
    padding: 1.3rem;
    text-align: center;
    box-shadow: 0 8px 32px rgba(56,189,248,0.2);
}

.prediction-highlight-value {
    font-size: 2.8rem;
    font-weight: 800;
    color: #38bdf8;
}

.advice-box-wide {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-left: 5px solid #38bdf8;
    border-radius: 10px;
    padding: 1.2rem 1.8rem;
    margin-top: 1rem;
    margin-bottom: 1.5rem;
    color: #ffffff;
    font-size: 1.05rem;
    line-height: 1.6;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25);
}

.section-divider-title {
    color: #ffffff;
    font-size: 1.35rem;
    font-weight: 700;
    margin-top: 1.5rem;
    margin-bottom: 0.8rem;
    border-bottom: 2px solid #38bdf8;
    padding-bottom: 0.4rem;
}

div[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
}
</style>
""", unsafe_allow_html=True)

PROCESSED_DIR = Path(__file__).parent / "data" / "processed"
MODELS_DIR = Path(__file__).parent / "models"
REPORTS_DIR = Path(__file__).parent / "reports"
MONTHLY_MODEL_PATH = MODELS_DIR / "monthly_model_through_202606.pkl"


TITLE_COLOR = "#FEFCE8"  # 圖表標題：淺黃白色


def style_chart(fig, title_text=None):
    """將圖表標題統一設為淺黃白色粗體，並套用深色主題與清晰白色軸文字、圖例"""
    layout_update = {
        "plot_bgcolor": "#0f172a",
        "paper_bgcolor": "#0f172a",
        "font": dict(color="#ffffff"),
        "legend": dict(
            font=dict(color="#ffffff", size=12),
            title_font_color="#ffffff",
        ),
    }
    if title_text:
        layout_update["title"] = dict(
            text=f"<b>{title_text}</b>",
            font=dict(color=TITLE_COLOR, size=16)
        )
    else:
        layout_update["title_font"] = dict(color=TITLE_COLOR, size=16)
        
    fig.update_layout(**layout_update)
    # 全站統一：座標軸刻度文字與軸標題改為明顯的白色，格線收斂為深灰藍
    fig.update_xaxes(
        tickfont=dict(color="#ffffff"),
        title_font=dict(color="#ffffff"),
        gridcolor="#334155",
    )
    fig.update_yaxes(
        tickfont=dict(color="#ffffff"),
        title_font=dict(color="#ffffff"),
        gridcolor="#334155",
    )
    return fig


@st.cache_data
def load_data():
    """載入逐月清理後資料"""
    path = PROCESSED_DIR / "hotel_monthly.csv"
    if path.exists():
        df = pd.read_csv(path)
        # 主體分析只呈現完整的 2023–2025 歷史事實；2026 資料保留給資料庫更新，
        # 不混入本專題的三年比較基準。
        df = df[df["year"].between(2023, 2025)].copy()
        df["clean_hotel_name"] = df["hotel_name"].apply(lambda x: str(x).split("\n")[0].strip("*# "))
        # 官方月報中同一間旅館的名稱字串曾於 2023 年中變動（同縣市、同房數、同星等、
        # 月份不重疊）。僅於顯示層合併，讓歷史連續；不修改原始資料，也不影響預測模型。
        HOTEL_NAME_ALIASES = {
            "礁溪老爺大酒店": "礁溪老爺酒店",   # 2023-10 後改名
            "寒舍艾麗酒店": "台北艾麗酒店",     # 2023-05 後改名
        }
        df["clean_hotel_name"] = df["clean_hotel_name"].replace(HOTEL_NAME_ALIASES)
        # 聚落標籤
        resort_cities = ["宜蘭縣", "花蓮縣", "南投縣", "屏東縣", "台東縣", "澎湖縣", "金門縣", "嘉義縣"]
        df["cluster_type"] = df["city"].apply(lambda c: "🏖️ 風景度假聚落" if c in resort_cities else "🏢 都會商務聚落")
        return df
    return None


@st.cache_data
def load_nationality_data():
    """載入住客國籍總表"""
    path = PROCESSED_DIR / "guest_nationality_summary.csv"
    if path.exists():
        df_nat = pd.read_csv(path)
        df_nat.rename(columns={"Unnamed: 0": "國籍地區"}, inplace=True)
        return df_nat
    return None


@st.cache_resource
def load_model():
    """載入正式月度模型。"""
    try:
        import joblib
        if MONTHLY_MODEL_PATH.exists():
            return joblib.load(MONTHLY_MODEL_PATH)
    except Exception:
        pass
    return None


# ── 側邊欄 ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏨 台灣觀光旅館分析")
    st.markdown("### 月度預測模型")
    st.page_link("pages/2_月度預測分析.py", label="🗓️ 月度預測分析")
    st.markdown("---")

    page = st.radio(
        "選擇分析主題",
        [
            "📊 整體營運與住房趨勢",
            "🏨 個別旅館年度實績",
            "⭐ 星級認證效益分析",
            "🌍 住客國籍與客源結構分析",
            "🔍 影響因素與特徵解析",
        ],
    )

    st.markdown("---")
    st.markdown("**📂 資料來源**")
    st.markdown("中華民國交通部觀光署\n觀光旅館營運統計\n（2023–2025 月度資料）")
    st.markdown("---")
    st.markdown("**🤖 機器學習模型**")
    st.markdown("• 月度 Gradient Boosting\n• 2023-01～2026-06 正式訓練\n• 預測自 2026-07 起")

# ── 標題 ─────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🏨 台灣觀光旅館住房率分析與預測</h1>
    <p>兼論星級認證與住房率之關聯 ｜ 2023–2025 年觀光旅館營運統計 ｜ 機器學習預測</p>
</div>
""", unsafe_allow_html=True)

df = load_data()
df_nat = load_nationality_data()
model = load_model()

st.caption(
    "主體分析採用 2023–2025 三年官方月度資料作為歷史比較基準；"
    "2026 年資料保留給月度模型的訓練與時間外驗證，不納入本頁的三年趨勢比較。"
)

# ══════════════════════════════════════════════════════════
# 頁面一：整體營運與住房趨勢
# ══════════════════════════════════════════════════════════
if page == "📊 整體營運與住房趨勢":

    if df is None:
        st.warning("⚠️ 尚未載入資料，請確認資料清理步驟已執行。")
    else:
        col1, col2, col3, col4 = st.columns(4)

        avg_occ = df["occupancy_rate"].mean() if "occupancy_rate" in df.columns else 0
        n_hotels = df["clean_hotel_name"].nunique() if "clean_hotel_name" in df.columns else 0
        avg_price = df["avg_price"].mean() if "avg_price" in df.columns else 0
        avg_revpar = df["revpar"].mean() if "revpar" in df.columns else (avg_price * avg_occ / 100)

        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{avg_occ:.1f}%</div>
                <div class="metric-label">全台平均住房率<br>（簡單平均）</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{n_hotels}</div>
                <div class="metric-label">涵蓋觀光旅館數<br>（2023–2025 合計）</div>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">NT${avg_price:,.0f}</div>
                <div class="metric-label">全台平均房價 (ADR)<br>（簡單平均）</div>
            </div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">NT${avg_revpar:,.0f}</div>
                <div class="metric-label">平均每房收益 (RevPAR)<br>（簡單平均）</div>
            </div>""", unsafe_allow_html=True)

        st.caption(
            "上列住房率／ADR／RevPAR 為「每個旅館×月」的**簡單平均**（每筆一票）；"
            "下方「歷史年度營運總覽」表為**加權平均**（總量相除，大型旅館影響較大），"
            "兩者數字會略有差異。"
        )
        st.markdown("<br>", unsafe_allow_html=True)

        if {"year", "total_rooms", "rooms_used", "room_revenue"}.issubset(df.columns):
            _idx = df.copy()
            _idx["_md"] = pd.to_datetime(
                dict(year=_idx["year"], month=_idx["month"], day=1), errors="coerce"
            )
            _idx["_avail"] = (
                pd.to_numeric(_idx["total_rooms"], errors="coerce")
                * _idx["_md"].dt.days_in_month
            )
            _idx["_sold"] = pd.to_numeric(_idx["rooms_used"], errors="coerce")
            _idx["_rev"] = pd.to_numeric(_idx["room_revenue"], errors="coerce")
            _g = _idx.groupby("year").agg(
                _avail=("_avail", "sum"), _sold=("_sold", "sum"), _rev=("_rev", "sum")
            )
            # 採加權口徑，與下方「歷史年度營運總覽」表一致
            yearly_metrics = pd.DataFrame({
                "住房率": _g["_sold"] / _g["_avail"] * 100,
                "ADR": _g["_rev"] / _g["_sold"],
                "RevPAR": _g["_rev"] / _g["_avail"],
            })
            base_year = int(yearly_metrics.index.min())
            indexed = (yearly_metrics / yearly_metrics.iloc[0] * 100).reset_index()
            indexed_long = indexed.melt(id_vars="year", var_name="營運指標", value_name="指數")
            indexed_long["year"] = indexed_long["year"].astype(str) + " 年"
            fig_index = px.line(
                indexed_long, x="year", y="指數", color="營運指標", markers=True,
                labels={"year": "年份", "指數": f"指數（{base_year} 年 = 100）"},
                template="plotly_dark",
                color_discrete_map={"住房率": "#38bdf8", "ADR": "#22c55e", "RevPAR": "#f59e0b"},
            )
            fig_index.add_hline(y=100, line_dash="dot", line_color="#94a3b8")
            _span = indexed_long["指數"]
            fig_index.update_yaxes(range=[_span.min() - 3, _span.max() + 3])
            style_chart(fig_index, f"📈 2023–2025 年全台住房率、ADR、RevPAR 指數化走勢（{base_year} 年 = 100）")
            st.plotly_chart(fig_index, use_container_width=True)
            _last = indexed.iloc[-1]
            st.caption(
                f"三項指標均採**加權**口徑（與下方「歷史年度營運總覽」表一致）。"
                f"{int(_last['year'])} 年住房率指數約 {_last['住房率']:.1f}、ADR 約 {_last['ADR']:.1f}"
                f"——成長以「量」為主，房價尚未回到 {base_year} 年水準。"
            )

        st.markdown('<div class="section-divider-title">📅 月份季節性：淡旺季分布</div>', unsafe_allow_html=True)
        if {"month", "occupancy_rate", "cluster_type"}.issubset(df.columns):
            monthly_season = (
                df.groupby(["month", "cluster_type"])["occupancy_rate"].mean().reset_index()
            )
            fig_season = px.line(
                monthly_season, x="month", y="occupancy_rate", color="cluster_type",
                markers=True,
                labels={"month": "月份", "occupancy_rate": "平均住房率 (%)", "cluster_type": "旅館聚落"},
                template="plotly_dark",
                color_discrete_map={
                    "🏢 都會商務聚落": "#38bdf8",
                    "🏖️ 風景度假聚落": "#f59e0b",
                },
            )
            fig_season.update_xaxes(dtick=1)
            style_chart(fig_season, "📅 各月份平均住房率：都會商務 vs 風景度假")
            st.plotly_chart(fig_season, use_container_width=True)

            overall_by_month = df.groupby("month")["occupancy_rate"].mean()
            peak_month = int(overall_by_month.idxmax())
            low_month = int(overall_by_month.idxmin())
            cluster_month = df.pivot_table(
                index="month", columns="cluster_type", values="occupancy_rate", aggfunc="mean"
            )
            avg_gap = float(
                (cluster_month.get("🏢 都會商務聚落") - cluster_month.get("🏖️ 風景度假聚落")).mean()
            )
            st.caption(
                f"重點：全體住房率以 {peak_month} 月最高、{low_month} 月最低（年底節慶旺季、年初傳統淡季）；"
                f"都會商務聚落各月住房率普遍高於風景度假聚落約 {avg_gap:.0f} 個百分點，"
                "兩類旅館的全年高點都落在 12 月。"
            )

        st.markdown('<div class="section-divider-title">🏖️ 都會商務聚落 vs 風景度假聚落 經營模式對照</div>', unsafe_allow_html=True)
        if {"cluster_type", "avg_price", "revpar", "domestic_ratio"}.issubset(df.columns):
            col_cl1, col_cl2 = st.columns(2)
            with col_cl1:
                cl_df = df.groupby("cluster_type")[["avg_price", "revpar"]].mean().reset_index()
                cl_df = cl_df.rename(columns={"avg_price": "平均房價 ADR", "revpar": "RevPAR"})
                fig_cl_rev = px.bar(
                    cl_df, x="cluster_type", y=["平均房價 ADR", "RevPAR"],
                    barmode="group",
                    labels={"value": "金額 (NT$)", "variable": "財務指標", "cluster_type": "聚落類型"},
                    template="plotly_dark",
                    color_discrete_map={"平均房價 ADR": "#38bdf8", "RevPAR": "#22c55e"},
                )
                style_chart(fig_cl_rev, "🏢 聚落平均房價與 RevPAR 對比")
                st.plotly_chart(fig_cl_rev, use_container_width=True)
            with col_cl2:
                cl_dom = df.groupby("cluster_type")["domestic_ratio"].mean().reset_index()
                cl_dom["本國客"] = cl_dom["domestic_ratio"] * 100
                cl_dom["國際客"] = 100 - cl_dom["本國客"]
                fig_cl_dom = px.bar(
                    cl_dom, x="cluster_type", y=["本國客", "國際客"],
                    barmode="stack",
                    labels={"value": "比例 (%)", "variable": "旅客來源", "cluster_type": "聚落類型"},
                    template="plotly_dark",
                    color_discrete_map={"本國客": "#38bdf8", "國際客": "#f59e0b"},
                )
                style_chart(fig_cl_dom, "👥 聚落客源結構（本國客 vs 國際客比重）")
                st.plotly_chart(fig_cl_dom, use_container_width=True)
            resort_rev_median = float(df.loc[df["cluster_type"] == "🏖️ 風景度假聚落", "revpar"].median())
            urban_rev_median = float(df.loc[df["cluster_type"] == "🏢 都會商務聚落", "revpar"].median())
            st.caption(
                "度假聚落**平均** ADR／RevPAR 高於都會聚落，因為那 8 個縣（宜蘭、花蓮、南投、屏東、台東、"
                "澎湖、金門、嘉義縣）有日月潭、太魯閣、墾丁等目的地型度假旅館。但這是被少數頂級度假村"
                f"（涵碧樓、漢來日月行館…）拉高的：度假聚落 RevPAR 中位數約 NT${resort_rev_median:,.0f}、"
                f"都會聚落約 NT${urban_rev_median:,.0f}，**用中位數看兩者相近**。都會聚落住房率與國際客佔比則明顯較高。"
                "「都會 vs 度假」為依縣市所在地的人工分類，非旅館實際定位；本圖只含客房收入，"
                "度假旅館餐飲／SPA 佔比高、整體效益被低估。"
            )

        st.markdown('<div class="section-divider-title">📚 歷史年度營運總覽：過去發生什麼</div>', unsafe_allow_html=True)
        annual_history = df.copy()
        annual_history["month_date"] = pd.to_datetime(
            dict(year=annual_history["year"], month=annual_history["month"], day=1),
            errors="coerce",
        )
        annual_history["available_room_nights"] = (
            pd.to_numeric(annual_history["total_rooms"], errors="coerce")
            * annual_history["month_date"].dt.days_in_month
        )
        annual_history["sold_room_nights"] = pd.to_numeric(annual_history["rooms_used"], errors="coerce")
        annual_history["room_revenue_numeric"] = pd.to_numeric(annual_history["room_revenue"], errors="coerce")
        annual_history["employees_numeric"] = pd.to_numeric(annual_history["employees"], errors="coerce")
        annual_history["rooms_numeric"] = pd.to_numeric(annual_history["total_rooms"], errors="coerce")
        annual_summary = annual_history.groupby("year", as_index=False).agg(
            可售客房間夜=("available_room_nights", "sum"),
            已售客房間夜=("sold_room_nights", "sum"),
            客房營收=("room_revenue_numeric", "sum"),
        )
        # 涵蓋旅館數只計「該年 12 個月都有申報」的旅館
        _month_counts = annual_history.groupby(["year", "clean_hotel_name"])["month"].nunique()
        _full_year_count = _month_counts[_month_counts >= 12].groupby(level="year").size()
        annual_summary["涵蓋旅館數（12月完整）"] = (
            annual_summary["year"].map(_full_year_count).fillna(0).astype(int)
        )
        annual_summary["未售客房間夜"] = annual_summary["可售客房間夜"] - annual_summary["已售客房間夜"]
        annual_summary["住房率 (%)"] = annual_summary["已售客房間夜"] / annual_summary["可售客房間夜"] * 100
        annual_summary["ADR (NT$)"] = annual_summary["客房營收"] / annual_summary["已售客房間夜"]
        annual_summary["RevPAR (NT$)"] = annual_summary["客房營收"] / annual_summary["可售客房間夜"]
        annual_display = annual_summary[[
            "year", "涵蓋旅館數（12月完整）", "住房率 (%)", "ADR (NT$)", "RevPAR (NT$)",
            "可售客房間夜", "已售客房間夜", "未售客房間夜", "客房營收",
        ]].rename(columns={"year": "年度"})
        st.dataframe(
            annual_display.style.format({
                "年度": "{:.0f}", "涵蓋旅館數（12月完整）": "{:.0f}",
                "住房率 (%)": "{:.2f}", "ADR (NT$)": "{:,.0f}",
                "RevPAR (NT$)": "{:,.0f}", "可售客房間夜": "{:,.0f}",
                "已售客房間夜": "{:,.0f}", "未售客房間夜": "{:,.0f}", "客房營收": "{:,.0f}",
            }),
            use_container_width=True,
        )
        st.caption(
            "「涵蓋旅館數（12月完整）」只計該年 12 個月都有申報的旅館（2023：110、2024：111、2025：113）；"
            "可售／已售房晚與營收則納入該年所有有申報月份，故跨年比較仍應考量樣本變動。"
        )

        if {"city", "occupancy_rate", "revpar", "clean_hotel_name"}.issubset(df.columns):
            city_stats = df.groupby("city").agg(
                平均住房率=("occupancy_rate", "mean"),
                RevPAR=("revpar", "mean"),
                觀光旅館數=("clean_hotel_name", "nunique"),
            ).reset_index()
            city_stats["縣市標籤"] = (
                city_stats["city"] + "（" + city_stats["觀光旅館數"].astype(str) + " 間）"
            )

        col_a, col_b = st.columns(2)
        with col_a:
            occ_sorted = city_stats.sort_values("平均住房率")
            fig_city = px.bar(
                occ_sorted, x="平均住房率", y="縣市標籤",
                labels={"縣市標籤": "縣市（觀光旅館數）", "平均住房率": "平均住房率 (%)"},
                template="plotly_dark",
                orientation="h",
                color="平均住房率",
                color_continuous_scale="Viridis",
                hover_data=["觀光旅館數"],
            )
            style_chart(fig_city, "🗺 各縣市平均住房率排行")
            st.plotly_chart(fig_city, use_container_width=True)
            st.caption(
                "重點：排名前段多為觀光旅館極少的縣市——基隆市僅 1 間（長榮桂冠）、苗栗縣／金門縣各 1 間、"
                "新竹市 2 間，其「平均」等於單一或少數旅館，不具縣市代表性。台北市 38 間、樣本大，"
                "平均值較貼近整體水準。"
            )

        with col_b:
            rev_sorted = city_stats.sort_values("RevPAR")
            fig_rev = px.bar(
                rev_sorted, x="RevPAR", y="縣市標籤",
                labels={"縣市標籤": "縣市（觀光旅館數）", "RevPAR": "RevPAR (NT$)"},
                template="plotly_dark",
                orientation="h",
                color="RevPAR",
                color_continuous_scale="Blues",
                hover_data=["觀光旅館數"],
            )
            style_chart(fig_rev, "💰 各縣市平均 RevPAR（每可售房收益）")
            st.plotly_chart(fig_rev, use_container_width=True)
            st.caption(
                "重點：RevPAR＝住房率 × ADR，是價格加權指標。排名前段是「少數幾間、且全屬目的地型度假旅館」"
                "的縣市（客人專程去住、ADR 特別高）——南投縣 4 間全為日月潭頂級／豪華度假旅館（涵碧樓、漢來日月行館、雲品，"
                "ADR 約 NT$12,000–23,000），花蓮縣、嘉義縣同理（太魯閣、阿里山）。這些縣市沒有平價／商務旅館可平均，"
                "故排前面，不代表「該地觀光最賺」。台北市 38 間、含大量中價位商務旅館，平均被拉低。"
            )


# ══════════════════════════════════════════════════════════
# 頁面二：星級認證效益分析
# ══════════════════════════════════════════════════════════
elif page == "⭐ 星級認證效益分析":

    st.subheader("⭐ 星級認證與旅館經營效益關聯分析")
    st.markdown("探討有星等認證（卓越五星～三星級）與無星等認證觀光旅館在住房率、房價及 RevPAR 上的表現差異。")

    if df is None:
        st.warning("⚠️ 尚未載入資料")
    else:
        star_operating = df.copy()
        star_operating["month_date"] = pd.to_datetime(
            dict(year=star_operating["year"], month=star_operating["month"], day=1),
            errors="coerce",
        )
        star_operating["available_room_nights"] = (
            pd.to_numeric(star_operating["total_rooms"], errors="coerce")
            * star_operating["month_date"].dt.days_in_month
        )
        star_operating["sold_room_nights"] = pd.to_numeric(
            star_operating["rooms_used"], errors="coerce"
        )
        star_operating["room_revenue_numeric"] = pd.to_numeric(
            star_operating["room_revenue"], errors="coerce"
        )
        star_summary = star_operating.groupby("star_rating", as_index=False).agg(
            觀光旅館數=("clean_hotel_name", "nunique"),
            可售客房間夜=("available_room_nights", "sum"),
            已售客房間夜=("sold_room_nights", "sum"),
            客房營收=("room_revenue_numeric", "sum"),
        )
        star_summary["住房率"] = star_summary["已售客房間夜"] / star_summary["可售客房間夜"] * 100
        star_summary["ADR"] = star_summary["客房營收"] / star_summary["已售客房間夜"]
        star_summary["RevPAR"] = star_summary["客房營收"] / star_summary["可售客房間夜"]
        star_order = ["卓越五星", "五星級", "四星級", "三星級", "無星等/未評鑑"]
        star_summary["排序"] = star_summary["star_rating"].map(
            {label: index for index, label in enumerate(star_order)}
        ).fillna(len(star_order))
        star_summary = star_summary.sort_values("排序")

        st.markdown("**2023–2025 各星級住房率、ADR 與 RevPAR 完整比較**")
        st.dataframe(
            star_summary[["star_rating", "觀光旅館數", "住房率", "ADR", "RevPAR"]]
            .rename(columns={"star_rating": "星級"})
            .style.format({
                "住房率": "{:.2f}%",
                "ADR": "NT${:,.0f}",
                "RevPAR": "NT${:,.0f}",
            }),
            use_container_width=True,
        )
        st.caption(
            "說明：星等以觀光署現行評鑑結果回填全期間，未還原歷年評鑑異動；"
            "少數旅館的歷史星等可能與當年實際不同，本分析一律以現行星等為準。"
        )

        df_star = df[df["has_star"] == 1].copy()
        df_nostar = df[df["has_star"] == 0].copy()

        col1, col2, col3, col4 = st.columns(4)

        star_occ = df_star["occupancy_rate"].mean() if len(df_star) > 0 else 0
        nostar_occ = df_nostar["occupancy_rate"].mean() if len(df_nostar) > 0 else 0
        star_price = df_star["avg_price"].mean() if len(df_star) > 0 else 0
        nostar_price = df_nostar["avg_price"].mean() if len(df_nostar) > 0 else 0

        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{star_occ:.1f}%</div>
                <div class="metric-label">有星等平均住房率<br>（簡單平均）</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{nostar_occ:.1f}%</div>
                <div class="metric-label">無星等平均住房率<br>（簡單平均）</div>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">NT${star_price:,.0f}</div>
                <div class="metric-label">有星等平均房價<br>（簡單平均）</div>
            </div>""", unsafe_allow_html=True)
        with col4:
            diff = star_occ - nostar_occ
            color = "#22c55e" if diff > 0 else "#ef4444"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color:{color};">{diff:+.1f}%</div>
                <div class="metric-label">住房率溢價差距<br>（簡單平均之差）</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption(
            "上列 4 張卡為「每個旅館×月」的**簡單平均**（每筆一票）；上方星級總表為**加權平均**（總量相除），"
            "故此處差距（約 +16.8 個百分點）與總表推得的差距（約 +14.8 個百分點）不同。"
        )
        st.caption(
            "⚠️ 本頁為「有星等 vs 無星等」的關聯比較，非因果推論。無星等旅館多半規模較小、"
            "或位於商圈較弱的地點，其住房率差距可能來自這些因素，而非缺少星等本身；"
            "本分析未控制縣市與客房規模。"
        )

        col_a, col_b = st.columns(2)
        with col_a:
            df["group_label"] = df["has_star"].map({1: "星級認證旅館", 0: "非星級觀光旅館"})
            fig_box1 = px.box(
                df, x="group_label", y="occupancy_rate",
                labels={"group_label": "", "occupancy_rate": "住房率 (%)"},
                template="plotly_dark",
                color="group_label",
                color_discrete_map={"星級認證旅館": "#38bdf8", "非星級觀光旅館": "#94a3b8"},
            )
            style_chart(fig_box1, "📊 有星等 vs 無星等住房率分佈對比")
            fig_box1.update_layout(showlegend=False)
            st.plotly_chart(fig_box1, use_container_width=True)

        with col_b:
            star_only = df[df["star_rating"].notna() & (df["star_rating"] != "無星等/未評鑑")]
            if len(star_only) > 0:
                fig_star_occ = px.box(
                    star_only, x="star_rating", y="occupancy_rate",
                    labels={"star_rating": "星等評鑑", "occupancy_rate": "住房率 (%)"},
                    template="plotly_dark",
                    color="star_rating",
                    category_orders={"star_rating": ["卓越五星", "五星級", "四星級", "三星級"]},
                )
                style_chart(fig_star_occ, "⭐ 各星等旅館住房率分佈")
                fig_star_occ.update_layout(showlegend=False)
                st.plotly_chart(fig_star_occ, use_container_width=True)

        col_c, col_d = st.columns(2)
        with col_c:
            if "star_rating" in df.columns:
                rev_by_star = df.groupby("star_rating")["revpar"].mean().sort_values(ascending=True).reset_index()
                fig_rstar = px.bar(
                    rev_by_star, x="revpar", y="star_rating",
                    labels={"star_rating": "星等", "revpar": "RevPAR (NT$)"},
                    template="plotly_dark",
                    orientation="h",
                    color="revpar",
                    color_continuous_scale="Blues",
                    text_auto="$,.0f",
                )
                style_chart(fig_rstar, "💰 各星等平均 RevPAR（每可售房收益）")
                st.plotly_chart(fig_rstar, use_container_width=True)
                st.caption(
                    "重點：RevPAR＝住房率 × ADR，星等越高兩者都升，差距被放大（五星約為三星 2.5 倍）。"
                    "「無星等/未評鑑」排在三星之上，是因為這組混了未送評的高價旅館（如日勝生加賀屋、"
                    "漢來日月行館），ADR 偏高、拉起 RevPAR，即使其住房率為全組最低。此為簡單平均"
                    "（每旅館×月一票），與上方星級總表的加權平均數字略有差異；卓越五星僅 1 間，不宜當類別比較。"
                )

        with col_d:
            if "domestic_ratio" in df.columns and "star_rating" in df.columns:
                dom_by_star = df.groupby("star_rating")["domestic_ratio"].mean().sort_values(ascending=True).reset_index()
                dom_by_star["domestic_pct"] = dom_by_star["domestic_ratio"] * 100
                fig_dom = px.bar(
                    dom_by_star, x="domestic_pct", y="star_rating",
                    labels={"star_rating": "星等", "domestic_pct": "本國客比例 (%)"},
                    template="plotly_dark",
                    orientation="h",
                    color="domestic_pct",
                    color_continuous_scale="Teal",
                    text_auto=".1f",
                )
                style_chart(fig_dom, "👥 各星等本國旅客佔比")
                st.plotly_chart(fig_dom, use_container_width=True)
                st.caption(
                    "星等與客源結構**非線性關係**——只有兩端明顯（卓越五星最靠國際客、無星等最靠本國客），"
                    "中間亂序（四星比三星更國際化、五星比四星更靠本國）。此為簡單平均（每旅館×月一票），"
                    "domestic_ratio 指住客人次佔比、非人數。"
                )


# ══════════════════════════════════════════════════════════
# 頁面三：住客國籍與客源結構分析
# ══════════════════════════════════════════════════════════
elif page == "🌍 住客國籍與客源結構分析":

    st.subheader("🌍 2023–2025 全台觀光旅館住客國籍與客源比率分析")
    st.markdown("深入探討全台灣觀光旅館之**本國客 vs 國際外籍旅客比率（%）**、主要客源市場份額與疫後回流趨勢。")
    st.caption(
        "資料定義：數字為觀光旅館申報的**住客人次**（同一旅客住多晚／多間旅館會分別計入），"
        "與移民署的「入境旅客人數」不同，數值會明顯較高。本表由 hotel_guest_nationality_detail.csv"
        "（逐旅館逐年）彙總，僅涵蓋觀光旅館，不含一般旅館與民宿。"
    )

    china_path = PROCESSED_DIR / "china_visitors_annual.csv"
    if china_path.exists():
        st.markdown(
            '<div class="section-divider-title">🇨🇳 為何預測模型限定 2023 年起：中國大陸旅客的體制斷裂</div>',
            unsafe_allow_html=True,
        )
        china_df = pd.read_csv(china_path)
        fig_china = px.line(
            china_df, x="年", y="中國大陸來臺旅客萬人次", markers=True,
            labels={"年": "年份", "中國大陸來臺旅客萬人次": "中國大陸來臺旅客（萬人次）"},
            template="plotly_dark",
        )
        fig_china.update_traces(line_color="#ef4444")
        fig_china.update_yaxes(rangemode="tozero")
        fig_china.add_vrect(
            x0=2019.5, x1=2022.5, fillcolor="#64748b", opacity=0.18, line_width=0,
            annotation_text="COVID 邊境管制", annotation_position="top left",
        )
        style_chart(fig_china, "🇨🇳 中國大陸來臺旅客年入境人次（2011–2025）")
        st.plotly_chart(fig_china, use_container_width=True)
        st.caption(
            "資料來源：交通部觀光署《來臺旅客統計》／《觀光統計年報》（2024–2025 為估計值，待官方定版）。"
            "2015 年高峰約 418 萬人次 → 2016 年起管制趨嚴、逐年腰斬 → 2020–2022 疫情邊境關閉 → "
            "2023 年起觀光尚未開放、僅約 22 萬（多為商務／轉機）。正因 2020 年前旅館需求由陸客團客顯著驅動、"
            "2020–2022 疫情斷裂、2023 年起才是現行需求體制，**本專題刻意將預測模型限定在 2023 年起的資料，"
            "以確保訓練與預測處於同一需求結構**；回補 2016–2019 並加入「陸客／團客占比」等體制控制變數列為未來工作。"
        )

    if df_nat is None:
        st.warning("⚠️ 尚未載入住客國籍總表資料。")
    else:
        # KPI 卡片
        k_n1, k_n2, k_n3, k_n4 = st.columns(4)
        dom_row = df_nat[df_nat["國籍地區"] == "本國旅客"].iloc[0]
        jp_row = df_nat[df_nat["國籍地區"] == "日本"].iloc[0]
        us_row = df_nat[df_nat["國籍地區"] == "美國"].iloc[0]
        kr_row = df_nat[df_nat["國籍地區"] == "南韓"].iloc[0]

        with k_n1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{dom_row['全台佔比(%)']:.1f}%</div>
                <div class="metric-label">🇹🇼 本國旅客（第一主力）</div>
                <div style="color:#94a3b8;font-size:0.8rem;margin-top:0.3rem;">三年合計 {dom_row['三年合計人次']/10000:,.0f} 萬人次</div>
            </div>""", unsafe_allow_html=True)
        with k_n2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{jp_row['全台佔比(%)']:.2f}%</div>
                <div class="metric-label">🇯🇵 日本旅客（外國第 1 名）</div>
                <div style="color:#94a3b8;font-size:0.8rem;margin-top:0.3rem;">三年合計 {jp_row['三年合計人次']/10000:,.0f} 萬人次</div>
            </div>""", unsafe_allow_html=True)
        with k_n3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{us_row['全台佔比(%)']:.2f}%</div>
                <div class="metric-label">🇺🇸 美國旅客（外國第 2 名）</div>
                <div style="color:#94a3b8;font-size:0.8rem;margin-top:0.3rem;">三年合計 {us_row['三年合計人次']/10000:,.0f} 萬人次</div>
            </div>""", unsafe_allow_html=True)
        with k_n4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{kr_row['全台佔比(%)']:.2f}%</div>
                <div class="metric-label">🇰🇷 南韓旅客（外國第 3 名）</div>
                <div style="color:#94a3b8;font-size:0.8rem;margin-top:0.3rem;">三年合計 {kr_row['三年合計人次']/10000:,.0f} 萬人次</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if df is not None and {
            "total_guests", "domestic_guests", "individual_guests", "group_guests"
        }.issubset(df.columns):
            guest_structure = df.groupby("year", as_index=False).agg(
                總住客人次=("total_guests", "sum"),
                本國旅客=("domestic_guests", "sum"),
                散客=("individual_guests", "sum"),
                團體旅客=("group_guests", "sum"),
            )
            guest_structure["國際旅客"] = (
                guest_structure["總住客人次"] - guest_structure["本國旅客"]
            ).clip(lower=0)
            guest_structure["本國旅客比例"] = guest_structure["本國旅客"] / guest_structure["總住客人次"] * 100
            guest_structure["國際旅客比例"] = guest_structure["國際旅客"] / guest_structure["總住客人次"] * 100
            booking_total = guest_structure["散客"] + guest_structure["團體旅客"]
            guest_structure["散客比例"] = guest_structure["散客"] / booking_total * 100
            guest_structure["團體旅客比例"] = guest_structure["團體旅客"] / booking_total * 100

            st.markdown('<div class="section-divider-title">👥 歷年旅客來源與散客／團體結構</div>', unsafe_allow_html=True)
            source_col, booking_col = st.columns(2)
            with source_col:
                source_figure = px.bar(
                    guest_structure,
                    x="year",
                    y=["本國旅客比例", "國際旅客比例"],
                    barmode="stack",
                    labels={"year": "年度", "value": "旅客比例（%）", "variable": "旅客來源"},
                    color_discrete_map={"本國旅客比例": "#38bdf8", "國際旅客比例": "#f59e0b"},
                    template="plotly_dark",
                )
                style_chart(source_figure, "🌏 本國與國際旅客結構")
                source_figure.update_xaxes(type="category")
                st.plotly_chart(source_figure, use_container_width=True)
            with booking_col:
                booking_figure = px.bar(
                    guest_structure,
                    x="year",
                    y=["散客比例", "團體旅客比例"],
                    barmode="stack",
                    labels={"year": "年度", "value": "旅客比例（%）", "variable": "訂房型態"},
                    color_discrete_map={"散客比例": "#22c55e", "團體旅客比例": "#a78bfa"},
                    template="plotly_dark",
                )
                style_chart(booking_figure, "🧳 散客（FIT）與團體旅客結構")
                booking_figure.update_xaxes(type="category")
                st.plotly_chart(booking_figure, use_container_width=True)

            structure_display = guest_structure[[
                "year", "總住客人次", "本國旅客比例", "國際旅客比例", "散客比例", "團體旅客比例",
            ]].rename(columns={"year": "年度"})
            st.dataframe(
                structure_display.style.format({
                    "總住客人次": "{:,.0f}",
                    "本國旅客比例": "{:.2f}%",
                    "國際旅客比例": "{:.2f}%",
                    "散客比例": "{:.2f}%",
                    "團體旅客比例": "{:.2f}%",
                }),
                use_container_width=True,
            )

        # 第一排圖表：國際旅客國籍分佈與回流排行圖
        st.markdown('<div class="section-divider-title">🌍 國際旅客國籍分佈與回流排行圖</div>', unsafe_allow_html=True)
        col_nat1, col_nat2 = st.columns(2)

        with col_nat1:
            fig_all_nat = px.bar(
                df_nat.sort_values("全台佔比(%)", ascending=True),
                x="全台佔比(%)", y="國籍地區",
                orientation="h",
                color="全台佔比(%)",
                color_continuous_scale="Blues",
                text="全台佔比(%)",
                template="plotly_dark",
                labels={"全台佔比(%)": "全台住客佔比 (%)", "國籍地區": "客源國籍"},
            )
            fig_all_nat.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
            style_chart(fig_all_nat, "🌍 各客源市場全台住客佔比（2023–2025 三年合計）")
            fig_all_nat.update_layout(height=400)
            st.plotly_chart(fig_all_nat, use_container_width=True)

        with col_nat2:
            # 純外籍客源回流成長倍率排行 (2025 vs 2023)
            foreign_rank = df_nat[df_nat["國籍地區"] != "本國旅客"].copy()
            foreign_rank["回流成長率(%)"] = ((foreign_rank["2025"] - foreign_rank["2023"]) / foreign_rank["2023"] * 100).round(1)
            foreign_rank = foreign_rank.sort_values("回流成長率(%)", ascending=True)

            fig_growth_rank = px.bar(
                foreign_rank,
                x="回流成長率(%)", y="國籍地區",
                orientation="h",
                color="回流成長率(%)",
                color_continuous_scale="Viridis",
                text="回流成長率(%)",
                template="plotly_dark",
                labels={"回流成長率(%)": "2023→2025 成長率 (%)", "國籍地區": "外籍客源市場"},
            )
            fig_growth_rank.update_traces(texttemplate='+%{text:.1f}%', textposition='outside')
            style_chart(fig_growth_rank, "🏆 各主要外國客源市場【疫後回流成長率排行】(2023→2025)")
            fig_growth_rank.update_layout(height=400)
            st.plotly_chart(fig_growth_rank, use_container_width=True)

        # 第二排圖表：主要外國市場歷年成長趨勢
        foreign_top6 = df_nat[df_nat["國籍地區"] != "本國旅客"].head(6)
        melted_foreign = foreign_top6.melt(
            id_vars=["國籍地區"], value_vars=["2023", "2024", "2025"],
            var_name="年份", value_name="住客人次",
        )
        melted_foreign["年份"] = melted_foreign["年份"].astype(str) + " 年"

        fig_trend_nat = px.bar(
            melted_foreign, x="國籍地區", y="住客人次", color="年份",
            barmode="group",
            template="plotly_dark",
            color_discrete_map={"2023 年": "#64748b", "2024 年": "#38bdf8", "2025 年": "#f59e0b"},
            labels={"住客人次": "住客人次 (人)", "國籍地區": "國家/地區", "年份": "統計年份"},
            text_auto=".2s",
        )
        style_chart(fig_trend_nat, "📈 主要外籍客源市場（美、日、韓、港澳、星、歐）歷年住客人次走勢")
        fig_trend_nat.update_layout(height=380, legend_title_text="<b>📅 統計年份</b>")
        st.plotly_chart(fig_trend_nat, use_container_width=True)
        st.caption("六大外籍客源市場 2023→2025 的住客人次逐年變化；各市場份額結構見下方總表。")

        # 完整國籍統計表格
        st.markdown('<div class="section-divider-title">📋 2023–2025 年全台觀光旅館住客國籍統計總表</div>', unsafe_allow_html=True)
        st.dataframe(df_nat, use_container_width=True)


# ══════════════════════════════════════════════════════════
# 頁面四：影響因素與特徵解析
# ══════════════════════════════════════════════════════════
elif page == "🔍 影響因素與特徵解析":

    st.subheader("🔍 住房率核心影響因素與機器學習特徵分析")

    if df is None:
        st.warning("⚠️ 尚未載入資料")
    else:
        col1, col2 = st.columns(2)
        with col1:
            price_bin = df.dropna(subset=["avg_price", "occupancy_rate"]).copy()
            price_bin["房價區間"] = pd.qcut(price_bin["avg_price"], 8, duplicates="drop")
            price_grp = (
                price_bin.groupby("房價區間", observed=True)["occupancy_rate"]
                .mean().reset_index(name="平均住房率")
            )
            price_grp["房價區間"] = price_grp["房價區間"].apply(
                lambda seg: f"{seg.left:,.0f}–{seg.right:,.0f}"
            )
            fig_price = px.bar(
                price_grp, x="房價區間", y="平均住房率",
                labels={"房價區間": "平均房價區間 (NT$)", "平均住房率": "平均住房率 (%)"},
                template="plotly_dark", color="平均住房率",
                color_continuous_scale="Blues", text_auto=".1f",
            )
            fig_price.update_yaxes(rangemode="tozero")
            fig_price.update_layout(coloraxis_showscale=False, xaxis_tickangle=-30)
            style_chart(fig_price, "💰 平均房價區間 vs 平均住房率")
            st.plotly_chart(fig_price, use_container_width=True)
            st.caption("將所有旅館-月資料依平均房價分成 8 等分，每組取平均住房率；比單點散布更能看出趨勢。")

        with col2:
            room_bin = df.dropna(subset=["total_rooms", "occupancy_rate"]).copy()
            room_bin["客房規模"] = pd.qcut(room_bin["total_rooms"], 6, duplicates="drop")
            room_grp = (
                room_bin.groupby("客房規模", observed=True)["occupancy_rate"]
                .mean().reset_index(name="平均住房率")
            )
            room_grp["客房規模"] = room_grp["客房規模"].apply(
                lambda seg: f"{seg.left:,.0f}–{seg.right:,.0f}"
            )
            fig_room = px.bar(
                room_grp, x="客房規模", y="平均住房率",
                labels={"客房規模": "客房數區間", "平均住房率": "平均住房率 (%)"},
                template="plotly_dark", color="平均住房率",
                color_continuous_scale="Teal", text_auto=".1f",
            )
            fig_room.update_yaxes(rangemode="tozero")
            fig_room.update_layout(coloraxis_showscale=False, xaxis_tickangle=-30)
            style_chart(fig_room, "🏢 客房規模區間 vs 平均住房率")
            st.plotly_chart(fig_room, use_container_width=True)
            st.caption("將旅館-月資料依客房數分成 6 等分，每組取平均住房率。")

        # 特徵重要性排行
        fi_path = REPORTS_DIR / "feature_importance_monthly_current.csv"
        if fi_path.exists():
            fi = pd.read_csv(fi_path).head(12)
            fig_fi = px.bar(
                fi.sort_values("importance", ascending=True),
                x="importance", y="feature",
                labels={"importance": "重要性權重", "feature": "特徵名稱"},
                template="plotly_dark",
                orientation="h",
                color="importance",
                color_continuous_scale="Blues",
            )
            style_chart(fig_fi, "🎯 機器學習模型特徵重要性排行 (Top 12 Features)")
            st.plotly_chart(fig_fi, use_container_width=True)
            top3_share = fi.sort_values("importance", ascending=False).head(3)["importance"].sum()
            st.caption(
                f"重點：前三名特徵（前 1 月、近 3 月、去年同月住房率）合計約佔重要性 {top3_share:.0%}，"
                "模型主要依賴住房率本身的慣性與季節性；房價、旅客結構、員工數等營運輸入影響有限。"
                "特徵重要性代表模型依賴程度，不代表因果關係。"
            )

        # 模型評估排行榜
        results_path = REPORTS_DIR / "model_results_monthly_current.json"
        if results_path.exists():
            import json
            with open(results_path, encoding="utf-8") as f:
                res_data = json.load(f)
            res_df = pd.DataFrame(res_data).T
            st.subheader("📋 2026 上半年時間外測試表現")
            st.dataframe(res_df.style.format("{:.2f}"), use_container_width=True)
            st.caption(
                "此表為 2026 年 1–6 月的時間外測試（模型僅用 2023-01～2025-12 訓練），"
                "與「月度預測分析」頁的驗證數字為同一份結果，並非另一次獨立測試。"
            )


# ══════════════════════════════════════════════════════════
# 頁面五：個別旅館年度實績（自主體分析獨立出來的分析主題）
# ══════════════════════════════════════════════════════════
elif page == "🏨 個別旅館年度實績":

    st.subheader("🏨 個別旅館 2023–2025 年營運實績與人力效率")
    st.markdown(
        "由官方月報彙整到年度，逐間檢視單一旅館的客房營收、年增率、加權住房率與人力效率。"
        "本頁只呈現歷史事實，不做預測。"
    )

    if df is None:
        st.warning("⚠️ 尚未載入資料")
    else:
        hotel_base = df.copy()
        hotel_base["month_date"] = pd.to_datetime(
            dict(year=hotel_base["year"], month=hotel_base["month"], day=1),
            errors="coerce",
        )
        hotel_base["available_room_nights"] = (
            pd.to_numeric(hotel_base["total_rooms"], errors="coerce")
            * hotel_base["month_date"].dt.days_in_month
        )
        hotel_base["sold_room_nights"] = pd.to_numeric(hotel_base["rooms_used"], errors="coerce")
        hotel_base["room_revenue_numeric"] = pd.to_numeric(hotel_base["room_revenue"], errors="coerce")
        hotel_base["employees_numeric"] = pd.to_numeric(hotel_base["employees"], errors="coerce")
        hotel_base["rooms_numeric"] = pd.to_numeric(hotel_base["total_rooms"], errors="coerce")

        history_hotel = st.selectbox(
            "選擇旅館查看 2023–2025 年實績",
            sorted(hotel_base["clean_hotel_name"].dropna().unique()),
            key="hotel_yearly_page",
        )
        selected_history = hotel_base[hotel_base["clean_hotel_name"] == history_hotel]
        hotel_yearly = (
            selected_history.groupby("year", as_index=False)
            .agg(
                客房營收=("room_revenue_numeric", "sum"),
                平均員工數=("employees_numeric", "mean"),
                平均客房數=("rooms_numeric", "mean"),
                可售客房間夜=("available_room_nights", "sum"),
                已售客房間夜=("sold_room_nights", "sum"),
            )
            .sort_values("year")
        )
        hotel_yearly["營收年增率"] = hotel_yearly["客房營收"].pct_change() * 100
        hotel_yearly["每位員工服務客房數"] = np.where(
            hotel_yearly["平均員工數"] > 0,
            hotel_yearly["平均客房數"] / hotel_yearly["平均員工數"],
            np.nan,
        )
        hotel_yearly["每位員工客房營收"] = np.where(
            hotel_yearly["平均員工數"] > 0,
            hotel_yearly["客房營收"] / hotel_yearly["平均員工數"],
            np.nan,
        )
        hotel_yearly["加權住房率"] = np.where(
            hotel_yearly["可售客房間夜"] > 0,
            hotel_yearly["已售客房間夜"] / hotel_yearly["可售客房間夜"] * 100,
            np.nan,
        )

        hotel_chart1, hotel_chart2 = st.columns(2)
        with hotel_chart1:
            revenue_figure = px.bar(
                hotel_yearly,
                x="year",
                y="客房營收",
                text_auto=".3s",
                color="客房營收",
                color_continuous_scale="Blues",
                labels={"year": "年度", "客房營收": "客房營收（NT$）"},
                template="plotly_dark",
            )
            style_chart(revenue_figure, f"💰 {history_hotel} 年度客房營收變化")
            revenue_figure.update_layout(coloraxis_showscale=False)
            revenue_figure.update_yaxes(rangemode="tozero")
            revenue_figure.update_xaxes(type="category")
            st.plotly_chart(revenue_figure, use_container_width=True)
        with hotel_chart2:
            efficiency_figure = px.bar(
                hotel_yearly,
                x="year",
                y="每位員工服務客房數",
                text_auto=".2f",
                color="每位員工服務客房數",
                color_continuous_scale="Teal",
                labels={"year": "年度", "每位員工服務客房數": "客房數／員工數"},
                template="plotly_dark",
            )
            style_chart(efficiency_figure, f"👥 {history_hotel} 每位員工服務客房數")
            efficiency_figure.update_layout(coloraxis_showscale=False)
            efficiency_figure.update_yaxes(rangemode="tozero")
            efficiency_figure.update_xaxes(type="category")
            st.plotly_chart(efficiency_figure, use_container_width=True)

        hotel_yearly_display = hotel_yearly.copy()
        hotel_yearly_display["營收年增率"] = hotel_yearly_display["營收年增率"].map(
            lambda value: f"{value:+.1f}%" if pd.notna(value) else "—"
        )
        st.dataframe(
            hotel_yearly_display[[
                "year", "加權住房率", "客房營收", "營收年增率",
                "平均客房數", "平均員工數", "每位員工服務客房數", "每位員工客房營收",
            ]].rename(columns={"year": "年度"}).style.format({
                "加權住房率": "{:.2f}%",
                "客房營收": "NT${:,.0f}",
                "平均客房數": "{:,.0f}",
                "平均員工數": "{:,.0f}",
                "每位員工服務客房數": "{:.2f}",
                "每位員工客房營收": "NT${:,.0f}",
            }),
            use_container_width=True,
        )
        st.caption(
            "加權住房率＝該旅館全年已售客房間夜 ÷ 可售客房間夜；"
            "「每位員工服務客房數」＝平均客房數 ÷ 平均員工數（人力配置密度）；"
            "「每位員工客房營收」＝年客房營收 ÷ 平均員工數（人力生產力，已同時反映住房率與房價）。員工數採月報平均。"
        )

        st.markdown('<div class="section-divider-title">📈 該旅館逐月住房率（2023-01～2025-12）</div>', unsafe_allow_html=True)
        monthly_trend = selected_history.sort_values("month_date")[["month_date", "occupancy_rate"]].dropna()
        if not monthly_trend.empty:
            fig_hotel_month = px.line(
                monthly_trend, x="month_date", y="occupancy_rate", markers=True,
                labels={"month_date": "月份", "occupancy_rate": "住房率 (%)"},
                template="plotly_dark",
            )
            fig_hotel_month.update_traces(line_color="#38bdf8")
            fig_hotel_month.update_yaxes(rangemode="tozero")
            style_chart(fig_hotel_month, f"📈 {history_hotel} 逐月住房率")
            st.plotly_chart(fig_hotel_month, use_container_width=True)
            st.caption(
                "年度實績表只呈現全年加權平均，這張圖顯示同一年內的淡旺季起伏；"
                "跨月與未來預測請至「月度預測分析」頁。"
            )

        st.markdown('<div class="section-divider-title">⚖️ 與同儕比較（2023–2025 合計）</div>', unsafe_allow_html=True)

        def _agg_metrics(frame):
            avail = frame["available_room_nights"].sum()
            sold = frame["sold_room_nights"].sum()
            rev = frame["room_revenue_numeric"].sum()
            return {
                "加權住房率": sold / avail * 100 if avail else np.nan,
                "ADR": rev / sold if sold else np.nan,
                "RevPAR": rev / avail if avail else np.nan,
            }

        peer_rows = [{"比較對象": f"本旅館：{history_hotel}", "觀光旅館數": 1, **_agg_metrics(selected_history)}]
        star_mode = selected_history["star_rating"].mode()
        city_mode = selected_history["city"].mode()
        if not star_mode.empty:
            peer_star = str(star_mode.iloc[0])
            star_peers = hotel_base[
                (hotel_base["star_rating"] == peer_star)
                & (hotel_base["clean_hotel_name"] != history_hotel)
            ]
            peer_rows.append({
                "比較對象": f"同星等（{peer_star}）平均",
                "觀光旅館數": int(star_peers["clean_hotel_name"].nunique()),
                **_agg_metrics(star_peers),
            })
        if not city_mode.empty:
            peer_city = str(city_mode.iloc[0])
            city_peers = hotel_base[
                (hotel_base["city"] == peer_city)
                & (hotel_base["clean_hotel_name"] != history_hotel)
            ]
            peer_rows.append({
                "比較對象": f"同縣市（{peer_city}）平均",
                "觀光旅館數": int(city_peers["clean_hotel_name"].nunique()),
                **_agg_metrics(city_peers),
            })
        peer_table = pd.DataFrame(peer_rows)
        st.dataframe(
            peer_table.style.format({
                "觀光旅館數": "{:.0f}", "加權住房率": "{:.2f}%",
                "ADR": "NT${:,.0f}", "RevPAR": "NT${:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )
        peer_counts = peer_table["觀光旅館數"].iloc[1:]
        peer_note = "同儕平均以 2023–2025 全期彙總計算，並已排除本旅館本身。"
        if not peer_counts.empty and peer_counts.min() < 5:
            peer_note += f" 注意：最小同儕組僅 {int(peer_counts.min())} 間，平均值代表性有限。"
        st.caption(peer_note)
