# -*- coding: utf-8 -*-
"""
把 facts.json 攤平成 Power BI 一鍵匯入用的 Excel 活頁簿（每張表一個分頁）。
不產生 .pbix（沒有對應工具能寫出這個二進位格式），這份檔案是給
Power BI Desktop「取得資料 → Excel活頁簿」匯入用的乾淨資料來源。

執行：python export_powerbi.py
輸出：powerbi_匯入資料_1130.xlsx
"""
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
F = json.loads((HERE / "facts.json").read_text(encoding="utf-8"))
OUT = HERE / "powerbi_匯入資料_1130.xlsx"

RESORT_CITIES = ["宜蘭縣", "花蓮縣", "南投縣", "屏東縣", "台東縣", "澎湖縣", "金門縣", "嘉義縣"]

sheets = {}

# ── 00 旅館月度原始資料（列層級，給 DAX 量值用）─────────────
import calendar as _cal

_raw = pd.read_csv(HERE.parent / "data" / "processed" / "hotel_monthly.csv")
_raw["可售房晚"] = _raw["total_rooms"] * [
    _cal.monthrange(int(y), int(m))[1] for y, m in zip(_raw["year"], _raw["month"])
]
_raw["已售房晚"] = _raw["rooms_used"]
_raw["聚落"] = _raw["city"].apply(lambda c: "風景度假" if c in RESORT_CITIES else "都會商務")
_raw["資料範圍"] = _raw["year"].apply(lambda y: "主分析(2023-2025)" if 2023 <= y <= 2025 else "盲測期(2026)")
_raw["年月"] = pd.to_datetime(dict(year=_raw["year"], month=_raw["month"], day=1))
_raw = _raw.rename(columns={
    "year": "年", "month": "月", "city": "縣市", "hotel_name": "旅館名稱",
    "total_rooms": "房間數", "occupancy_rate": "住房率", "avg_price": "平均房價",
    "room_revenue": "客房營收", "food_revenue": "餐飲營收", "total_revenue": "總營收",
    "employees": "員工數", "domestic_ratio": "本國客佔比", "international_ratio": "國際客佔比",
    "individual_ratio": "散客佔比", "revpar": "RevPAR", "star_rating": "星等", "has_star": "有星等",
})
sheets["旅館月度原始資料"] = _raw[[
    "年月", "年", "月", "資料範圍", "縣市", "聚落", "旅館名稱", "星等", "有星等", "房間數",
    "可售房晚", "已售房晚", "住房率", "平均房價", "RevPAR", "客房營收", "餐飲營收", "總營收",
    "員工數", "本國客佔比", "國際客佔比", "散客佔比",
]]

# ── 01 年度營運總覽（加權）──────────────────────────────────
A = F["annual"]
sheets["年度營運總覽"] = pd.DataFrame({
    "年度": A["years"],
    "加權住房率(%)": A["occ"],
    "平均房價ADR": A["adr"],
    "每可售房收益RevPAR": A["revpar"],
    "已售房晚(萬)": A["sold_wan"],
    "可售房晚(萬)": A["avail_wan"],
    "客房營收(億)": A["room_rev_yi"],
    "餐飲營收(億)": A["food_rev_yi"],
    "總營收含其他(億)": A["total_rev_yi"],
    "住客人次(萬)": A["guests_wan"],
    "旅館家數": A["hotels"],
    "全年12月完整家數": A["hotels_12m"],
})

# ── 02 指數化（2023=100）────────────────────────────────────
IDX = F["index"]
sheets["指數化2023為100"] = pd.DataFrame({
    "年度": IDX["years"],
    "住房率指數": IDX["occ"],
    "ADR指數": IDX["adr"],
    "RevPAR指數": IDX["revpar"],
})

# ── 03 月份季節性（簡單平均 + 加權）─────────────────────────
SEA = F["season"]
season_rows = []
for i, m in enumerate(SEA["months"]):
    season_rows.append({"月份": m, "聚落": "都會商務", "簡單平均住房率(%)": SEA["urban"][i]})
    season_rows.append({"月份": m, "聚落": "風景度假", "簡單平均住房率(%)": SEA["resort"][i]})
