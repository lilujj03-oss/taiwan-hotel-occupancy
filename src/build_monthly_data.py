"""
將交通部觀光署逐月觀光旅館月報解析成長格式資料。

輸入：data/raw/monthly/YYYYMM.xlsx（單月資料）
輸出：data/processed/hotel_monthly.csv
既有年度資料不會被覆蓋。
"""

import calendar
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from preprocessing import CITIES, STAR_DATABASE, STAR_LABELS


ROOT = Path(__file__).resolve().parent.parent
MONTHLY_DIR = ROOT / "data" / "raw" / "monthly"
OUTPUT = ROOT / "data" / "processed" / "hotel_monthly.csv"
CITY_OVERRIDES = {
    # 2026-03 起新版明細未列縣市；新開業旅館以觀光署旅宿資料補入。
    "紅羽莊園": "宜蘭縣",
}


def cell_text(value):
    return "" if pd.isna(value) else str(value).strip()


def first_index(headers, predicate):
    for i, value in enumerate(headers):
        if predicate(cell_text(value)):
            return i
    return None


def clean_name(value):
    name = cell_text(value).split("\n")[0]
    return re.sub(r"^[*#\s]+", "", name).strip()


def clean_city(value):
    value = cell_text(value).replace("臺", "台")
    for city in CITIES:
        city_clean = city.replace("臺", "台")
        if city_clean in value:
            return city_clean
    return "未知"


def is_total_name(name):
    compact = name.replace(" ", "")
    return compact in {
        "總計", "小計", "合計", "全臺合計", "全台合計", "國際", "一般",
        "國際Internation", "一般Standard", "小計SubTotal",
    }


def number(row, index):
    if index is None or index >= len(row):
        return np.nan
    return pd.to_numeric(row.iloc[index], errors="coerce")


def parse_file(path: Path):
    df = pd.read_excel(path, header=None, engine="openpyxl")
    year = int(path.stem[:4])
    month = int(path.stem[4:6])
    current_city = "未知"
    operations = {}
    nationality = {}
    mode = None
    columns = {}

    for _, row in df.iterrows():
        values = [cell_text(v) for v in row.tolist()]
        joined = " ".join(v for v in values if v)

        if "資料期間" in joined:
            current_city = clean_city(joined)

        if any("旅館名稱" in v and ("客房住用數" in joined or "客房數" in joined) for v in values):
            mode = "operations"
            employees_index = first_index(
                values, lambda x: "員工合計人數" in x or ("員工合計" in x and "人數" in x)
            )
            if employees_index is None:
                employees_group = first_index(values, lambda x: "員工合計" in x)
                if employees_group is not None:
                    employees_index = employees_group + 2
            columns = {
                "name": first_index(values, lambda x: "旅館名稱" in x),
                "rooms": first_index(
                    values,
                    lambda x: ("客房數" in x and "住用" not in x) or "可供住用數" in x,
                ),
                "rooms_are_room_nights": any("可供住用數" in x for x in values),
                "used": first_index(values, lambda x: "客房住用數" in x),
                "occupancy": first_index(values, lambda x: "住用率" in x),
                "price": first_index(values, lambda x: "平均房價" in x),
                "room_revenue": first_index(values, lambda x: "房租收入" in x or "客房收入" in x),
                "food_revenue": first_index(values, lambda x: "餐飲收入" in x or "F & B Revenue" in x),
                "total_revenue": first_index(values, lambda x: "總營業收入" in x or "Total Revenue" in x),
                "employees": employees_index,
            }
            continue

        if ("FIT類別" in joined or "個別旅客" in joined) and "旅館名稱" in joined:
            mode = "nationality"
            columns = {
                "name": first_index(values, lambda x: "旅館名稱" in x),
                "fit": first_index(values, lambda x: "FIT類別" in x or "個別旅客" in x),
                "group": first_index(values, lambda x: "GROUP類別" in x or "團體旅客" in x),
                "total_guests": first_index(values, lambda x: "類別合計" in x or "總住客人次" in x),
                "domestic": first_index(values, lambda x: "本國" in x),
                "japan": first_index(values, lambda x: "日本" in x),
                "korea": first_index(values, lambda x: "南韓" in x),
                "hk_mo": first_index(values, lambda x: "港澳" in x),
                "usa": first_index(values, lambda x: "美國" in x),
            }
            continue

        if mode not in {"operations", "nationality"}:
            continue

        name = clean_name(row.iloc[columns.get("name")]) if columns.get("name") is not None else ""
        if not name or is_total_name(name) or name in CITIES:
            continue

        if mode == "operations":
            occupancy = number(row, columns.get("occupancy"))
            if pd.isna(occupancy):
                continue
            if occupancy <= 1:
                occupancy *= 100
            rooms = number(row, columns.get("rooms"))
            if columns.get("rooms_are_room_nights") and pd.notna(rooms):
                rooms /= calendar.monthrange(year, month)[1]
            operations[name] = {
                "year": year,
                "month": month,
                "city": current_city,
                "hotel_name": name,
                "total_rooms": rooms,
                "rooms_used": number(row, columns.get("used")),
                "occupancy_rate": occupancy,
                "avg_price": number(row, columns.get("price")),
                "room_revenue": number(row, columns.get("room_revenue")),
                "food_revenue": number(row, columns.get("food_revenue")),
                "total_revenue": number(row, columns.get("total_revenue")),
                "employees": number(row, columns.get("employees")),
            }
        else:
            total_guests = number(row, columns.get("total_guests"))
            if pd.isna(total_guests):
                continue
            nationality[name] = {
                "individual_guests": number(row, columns.get("fit")),
                "group_guests": number(row, columns.get("group")),
                "total_guests": total_guests,
                "domestic_guests": number(row, columns.get("domestic")),
                "japan_guests": number(row, columns.get("japan")),
                "korea_guests": number(row, columns.get("korea")),
                "hk_mo_guests": number(row, columns.get("hk_mo")),
                "usa_guests": number(row, columns.get("usa")),
            }

    records = []
    for name, record in operations.items():
        record.update(nationality.get(name, {}))
        total_guests = record.get("total_guests", np.nan)
        if pd.notna(total_guests) and total_guests > 0:
            record["domestic_ratio"] = np.clip(
                record.get("domestic_guests", np.nan) / total_guests, 0, 1
            )
            record["international_ratio"] = 1 - record["domestic_ratio"]
            record["individual_ratio"] = np.clip(
                record.get("individual_guests", np.nan) / total_guests, 0, 1
            )
        else:
            record["domestic_ratio"] = np.nan
            record["international_ratio"] = np.nan
            record["individual_ratio"] = np.nan

        if pd.notna(record.get("avg_price")) and pd.notna(record.get("occupancy_rate")):
            record["revpar"] = record["avg_price"] * record["occupancy_rate"] / 100

        star_rank = STAR_DATABASE.get(name, np.nan)
        if pd.isna(star_rank):
            for known_name, rank in STAR_DATABASE.items():
                if known_name in name or name in known_name:
                    star_rank = rank
                    break
        record["star_rank"] = star_rank
        record["star_rating"] = STAR_LABELS.get(star_rank, "無星等/未評鑑" if pd.isna(star_rank) else "其他")
        record["has_star"] = int(pd.notna(star_rank))
        records.append(record)

    return records


