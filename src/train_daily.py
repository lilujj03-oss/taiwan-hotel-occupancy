"""Train the daily model only when actual daily occupancy is supplied."""

from pathlib import Path
import json
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "data" / "processed" / "hotel_daily_features.csv"
REPORT = ROOT / "reports" / "daily_model_readiness.json"
MODEL = ROOT / "models" / "daily_gradient_boosting.pkl"


def train():
    df = pd.read_csv(INPUT)
    target = pd.to_numeric(df.get("occupancy_rate"), errors="coerce")
    ready = target.notna()
    report = {"status": "not_ready", "message": "尚未提供旅館端每日實際住房率，未訓練每日模型。", "rows_with_actual_daily_occupancy": int(ready.sum())}
    if ready.sum() < 180:
        REPORT.parent.mkdir(exist_ok=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    work = df.loc[ready].copy()
    work["target_next_occupancy"] = work.groupby("hotel_name")["occupancy_rate"].shift(-1)
    work = work.dropna(subset=["target_next_occupancy"])
    numeric = ["weekday", "is_weekend", "is_holiday", "event_level", "avg_price", "price_log", "availability_pressure", "rooms_available"]
    categorical = ["city", "star_rating", "availability_status"]
    X, y = work[numeric + categorical], work["target_next_occupancy"]
    prep = ColumnTransformer([
        ("num", SimpleImputer(strategy="median"), numeric),
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical),
    ])
    model = Pipeline([("preprocessor", prep), ("model", GradientBoostingRegressor(n_estimators=250, max_depth=3, learning_rate=0.04, random_state=42))])
    split = work["date"].str[:4].astype(int) < work["date"].str[:4].astype(int).max()
    model.fit(X[split], y[split])
    pred = model.predict(X[~split])
    report = {"status": "trained", "rows": int(len(work)), "mae": round(mean_absolute_error(y[~split], pred), 2), "rmse": round(mean_squared_error(y[~split], pred) ** 0.5, 2), "r2": round(r2_score(y[~split], pred), 4)}
    MODEL.parent.mkdir(exist_ok=True); REPORT.parent.mkdir(exist_ok=True)
    joblib.dump(model, MODEL)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    train()
