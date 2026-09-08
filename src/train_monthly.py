"""使用逐月資料建立月度住房率預測模型。"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "data" / "processed" / "hotel_monthly.csv"
FEATURE_OUTPUT = ROOT / "data" / "processed" / "hotel_monthly_features.csv"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"
TARGET = "target_occupancy"
BACKTEST_OUTPUT = REPORT_DIR / "monthly_backtest_predictions.csv"
MODEL_START = pd.Timestamp("2023-01-01")
MODEL_END = pd.Timestamp("2025-12-01")


def add_month_features(df):
    df = df.copy()
    df["date"] = pd.to_datetime(dict(year=df.year, month=df.month, day=1))
    keys = ["hotel_name", "date"]
    occ = df.set_index(keys)[["occupancy_rate"]].rename(columns={"occupancy_rate": "occ_value"})

    for months in (1, 2, 3, 12):
        lookup = occ.copy()
        lookup.index = pd.MultiIndex.from_arrays(
            [lookup.index.get_level_values(0), lookup.index.get_level_values(1) + pd.DateOffset(months=months)],
            names=keys,
        )
        df = df.merge(lookup.rename(columns={"occ_value": f"occupancy_lag_{months}"}), on=keys, how="left")

    # 每一列預測該列月份，lag_1 才會正確代表「前一個月」。
    # 未來月份由預測函式使用已知歷史值（必要時遞迴）建立相同特徵。
    df[TARGET] = df["occupancy_rate"]
    df["occupancy_roll3"] = df[["occupancy_lag_1", "occupancy_lag_2", "occupancy_lag_3"]].mean(axis=1)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    return df


def build_model(numeric, categorical, estimator, scale=False):
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale:
        numeric_steps.append(("scaler", StandardScaler()))
    preprocessor = ColumnTransformer([
        ("num", Pipeline(numeric_steps), numeric),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
    ])
    return Pipeline([("preprocessor", preprocessor), ("model", estimator)])


def train():
    MODEL_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    df = pd.read_csv(INPUT)
    df = add_month_features(df)
    source_data_end = df["date"].max()
    model_df = df[df["date"].between(MODEL_START, MODEL_END)].copy()
    model_df.to_csv(FEATURE_OUTPUT, index=False, encoding="utf-8-sig")

    numeric = [
        "month", "month_sin", "month_cos", "total_rooms", "employees", "avg_price",
        "domestic_ratio", "international_ratio", "individual_ratio",
        "occupancy_lag_1", "occupancy_lag_2", "occupancy_lag_3", "occupancy_lag_12", "occupancy_roll3",
    ]
    categorical = ["city", "star_rating"]
    valid_df = model_df[model_df[TARGET].notna()].copy()
    periods = sorted(valid_df["date"].drop_duplicates())
    if len(periods) < 24:
        raise RuntimeError("月度資料少於 24 個月份，無法建立 12 個月時間外測試集")
    test_start = periods[-12]
    train_df = valid_df[valid_df["date"] < test_start].copy()
    test_df = valid_df[valid_df["date"] >= test_start].copy()
    X_train, y_train = train_df[numeric + categorical], train_df[TARGET]
    X_test, y_test = test_df[numeric + categorical], test_df[TARGET]

    models = {
        "Ridge": build_model(numeric, categorical, Ridge(alpha=10.0), scale=True),
        "Random Forest": build_model(numeric, categorical, RandomForestRegressor(n_estimators=300, max_depth=8, random_state=42, n_jobs=-1)),
        "Gradient Boosting": build_model(numeric, categorical, GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.04, random_state=42)),
    }
    results = {}
    test_predictions = {}
    baseline = test_df["occupancy_lag_1"]
    valid = baseline.notna()
    results["Baseline (前月住房率)"] = {
        "mae": round(mean_absolute_error(y_test[valid], baseline[valid]), 2),
        "rmse": round(mean_squared_error(y_test[valid], baseline[valid]) ** 0.5, 2),
        "r2": round(r2_score(y_test[valid], baseline[valid]), 4),
        "n": int(valid.sum()),
    }

    for name, model in models.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        test_predictions[name] = np.clip(pred, 0, 100)
        results[name] = {
            "mae": round(mean_absolute_error(y_test, pred), 2),
            "rmse": round(mean_squared_error(y_test, pred) ** 0.5, 2),
            "r2": round(r2_score(y_test, pred), 4),
            "n": int(len(y_test)),
        }
        # 評估完成後，只用指定期間 2023-01～2025-12 重訓正式模型。
        model.fit(valid_df[numeric + categorical], valid_df[TARGET])
        joblib.dump(model, MODEL_DIR / f"monthly_{name.lower().replace(' ', '_')}.pkl")

    selected_model = min(models, key=lambda name: results[name]["mae"])
    production_model = models[selected_model]
    joblib.dump(production_model, MODEL_DIR / "monthly_model.pkl")

    backtest = test_df[["date", "year", "month", "city", "hotel_name", TARGET]].copy()
    backtest = backtest.rename(columns={TARGET: "actual_occupancy"})
    backtest["predicted_occupancy"] = test_predictions[selected_model]
    backtest["error"] = backtest["predicted_occupancy"] - backtest["actual_occupancy"]
    backtest["absolute_error"] = backtest["error"].abs()
    backtest.to_csv(BACKTEST_OUTPUT, index=False, encoding="utf-8-sig")

    feature_names = production_model.named_steps["preprocessor"].get_feature_names_out()
    importance = production_model.named_steps["model"].feature_importances_
    pd.DataFrame({"feature": feature_names, "importance": importance}).sort_values(
        "importance", ascending=False
    ).to_csv(REPORT_DIR / "feature_importance_monthly.csv", index=False, encoding="utf-8-sig")

    with open(REPORT_DIR / "model_results_monthly.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    metadata = {
        "data_start": valid_df["date"].min().strftime("%Y-%m"),
        "data_end": valid_df["date"].max().strftime("%Y-%m"),
        "source_data_end": pd.Timestamp(source_data_end).strftime("%Y-%m"),
        "holdout_start": pd.Timestamp(test_start).strftime("%Y-%m"),
        "holdout_end": valid_df["date"].max().strftime("%Y-%m"),
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "production_rows": int(len(valid_df)),
        "hotel_count": int(valid_df["hotel_name"].nunique()),
        "selected_model": selected_model,
    }
    with open(REPORT_DIR / "monthly_model_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"月度特徵輸出：{FEATURE_OUTPUT}")
    print(
        f"評估訓練筆數：{len(train_df)}，"
        f"時間外測試 {metadata['holdout_start']}–{metadata['holdout_end']}：{len(test_df)} 筆"
    )
    print(f"正式模型重訓筆數：{len(valid_df)}，資料截止：{metadata['data_end']}")
    print(f"正式採用模型：{selected_model}")
    print(f"月度時間外回測明細：{BACKTEST_OUTPUT}")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    train()
