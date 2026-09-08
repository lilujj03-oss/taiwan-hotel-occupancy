"""由行政院人事行政總處官方辦公日曆建立日／月曆特徵。"""

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "calendar"
PROCESSED_DIR = ROOT / "data" / "processed"
DAILY_OUTPUT = PROCESSED_DIR / "taiwan_official_daily_calendar.csv"
MONTHLY_OUTPUT = PROCESSED_DIR / "taiwan_monthly_calendar_features.csv"
MANIFEST_OUTPUT = ROOT / "reports" / "calendar_data_manifest.json"

SOURCE_PAGE = "https://data.gov.tw/dataset/14718"
SOURCE_FILES = {
    2023: "official_work_calendar_2023.csv",
    2024: "official_work_calendar_2024.csv",
    2025: "official_work_calendar_2025.csv",
    2026: "official_work_calendar_2026.csv",
    2027: "official_work_calendar_2027.csv",
}


def read_official_csv(path):
    """官方歷年檔案有 UTF-8 BOM 與 Big5，依序嘗試解碼。"""
    last_error = None
    for encoding in ("utf-8-sig", "big5", "cp950"):
        try:
            return pd.read_csv(path, encoding=encoding), encoding
        except UnicodeDecodeError as error:
            last_error = error
    raise last_error


def add_break_features(daily):
    result = daily.sort_values("date").copy()
    run_boundary = result["is_day_off"].ne(result["is_day_off"].shift())
    result["off_run_id"] = run_boundary.cumsum()
    off_run_length = (
        result[result["is_day_off"].eq(1)]
        .groupby("off_run_id")["date"]
        .transform("size")
    )
    result["off_run_length"] = 0
    result.loc[result["is_day_off"].eq(1), "off_run_length"] = off_run_length
    result["is_long_break_day"] = result["off_run_length"].ge(3).astype(int)
    return result


def build_monthly(daily):
    grouped = daily.groupby(["year", "month"], as_index=False)
    monthly = grouped.agg(
        days_in_month=("date", "size"),
        weekend_days=("is_weekend", "sum"),
        day_off_days=("is_day_off", "sum"),
        weekday_day_off_days=("is_weekday_day_off", "sum"),
        makeup_workdays=("is_makeup_workday", "sum"),
        long_break_day_count=("is_long_break_day", "sum"),
        longest_break_days=("off_run_length", "max"),
        spring_festival_days=("is_spring_festival_day", "sum"),
    )
    long_runs = (
        daily[daily["is_long_break_day"].eq(1)]
        .groupby(["year", "month"])["off_run_id"]
        .nunique()
        .rename("long_weekend_count")
        .reset_index()
    )
    monthly = monthly.merge(long_runs, on=["year", "month"], how="left")
    monthly["long_weekend_count"] = monthly["long_weekend_count"].fillna(0).astype(int)
    monthly["day_off_ratio"] = monthly["day_off_days"] / monthly["days_in_month"]
    monthly["has_spring_festival"] = monthly["spring_festival_days"].gt(0).astype(int)
    monthly["is_summer_month"] = monthly["month"].isin([7, 8]).astype(int)
    monthly["is_year_end_month"] = monthly["month"].isin([12, 1]).astype(int)
    return monthly.sort_values(["year", "month"])


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frames = []
    manifest_files = []
    for year, filename in SOURCE_FILES.items():
        path = RAW_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"缺少官方日曆檔：{path}")
        frame, source_encoding = read_official_csv(path)
        required = {"西元日期", "星期", "是否放假", "備註"}
        if not required.issubset(frame.columns):
            raise ValueError(f"{filename} 欄位不符：{list(frame.columns)}")
        frame = frame.rename(
            columns={
                "西元日期": "date",
                "星期": "official_weekday",
                "是否放假": "official_day_status",
                "備註": "holiday_note",
            }
        )
        frame["date"] = pd.to_datetime(frame["date"].astype(str), format="%Y%m%d")
        if set(frame["date"].dt.year.unique()) != {year}:
            raise ValueError(f"{filename} 含非 {year} 年日期")
        expected_days = 366 if pd.Timestamp(year, 12, 31).dayofyear == 366 else 365
        if len(frame) != expected_days or frame["date"].nunique() != expected_days:
            raise ValueError(f"{filename} 日期不完整：{len(frame)} 筆")
        frames.append(frame)
        manifest_files.append(
            {
                "year": year,
                "file": str(path.relative_to(ROOT)),
                "rows": int(len(frame)),
                "source_encoding": source_encoding,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    daily = pd.concat(frames, ignore_index=True).sort_values("date")
    daily["holiday_note"] = daily["holiday_note"].fillna("")
    daily["year"] = daily["date"].dt.year
    daily["month"] = daily["date"].dt.month
    daily["day"] = daily["date"].dt.day
    daily["weekday"] = daily["date"].dt.weekday
    daily["is_weekend"] = daily["weekday"].ge(5).astype(int)
    daily["is_day_off"] = daily["official_day_status"].eq(2).astype(int)
    daily["is_weekday_day_off"] = (
        daily["weekday"].lt(5) & daily["official_day_status"].eq(2)
    ).astype(int)
    daily["is_makeup_workday"] = (
        daily["weekday"].ge(5) & daily["official_day_status"].eq(0)
    ).astype(int)
    daily["is_spring_festival_day"] = daily["holiday_note"].str.contains(
        "小年夜|除夕|春節", regex=True
    ).astype(int)
    daily = add_break_features(daily)
    monthly = build_monthly(daily)

    daily.to_csv(DAILY_OUTPUT, index=False, encoding="utf-8-sig")
    monthly.to_csv(MONTHLY_OUTPUT, index=False, encoding="utf-8-sig")
    manifest = {
        "provider": "行政院人事行政總處",
        "dataset": "中華民國政府行政機關辦公日曆表",
        "source_page": SOURCE_PAGE,
        "official_status_definition": {"0": "上班", "2": "放假"},
        "downloaded_files": manifest_files,
        "daily_output": str(DAILY_OUTPUT.relative_to(ROOT)),
        "monthly_output": str(MONTHLY_OUTPUT.relative_to(ROOT)),
        "date_start": daily["date"].min().strftime("%Y-%m-%d"),
        "date_end": daily["date"].max().strftime("%Y-%m-%d"),
    }
    with MANIFEST_OUTPUT.open("w", encoding="utf-8-sig") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)

    print(monthly.to_string(index=False))
    print(f"每日特徵：{DAILY_OUTPUT}")
    print(f"月度特徵：{MONTHLY_OUTPUT}")


if __name__ == "__main__":
    main()
