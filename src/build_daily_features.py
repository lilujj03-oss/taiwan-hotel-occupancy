"""Build daily demand indicators without pretending they are occupancy.

Inputs (all optional):
  data/raw/daily/daily_hotel_signals.csv
  data/raw/daily/taiwan_holidays.csv
  data/raw/daily/events.csv

The output keeps one row per hotel/date from the available monthly history.
Actual daily occupancy is intentionally nullable and is only used by
train_daily.py after a PMS/official daily export is supplied.
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MONTHLY = ROOT / "data" / "processed" / "hotel_monthly.csv"
DAILY_DIR = ROOT / "data" / "raw" / "daily"
OUTPUT = ROOT / "data" / "processed" / "hotel_daily_features.csv"


def _read_csv(path, columns):
    if not path.exists():
        return pd.DataFrame(columns=columns)
    df = pd.read_csv(path)
    for col in columns:
        if col not in df.columns:
            df[col] = np.nan
    return df


def build():
    monthly = pd.read_csv(MONTHLY)
    monthly["hotel_name"] = monthly["hotel_name"].astype(str).str.split("\\n").str[0].str.strip("*# ")
    monthly["date"] = pd.to_datetime(dict(year=monthly["year"], month=monthly["month"], day=1))

    dates = pd.date_range(monthly["date"].min(), monthly["date"].max() + pd.offsets.MonthEnd(1), freq="D")
    hotels = monthly[["hotel_name", "city", "star_rating", "star_rank"]].drop_duplicates("hotel_name")
    calendar = hotels.assign(key=1).merge(pd.DataFrame({"date": dates, "key": 1}), on="key").drop(columns="key")
    calendar["weekday"] = calendar["date"].dt.dayofweek
    calendar["is_weekend"] = calendar["weekday"].isin([5, 6]).astype(int)
    calendar["year"] = calendar["date"].dt.year
    calendar["month"] = calendar["date"].dt.month

    holidays = _read_csv(DAILY_DIR / "taiwan_holidays.csv", ["date", "holiday_name", "is_holiday"])
    holidays["date"] = pd.to_datetime(holidays["date"], errors="coerce")
    holidays["is_holiday"] = pd.to_numeric(holidays["is_holiday"], errors="coerce").fillna(0).astype(int)
    calendar = calendar.merge(holidays[["date", "holiday_name", "is_holiday"]], on="date", how="left")
    calendar["holiday_name"] = calendar["holiday_name"].fillna("")
    calendar["is_holiday"] = calendar["is_holiday"].fillna(0).astype(int)

    events = _read_csv(DAILY_DIR / "events.csv", ["date", "event_name", "event_level"])
    events["date"] = pd.to_datetime(events["date"], errors="coerce")
    events["event_level"] = pd.to_numeric(events["event_level"], errors="coerce").fillna(0)
    events = events.groupby("date", as_index=False).agg(
        event_name=("event_name", lambda s: "、".join(str(x) for x in s.dropna() if str(x).strip())),
        event_level=("event_level", "max"),
    )
    calendar = calendar.merge(events, on="date", how="left")
    calendar["event_name"] = calendar["event_name"].fillna("")
    calendar["event_level"] = calendar["event_level"].fillna(0)

    signals = _read_csv(DAILY_DIR / "daily_hotel_signals.csv", [
        "hotel_name", "date", "avg_price", "availability_status", "rooms_available",
        "source", "captured_at", "occupancy_rate",
    ])
    signals["hotel_name"] = signals["hotel_name"].astype(str).str.split("\\n").str[0].str.strip("*# ")
    signals["date"] = pd.to_datetime(signals["date"], errors="coerce")
    signals = signals.dropna(subset=["hotel_name", "date"]).drop_duplicates(["hotel_name", "date"], keep="last")
    result = calendar.merge(signals, on=["hotel_name", "date"], how="left")
    result["availability_status"] = result["availability_status"].fillna("unknown").str.lower()
    status_score = {"sold_out": 1.0, "limited": 0.7, "available": 0.2, "unknown": np.nan}
    result["availability_pressure"] = result["availability_status"].map(status_score)
    result["avg_price"] = pd.to_numeric(result["avg_price"], errors="coerce")
    result["price_log"] = np.log1p(result["avg_price"].clip(lower=0))
    result["has_daily_signal"] = result["avg_price"].notna() | result["availability_status"].ne("unknown")
    result["data_quality"] = np.select(
        [result["occupancy_rate"].notna(), result["has_daily_signal"]],
        ["actual_daily_occupancy", "demand_signal_only"], default="calendar_only"
    )
    result.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"輸出：{OUTPUT}")
    print(f"旅館：{result.hotel_name.nunique()}，日期：{result.date.nunique()}，列數：{len(result)}")
    print(result["data_quality"].value_counts().to_string())


if __name__ == "__main__":
    build()