def build_dataset():
    files = sorted(
        path
        for path in MONTHLY_DIR.glob("*.xlsx")
        if re.fullmatch(r"20\d{2}(?:0[1-9]|1[0-2])", path.stem)
        and int(path.stem[:4]) >= 2023
    )
    if not files:
        raise FileNotFoundError("找不到 2023 年起的單月月報 XLSX")

    latest = files[-1].stem
    latest_year, latest_month = int(latest[:4]), int(latest[4:])
    expected = {
        f"{year}{month:02d}"
        for year in range(2023, latest_year + 1)
        for month in range(1, 13)
        if year < latest_year or month <= latest_month
    }
    actual = {p.stem for p in files}
    missing = sorted(expected - actual)
    if missing:
        raise FileNotFoundError(f"缺少月報檔案：{', '.join(missing)}")

    records = []
    for path in files:
        parsed = parse_file(path)
        records.extend(parsed)
        print(f"[{path.stem}] 解析 {len(parsed)} 間旅館")

    result = pd.DataFrame(records)
    # 2026-03 起的新版單月表不再於旅館明細重複列出縣市，
    # 用同一旅館先前已知的官方縣市補回，避免整批落入「未知」。
    known_city = (
        result[result["city"].ne("未知")]
        .drop_duplicates("hotel_name", keep="last")
        .set_index("hotel_name")["city"]
    )
    unknown = result["city"].eq("未知")
    result.loc[unknown, "city"] = result.loc[unknown, "hotel_name"].map(known_city).fillna("未知")
    result.loc[result["hotel_name"].isin(CITY_OVERRIDES), "city"] = result.loc[
        result["hotel_name"].isin(CITY_OVERRIDES), "hotel_name"
    ].map(CITY_OVERRIDES)
    result = result.sort_values(["year", "month", "city", "hotel_name"]).reset_index(drop=True)
    result.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"\n完成：{len(result)} 筆，{result['hotel_name'].nunique()} 家旅館")
    print(f"資料期間：{result['year'].min()}–{result['year'].max()}，共 {result[['year', 'month']].drop_duplicates().shape[0]} 個月份")
    print(f"輸出：{OUTPUT}")
    return result


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build_dataset()