sheets["月份季節性"] = pd.DataFrame(season_rows)

sheets["聚落財務結構_加權"] = pd.DataFrame({
    "聚落": ["都會商務", "風景度假"],
    "加權ADR": [SEA["urban_adr_w"], SEA["resort_adr_w"]],
    "加權RevPAR": [SEA["urban_revpar_w"], SEA["resort_revpar_w"]],
    "簡單平均住房率(%)": [SEA["urban_mean"], SEA["resort_mean"]],
    "加權住房率(%)": [SEA["urban_mean_w"], SEA["resort_mean_w"]],
})

# ── 04 縣市排行 ──────────────────────────────────────────────
CITY = F["city"]
sheets["縣市排行"] = pd.DataFrame({
    "縣市": CITY["names"],
    "旅館家數": CITY["n"],
    "加權住房率(%)": CITY["occ_weighted"],
    "簡單平均住房率(%)": CITY["occ_simple"],
    "營收佔全台比例(%)": CITY["rev_share"],
    "是否度假縣市": ["是" if c in RESORT_CITIES else "否" for c in CITY["names"]],
})

# ── 05 客源結構 ──────────────────────────────────────────────
GU = F["guests"]
sheets["客源結構"] = pd.DataFrame({
    "年度": GU["years"],
    "本國旅客佔比(%)": GU["dom_ratio"],
    "國際旅客佔比(%)": GU["intl_ratio"],
    "散客佔比(%)": GU["fit_ratio"],
    "團體佔比(%)": GU["group_ratio"],
    "日本(萬人次)": GU["japan_wan"],
    "美國(萬人次)": GU["usa_wan"],
    "韓國(萬人次)": GU["korea_wan"],
    "港澳(萬人次)": GU["hkmo_wan"],
})

# ── 06 中國大陸來臺旅客年表（獨立 CSV，直接併入）───────────
cv_path = HERE.parent / "data" / "processed" / "china_visitors_annual.csv"
cv = pd.read_csv(cv_path, encoding="utf-8-sig")
cv.columns = ["年度", "陸客來台萬人次", "備註"]
sheets["陸客來台年表"] = cv

# ── 07 星等效益 ──────────────────────────────────────────────
ST = F["star"]
sheets["星等效益"] = pd.DataFrame({
    "星等": ST["names"],
    "家數": ST["n"],
    "加權住房率(%)": ST["occ"],
    "平均房價ADR": ST["adr"],
    "每房收益RevPAR": ST["revpar"],
    "客房營收佔比(%)": ST["rev_share"],
})

sheets["有無星等對照"] = pd.DataFrame({
    "分組": ["有星等", "無星等"],
    "簡單平均住房率(%)": [F["star_gap"]["occ_simple"]["star"], F["star_gap"]["occ_simple"]["nostar"]],
    "加權住房率(%)": [F["star_gap"]["occ_weighted"]["star"], F["star_gap"]["occ_weighted"]["nostar"]],
    "加權ADR": [F["star_gap"]["adr_weighted"]["star"], F["star_gap"]["adr_weighted"]["nostar"]],
})

SO = F["star_ols"]
star_ols_rows = [{"項目": "原始差距(全樣本pp)", "數值": F["star_gap"]["occ_simple"]["gap_pp"]},
                  {"項目": "原始差距(迴歸樣本pp)", "數值": SO["raw_gap_pp"]},
                  {"項目": "控制後差距(pp)", "數值": SO["controlled_pp"]},
                  {"項目": "95%信賴區間下界", "數值": SO["ci_lo"]},
                  {"項目": "95%信賴區間上界", "數值": SO["ci_hi"]},
                  {"項目": "樣本旅館家數", "數值": SO["n_hotels"]}]
