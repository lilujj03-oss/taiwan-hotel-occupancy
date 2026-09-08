"""
preprocessing.py
完整解析觀光署 2023–2025 年觀光旅館營運統計 Excel 檔
提取：
1. Part 1: 各旅館之客房數、住用數、住用率、平均房價、客房/餐飲/總營收、員工人數
2. Part 2: 各旅館之散客(FIT)/團體客(Group)人數、本國旅客、國際旅客來源國籍分佈
3. 星級認證標籤 (1星~卓越5星 vs 無星等/未評鑑)
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
import re
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
CORRECTED_OUTPUT = PROCESSED_DIR / "hotel_combined_corrected.csv"

# 觀光署官方星等對照庫
STAR_DATABASE = {
    # 卓越五星 (6星)
    "台北美福大飯店": 6, "美福大飯店": 6, "台北文華東方酒店": 6, "文華東方酒店": 6,
    # 五星級 (5星)
    "圓山大飯店": 5, "台北寒舍喜來登大飯店": 5, "老爺大酒店": 5, "福華大飯店": 5,
    "台北君悅酒店": 5, "晶華酒店": 5, "台北遠東香格里拉": 5, "台北W飯店": 5,
    "君品酒店": 5, "台北君品大酒店": 5, "寒舍艾美酒店": 5, "台北寒舍艾美酒店": 5,
    "寒舍艾麗酒店": 5, "台北艾麗酒店": 5, "大倉久和大飯店": 5,
    "台北萬豪酒店": 5, "萬豪酒店": 5, "台北新板希爾頓酒店": 5, "板橋凱撒大飯店": 5,
    "長榮桂冠酒店(台中)": 5, "台中金典酒店": 5, "裕元花園酒店": 5, "台中日月千禧酒店": 5,
    "台中福華大飯店": 5, "全國大飯店": 5,
    "台南晶英酒店": 5, "香格里拉台南遠東國際大飯店": 5, "台南遠東香格里拉": 5, "台糖長榮酒店(台南)": 5,
    "台南大員皇冠假日酒店": 5,
    "高雄漢來大飯店": 5, "漢來大飯店": 5, "高雄國賓大飯店": 5, "高雄洲際酒店": 5,
    "高雄萬豪酒店": 5, "高雄福華大飯店": 5, "寒軒國際大飯店": 5, "高雄圓山大飯店": 5,
    "長榮鳳凰酒店(礁溪)": 5, "礁溪老爺酒店": 5, "蘭城晶英酒店": 5,
    "涵碧樓大飯店": 5, "雲品溫泉酒店日月潭": 5, "日月潭涵碧樓": 5, "日月潭力麗溫德姆溫泉酒店": 5,
    "花蓮遠雄悅來大飯店": 5, "遠雄悅來大飯店": 5, "花蓮理想大地渡假飯店": 5, "理想大地渡假飯店": 5,
    "美侖大飯店": 5, "太魯閣晶英酒店": 5, "瑞穗天合國際觀光酒店": 5,
    "知本老爺大酒店": 5, "娜路彎大酒店": 5, "台東桂田喜來登酒店": 5,
    "墾丁福華渡假飯店": 5, "墾丁凱撒大飯店": 5, "凱撒大飯店": 5,
    "澎湖福朋喜來登酒店": 5, "長榮桂冠酒店(基隆)": 5, "耐斯王子大飯店": 5,
    # 四星級 (4星)
    "福容大飯店    淡水漁人碼頭": 4, "福容大飯店 淡水漁人碼頭": 4, "大板根渡假酒店": 4,
    "台北凱撒大飯店": 4, "亞都麗緻大飯店": 4, "國聯大飯店": 4, "兄弟大飯店": 4,
    "天成大飯店": 4, "第一大飯店": 4, "歐華酒店": 4, "福容大飯店  台北一館": 4,
    "台北花園大酒店": 4, "北投麗禧溫泉酒店": 4, "北投老爺酒店": 4, "JR東日本大飯店台北": 4,
    "新竹喜來登大飯店": 4, "豐邑喜來登大飯店": 4, "新竹老爺大酒店": 4, "新竹國賓大飯店": 4,
    "煙波大飯店": 4, "清新溫泉飯店": 4, "義大皇家酒店": 4, "晶英國際行館": 4,
    "南方莊園渡假飯店": 4, "台北諾富特華航桃園機場飯店": 4, "桃園喜來登酒店": 4, "和逸飯店桃園青埔館": 4,
    "綠舞國際觀光飯店": 4, "悅川酒店": 4, "阿里山賓館(現代館)": 4, "阿里山賓館(歷史館)": 4,
    # 三星級 (3星)
    "雀客藏居台北陽明山": 3, "豪景大酒店": 3, "國王大飯店": 3, "三德大飯店": 3,
    "瓏山林台北中和飯店": 3, "福容大飯店 福隆": 3, "八里福朋喜來登酒店": 3,
    "尊爵天際大飯店": 3, "尊爵大飯店": 3, "古華花園飯店": 3, "福容大飯店   桃園": 3,
    "通豪大飯店": 3, "台中港酒店": 3, "台南大飯店": 3, "趣淘漫旅": 3,
    "麗尊大酒店": 3, "福容大飯店 高雄": 3, "馥藝金鬱金香酒店": 3, "山泉大飯店": 3,
    "幼獅大飯店": 3, "名都觀光渡假大飯店": 3, "墾丁怡灣渡假酒店": 3, "鈺通大飯店": 3,
}

STAR_LABELS = {6: "卓越五星", 5: "五星級", 4: "四星級", 3: "三星級", 2: "二星級", 1: "一星級"}

CITIES = ["新北市", "臺北市", "台北市", "桃園市", "臺中市", "台中市", "臺南市", "台南市",
          "高雄市", "宜蘭縣", "新竹縣", "苗栗縣", "彰化縣", "南投縣", "雲林縣", "嘉義縣",
          "嘉義市", "屏東縣", "臺東縣", "台東縣", "花蓮縣", "澎湖縣", "基隆市", "新竹市", "金門縣"]


def parse_year_data(year: int) -> pd.DataFrame:
    path = RAW_DIR / f"hotel_{year}.xlsx"
    if not path.exists():
        raise FileNotFoundError(f"找不到檔案：{path}")

    df_raw = pd.read_excel(path, header=None)

    # 找到 Part 1 與 Part 2 的分界點 (住客類別統計)
    split_idx = len(df_raw)
    for idx, row in df_raw.iterrows():
        text = " ".join([str(x) for x in row.values if pd.notna(x)])
        if idx > 50 and ("住客類別統計" in text or "各地區旅客人數統計" in text):
            split_idx = idx
            break

    part1_df = df_raw.iloc[:split_idx].copy()
    part2_df = df_raw.iloc[split_idx:].copy()

    # 解析 Part 1 (營運及營收指標)
    hotels_p1 = {}
    current_city = "未知"

    for idx, row in part1_df.iterrows():
        r_str = [str(x).strip() for x in row.values if pd.notna(x)]
        if not r_str:
            continue
        row_text = " ".join(r_str)

        for c in CITIES:
            if c in row_text and ("資料期間" in row_text or "Data for" in row_text):
                current_city = c.replace("臺", "台")
                break

        first_val = str(row.iloc[0]).strip()
        # 排除地區彙總列（2025 年英文版資料中的分類名稱不同）
        aggregate_names = {
            "國際", "一般", "小計", "合計", "總計",
            "國際Internation", "一般Standard", "小計SubTotal",
        }
        if first_val in aggregate_names or first_val.lower() in {
            "international", "standard", "subtotal", "total"
        }:
            continue
        # 排除標題列與彙整總計列
        if (first_val and first_val not in ["旅館名稱", "地區名稱", "總計", "小計", "國際", "一般", "合計", "nan", ""]
            and not first_val.startswith("觀光旅館營運")
            and not first_val.startswith("列印日期")
            and not first_val.startswith("Data for")):

            clean_name = re.sub(r"^[\*\#\s]+", "", first_val).strip()

            # 2023/2024 的明細列：客房數在 Col 5、住用數在 Col 6。
            # 2025 英文版明細列：客房數移到 Col 3、住用數在 Col 5。
            if year == 2025:
                total_rooms = pd.to_numeric(row.iloc[3], errors="coerce") if len(row) > 3 else np.nan
                rooms_used = pd.to_numeric(row.iloc[5], errors="coerce") if len(row) > 5 else np.nan
            else:
                total_rooms = pd.to_numeric(row.iloc[5], errors="coerce") if len(row) > 5 else np.nan
                rooms_used = pd.to_numeric(row.iloc[6], errors="coerce") if len(row) > 6 else np.nan
            occ_rate = pd.to_numeric(row.iloc[8], errors="coerce") if len(row) > 8 else np.nan
            avg_price = pd.to_numeric(row.iloc[9], errors="coerce") if len(row) > 9 else np.nan
            room_rev = pd.to_numeric(row.iloc[11], errors="coerce") if len(row) > 11 else np.nan
            food_rev = pd.to_numeric(row.iloc[12], errors="coerce") if len(row) > 12 else np.nan
            total_rev = pd.to_numeric(row.iloc[13], errors="coerce") if len(row) > 13 else np.nan
            employees = pd.to_numeric(row.iloc[28], errors="coerce") if len(row) > 28 else np.nan

            if pd.notna(occ_rate) and clean_name not in CITIES:
                if occ_rate <= 1.0:
                    occ_rate = occ_rate * 100

                hotels_p1[clean_name] = {
                    "year": year,
                    "city": current_city,
                    "hotel_name": clean_name,
                    "total_rooms": total_rooms,
                    "rooms_used": rooms_used,
                    "occupancy_rate": occ_rate,
                    "avg_price": avg_price,
                    "room_revenue": room_rev,
                    "food_revenue": food_rev,
                    "total_revenue": total_rev,
                    "employees": employees,
                }

    # 解析 Part 2 (客源結構)
    hotels_p2 = {}
    current_city = "未知"

    for idx, row in part2_df.iterrows():
        r_str = [str(x).strip() for x in row.values if pd.notna(x)]
        if not r_str:
            continue
        row_text = " ".join(r_str)

        for c in CITIES:
            if c in row_text and ("資料期間" in row_text or "Data for" in row_text):
                current_city = c.replace("臺", "台")
                break

        first_val = str(row.iloc[0]).strip()
        if (first_val and first_val not in ["旅館名稱", "地區名稱", "總計", "小計", "國際", "一般", "合計", "nan", ""]
            and not first_val.startswith("觀光旅館營運")
            and not first_val.startswith("列印日期")
            and not first_val.startswith("Data for")):

            clean_name = re.sub(r"^[\*\#\s]+", "", first_val).strip()

            # Col 2(FIT), Col 3(GROUP), Col 4(類別合計), Col 5(本國), Col 7(日本), Col 8(南韓), Col 9(港澳), Col 23(美國)
            fit_guests = pd.to_numeric(row.iloc[2], errors="coerce") if len(row) > 2 else np.nan
            group_guests = pd.to_numeric(row.iloc[3], errors="coerce") if len(row) > 3 else np.nan
            total_guests = pd.to_numeric(row.iloc[4], errors="coerce") if len(row) > 4 else np.nan
            domestic_guests = pd.to_numeric(row.iloc[5], errors="coerce") if len(row) > 5 else np.nan
            japan_guests = pd.to_numeric(row.iloc[7], errors="coerce") if len(row) > 7 else np.nan
            korea_guests = pd.to_numeric(row.iloc[8], errors="coerce") if len(row) > 8 else np.nan
            hk_mo_guests = pd.to_numeric(row.iloc[9], errors="coerce") if len(row) > 9 else np.nan
            usa_guests = pd.to_numeric(row.iloc[23], errors="coerce") if len(row) > 23 else np.nan

            hotels_p2[clean_name] = {
                "individual_guests": fit_guests,
                "group_guests": group_guests,
                "total_guests": total_guests,
                "domestic_guests": domestic_guests,
                "japan_guests": japan_guests,
                "korea_guests": korea_guests,
                "hk_mo_guests": hk_mo_guests,
                "usa_guests": usa_guests,
            }

    # 合併 Part 1 與 Part 2
    records = []
    for hname, p1_data in hotels_p1.items():
        p2_data = hotels_p2.get(hname, {})
        row_data = {**p1_data, **p2_data}

        # 旅客結構比例
        tot_g = row_data.get("total_guests")
        dom_g = row_data.get("domestic_guests")
        fit_g = row_data.get("individual_guests")

        if pd.notna(tot_g) and tot_g > 0:
            row_data["domestic_ratio"] = (dom_g / tot_g) if pd.notna(dom_g) else np.nan
            row_data["international_ratio"] = 1.0 - row_data["domestic_ratio"] if pd.notna(row_data["domestic_ratio"]) else np.nan
            row_data["individual_ratio"] = (fit_g / tot_g) if pd.notna(fit_g) else np.nan
        else:
            row_data["domestic_ratio"] = np.nan
            row_data["international_ratio"] = np.nan
            row_data["individual_ratio"] = np.nan

        # RevPAR 計算
        if pd.notna(row_data["avg_price"]) and pd.notna(row_data["occupancy_rate"]):
            row_data["revpar"] = row_data["avg_price"] * row_data["occupancy_rate"] / 100

        # 星等認證查詢
        star_rank = STAR_DATABASE.get(hname, np.nan)
        if pd.isna(star_rank):
            for k, v in STAR_DATABASE.items():
                if k in hname or hname in k:
                    star_rank = v
                    break

        row_data["star_rank"] = star_rank
        row_data["star_rating"] = STAR_LABELS.get(star_rank, "無星等/未評鑑" if pd.isna(star_rank) else "其他")
        row_data["has_star"] = 1 if pd.notna(star_rank) else 0

        records.append(row_data)

    df_out = pd.DataFrame(records)
    print(f"[{year}] 解析完成：共 {len(df_out)} 間旅館（星級認證：{df_out['has_star'].sum()} 間，無星等：{len(df_out)-df_out['has_star'].sum()} 間）")
    return df_out


def merge_all_years():
    dfs = []
    for y in [2023, 2024, 2025]:
        dfs.append(parse_year_data(y))
    combined = pd.concat(dfs, ignore_index=True)
    out_path = CORRECTED_OUTPUT
    combined.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n全部資料已整併儲存至：{out_path}")
    print(f"資料筆數：{len(combined)} 筆，涵蓋 {combined['hotel_name'].nunique()} 家觀光旅館")
    print(f"整體星級認證比例：{combined['has_star'].mean()*100:.1f}%")
    return combined


if __name__ == "__main__":
    df = merge_all_years()
    print("\n欄位清單：", df.columns.tolist())
    print("\n前 5 筆預覽：")
    print(df[["year", "city", "hotel_name", "star_rating", "occupancy_rate", "avg_price", "revpar"]].head())
