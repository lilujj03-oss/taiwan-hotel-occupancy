import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import re

df_raw = pd.read_excel("data/raw/hotel_2023.xlsx", header=None)
part1 = df_raw.iloc[:302]
hotels_p1 = {}
current_city = "未知"

CITIES = ["新北市", "臺北市", "台北市", "桃園市", "臺中市", "台中市", "臺南市", "台南市",
          "高雄市", "宜蘭縣", "新竹縣", "苗栗縣", "彰化縣", "南投縣", "雲林縣", "嘉義縣",
          "嘉義市", "屏東縣", "臺東縣", "台東縣", "花蓮縣", "澎湖縣", "基隆市", "新竹市", "金門縣"]

for idx, row in part1.iterrows():
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
        clean_name = re.sub(r"^[\*\#\s]+", "", first_val)
        occ_rate = pd.to_numeric(row.iloc[3], errors="coerce")
        print(f"Row {idx:3d}: Hotel='{clean_name}', City='{current_city}', Occ={occ_rate}")
        hotels_p1[clean_name] = occ_rate

print(f"\nTotal hotels in p1: {len(hotels_p1)}")