for s in ["三星級", "四星級", "五星級", "卓越五星"]:
    star_ols_rows.append({"項目": f"{s}_原始差(pp)", "數值": SO["by_star"][s]["raw_pp"]})
    star_ols_rows.append({"項目": f"{s}_控制後差(pp)", "數值": SO["by_star"][s]["controlled_pp"]})
sheets["星等OLS控制分析"] = pd.DataFrame(star_ols_rows)

# ── 08 房價與規模非線性 ─────────────────────────────────────
PB = F["price_bins"]
sheets["房價八分位"] = pd.DataFrame({
    "房價區間": PB["labels"],
    "住房率(%)": PB["occ"],
    "樣本數": PB["n"],
})

RB = F["room_bins"]
sheets["規模四分位"] = pd.DataFrame({
    "規模區間": RB["labels"],
    "旅館家數": RB["hotels"],
    "簡單平均住房率(%)": RB["occ_simple"],
    "加權住房率(%)": RB["occ_weighted"],
    "簡單平均ADR": RB["adr_simple"],
    "加權ADR": RB["adr_weighted"],
})

# ── 09 模型效益／比較 ────────────────────────────────────────
BL = F["baselines"]
sheets["多基準對照"] = pd.DataFrame({
    "方法": [r["name"] for r in BL["rows"]],
    "MAE_pp": [r["mae"] for r in BL["rows"]],
})

M = F["model"]
sheets["候選模型比較"] = pd.DataFrame(M["candidates"])[["name", "mae", "rmse", "r2", "bias", "n"]].rename(
    columns={"name": "模型", "mae": "MAE", "rmse": "RMSE", "r2": "R2", "bias": "Bias", "n": "樣本數"})

sheets["期程衰減"] = pd.DataFrame(M["horizons"])[["h", "mae", "rmse", "r2", "bias"]].rename(
    columns={"h": "第幾個月", "mae": "MAE", "rmse": "RMSE", "r2": "R2", "bias": "Bias"})

# ── 10 特徵重要性 ────────────────────────────────────────────
FI = F["importance"]
nm_map = {"occupancy_lag_1": "前1月住房率", "occupancy_roll3": "近3月均值",
          "occupancy_lag_12": "去年同月", "month": "月份", "month_sin": "月份循環",
          "occupancy_lag_2": "前2月住房率", "input_domestic_ratio": "本國客佔比",
          "input_international_ratio": "國際客佔比"}
sheets["特徵重要性"] = pd.DataFrame({
    "特徵": [nm_map.get(n, n) for n in FI["names"]],
    "重要性(%)": FI["values"],
})

# ── 11 穩健性／縣市誤差 ──────────────────────────────────────
RO = F["robust"]
city_rows = []
for c, v in RO["by_city"].items():
    city_rows.append({"縣市": c, "MAE": v["MAE"], "RMSE": v["RMSE"], "R2": v["R2"],
                       "Bias": v["bias"], "旅館家數": v["hotels"], "樣本筆數": v["n"],
                       "是否度假縣市": "是" if c in RESORT_CITIES else "否"})
sheets["縣市預測誤差"] = pd.DataFrame(city_rows)

sheets["樣本穩健性"] = pd.DataFrame([
    {"分組": "全體", "MAE": RO["all"]["MAE"], "旅館家數": RO["all"]["hotels"], "樣本筆數": RO["all"]["n"]},
    {"分組": "三年皆在榜(平衡樣本)", "MAE": RO["balanced"]["MAE"],
     "旅館家數": RO["balanced"]["hotels"], "樣本筆數": RO["balanced"]["n"]},
])

# ── 寫出 Excel，一次一個分頁 ─────────────────────────────────
with pd.ExcelWriter(OUT, engine="openpyxl") as writer:
    for name, df in sheets.items():
        df.to_excel(writer, sheet_name=name[:31], index=False)  # Excel 分頁名上限 31 字

print(f"已輸出：{OUT}")
print(f"共 {len(sheets)} 個分頁：")
for name, df in sheets.items():
    print(f"  {name}｜{len(df)} 列 × {len(df.columns)} 欄")
