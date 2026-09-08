"""
train.py
模型訓練與評估：比較 Linear Regression、Ridge、Decision Tree、Random Forest、Gradient Boosting
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path

from sklearn.linear_model import LinearRegression, Ridge
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from features import get_feature_columns

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

TARGET = "occupancy_rate"
TRAIN_YEARS = [2023, 2024]
TEST_YEAR = 2025


def load_data() -> pd.DataFrame:
    path = PROCESSED_DIR / "hotel_features.csv"
    if not path.exists():
        raise FileNotFoundError(f"找不到特徵資料：{path}")
    return pd.read_csv(path)


def get_models() -> dict:
    return {
        "Linear Regression": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LinearRegression()),
        ]),
        "Ridge": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=1.0)),
        ]),
        "Decision Tree": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", DecisionTreeRegressor(max_depth=5, random_state=42)),
        ]),
        "Random Forest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42, n_jobs=-1)),
        ]),
        "Gradient Boosting": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", GradientBoostingRegressor(n_estimators=150, max_depth=4, learning_rate=0.05, random_state=42)),
        ]),
    }


def train_and_evaluate():
    print("=== 開始模型訓練與評估 ===")
    df = load_data()
    feature_cols = [c for c in get_feature_columns() if c in df.columns]

    train_df = df[df["year"].isin(TRAIN_YEARS)].dropna(subset=[TARGET])
    test_df = df[df["year"] == TEST_YEAR].dropna(subset=[TARGET])

    X_train = train_df[feature_cols]
    y_train = train_df[TARGET]
    X_test = test_df[feature_cols]
    y_test = test_df[TARGET]

    print(f"訓練集（2023–2024）：{len(train_df)} 筆，平均住房率：{y_train.mean():.1f}%")
    print(f"測試集（2025）：{len(test_df)} 筆，平均住房率：{y_test.mean():.1f}%")

    # Baseline 基準模型（歷史各縣市平均）
    city_mean = train_df.groupby("city")[TARGET].mean()
    y_baseline = test_df["city"].map(city_mean).fillna(y_train.mean())

    results = {}
    results["Baseline (縣市平均)"] = {
        "mae": round(mean_absolute_error(y_test, y_baseline), 2),
        "rmse": round(mean_squared_error(y_test, y_baseline) ** 0.5, 2),
        "r2": round(r2_score(y_test, y_baseline), 4),
    }

    models = get_models()
    for name, pipeline in models.items():
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        mae = mean_absolute_error(y_test, y_pred)
        rmse = mean_squared_error(y_test, y_pred) ** 0.5
        r2 = r2_score(y_test, y_pred)

        results[name] = {"mae": round(mae, 2), "rmse": round(rmse, 2), "r2": round(r2, 4)}

        # 儲存模型
        model_file = name.lower().replace(" ", "_") + ".pkl"
        joblib.dump(pipeline, MODELS_DIR / model_file)

    # 輸出比較結果
    results_df = pd.DataFrame(results).T.sort_values("mae")
    print("\n" + "=" * 50)
    print("模型評估排行榜（測試集 2025 年）：")
    print("=" * 50)
    print(results_df.to_string())

    # 儲存報告
    report_file = REPORTS_DIR / "model_results.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n評估報告已儲存：{report_file}")

    # 特徵重要性 (Random Forest)
    rf_pipeline = models["Random Forest"]
    rf_model = rf_pipeline.named_steps["model"]
    feat_imp = pd.DataFrame({
        "feature": feature_cols,
        "importance": rf_model.feature_importances_
    }).sort_values("importance", ascending=False)

    feat_imp_file = REPORTS_DIR / "feature_importance.csv"
    feat_imp.to_csv(feat_imp_file, index=False, encoding="utf-8-sig")
    print(f"特徵重要性已儲存：{feat_imp_file}")
    print("\nTop 10 重要特徵：")
    for _, row in feat_imp.head(10).iterrows():
        print(f"  {row['feature']:<22}: {row['importance']:.4f}")

    return results_df


if __name__ == "__main__":
    train_and_evaluate()
