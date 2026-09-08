"""建立截至 2026-06 的正式月度模型，並保留 2026 上半年外部時間驗證。"""

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
FEATURE_OUTPUT = ROOT / "data" / "processed" / "hotel_monthly_features_current.csv"
MODEL_OUTPUT = ROOT / "models" / "monthly_model_through_202606.pkl"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"
RESULTS_OUTPUT = REPORT_DIR / "model_results_monthly_current.json"
METADATA_OUTPUT = REPORT_DIR / "monthly_model_current_metadata.json"
IMPORTANCE_OUTPUT = REPORT_DIR / "feature_importance_monthly_current.csv"
ROLLING_OUTPUT = REPORT_DIR / "monthly_2026h1_rolling_backtest.csv"
FIXED_OUTPUT = REPORT_DIR / "monthly_2026h1_fixed_backtest.csv"
VALIDATION_OUTPUT = REPORT_DIR / "monthly_2026h1_validation.json"

TRAIN_START = pd.Timestamp("2023-01-01")
EVALUATION_TRAIN_END = pd.Timestamp("2025-12-01")
EVALUATION_START = pd.Timestamp("2026-01-01")
EVALUATION_END = pd.Timestamp("2026-06-01")
PRODUCTION_END = pd.Timestamp("2026-06-01")

LAGGED_INPUTS = [
    "total_rooms",
    "employees",
    "avg_price",
    "domestic_ratio",
    "international_ratio",
    "individual_ratio",
]
NUMERIC = [
    "month",
    "month_sin",
    "month_cos",
    *[f"input_{column}" for column in LAGGED_INPUTS],
    "occupancy_lag_1",
    "occupancy_lag_2",
    "occupancy_lag_3",
    "occupancy_lag_12",
    "occupancy_roll3",
]
CATEGORICAL = ["city", "star_rating"]
FEATURES = NUMERIC + CATEGORICAL


def add_calendar_lag(source, target, source_column, output_column, months):
    lookup = source[["hotel_name", "date", source_column]].copy()
    lookup["date"] = lookup["date"] + pd.DateOffset(months=months)
    return target.merge(
        lookup.rename(columns={source_column: output_column}),
        on=["hotel_name", "date"],
        how="left",
    )


def build_features(raw):
    data = raw.copy()
    data["date"] = pd.to_datetime(dict(year=data.year, month=data.month, day=1))
    data = data.sort_values(["hotel_name", "date"]).drop_duplicates(
        ["hotel_name", "date"], keep="last"
    )
    result = data.copy()
    for months in (1, 2, 3, 12):
        result = add_calendar_lag(
            data, result, "occupancy_rate", f"occupancy_lag_{months}", months
        )
    for column in LAGGED_INPUTS:
        result = add_calendar_lag(data, result, column, f"input_{column}", 1)
    result["occupancy_roll3"] = result[
        ["occupancy_lag_1", "occupancy_lag_2", "occupancy_lag_3"]
    ].mean(axis=1)
    result["month_sin"] = np.sin(2 * np.pi * result["month"] / 12)
    result["month_cos"] = np.cos(2 * np.pi * result["month"] / 12)
    return result


def build_model(estimator, scale=False):
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale:
        numeric_steps.append(("scaler", StandardScaler()))
    preprocessor = ColumnTransformer(
        [
            ("num", Pipeline(numeric_steps), NUMERIC),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ]
    )
    return Pipeline([("preprocessor", preprocessor), ("model", estimator)])


def candidate_models():
    return {
        "Ridge": build_model(Ridge(alpha=10.0), scale=True),
        "Random Forest": build_model(
            RandomForestRegressor(
                n_estimators=300, max_depth=8, random_state=42, n_jobs=-1
            )
        ),
        "Gradient Boosting": build_model(
            GradientBoostingRegressor(
                n_estimators=200, max_depth=3, learning_rate=0.04, random_state=42
            )
        ),
    }


def metrics(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    valid = np.isfinite(actual) & np.isfinite(predicted)
    actual = actual[valid]
    predicted = predicted[valid]
    return {
        "mae": round(mean_absolute_error(actual, predicted), 2),
        "rmse": round(mean_squared_error(actual, predicted) ** 0.5, 2),
        "r2": round(r2_score(actual, predicted), 4),
        "bias": round(float(np.mean(predicted - actual)), 2),
        "n": int(len(actual)),
    }


def recursive_fixed_origin(model, raw):
    history = raw[raw["date"] <= EVALUATION_TRAIN_END].copy()
    latest = history.sort_values("date").groupby("hotel_name", as_index=False).tail(1)
    latest = latest[latest["date"].eq(EVALUATION_TRAIN_END)].set_index("hotel_name")
    actual = raw[raw["date"].between(EVALUATION_START, EVALUATION_END)].set_index(
        ["hotel_name", "date"]
    )["occupancy_rate"]
    known = {
        (row.hotel_name, pd.Timestamp(row.date)): float(row.occupancy_rate)
        for row in history.itertuples()
        if pd.notna(row.occupancy_rate)
    }
    records = []
    dates = pd.date_range(EVALUATION_START, EVALUATION_END, freq="MS")
    for horizon, forecast_date in enumerate(dates, 1):
        rows = []
        hotel_names = []
        for hotel_name, latest_row in latest.iterrows():
            lags = [
                known.get((hotel_name, forecast_date - pd.DateOffset(months=months)), np.nan)
                for months in (1, 2, 3)
            ]
            rows.append(
                {
                    "month": forecast_date.month,
                    "month_sin": np.sin(2 * np.pi * forecast_date.month / 12),
                    "month_cos": np.cos(2 * np.pi * forecast_date.month / 12),
                    "input_total_rooms": latest_row["total_rooms"],
                    "input_employees": latest_row["employees"],
                    "input_avg_price": latest_row["avg_price"],
                    "input_domestic_ratio": latest_row["domestic_ratio"],
                    "input_international_ratio": latest_row["international_ratio"],
                    "input_individual_ratio": latest_row["individual_ratio"],
                    "occupancy_lag_1": lags[0],
                    "occupancy_lag_2": lags[1],
                    "occupancy_lag_3": lags[2],
                    "occupancy_lag_12": known.get(
                        (hotel_name, forecast_date - pd.DateOffset(months=12)), np.nan
                    ),
                    "occupancy_roll3": (
                        np.nanmean(lags) if any(pd.notna(value) for value in lags) else np.nan
                    ),
                    "city": latest_row["city"],
                    "star_rating": latest_row["star_rating"],
                }
            )
            hotel_names.append(hotel_name)
        predictions = np.clip(model.predict(pd.DataFrame(rows)[FEATURES]), 0, 100)
        for hotel_name, prediction in zip(hotel_names, predictions):
            known[(hotel_name, forecast_date)] = float(prediction)
            try:
                actual_value = actual.loc[(hotel_name, forecast_date)]
            except KeyError:
                continue
            records.append(
                {
                    "date": forecast_date,
                    "year": forecast_date.year,
                    "month": forecast_date.month,
                    "horizon": horizon,
                    "city": latest.loc[hotel_name, "city"],
                    "hotel_name": hotel_name,
                    "actual_occupancy": float(actual_value),
                    "predicted_occupancy": float(prediction),
                }
            )
    result = pd.DataFrame(records)
    result["error"] = result["predicted_occupancy"] - result["actual_occupancy"]
    result["absolute_error"] = result["error"].abs()
    return result


def train():
    MODEL_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    raw = pd.read_csv(INPUT)
    features = build_features(raw)
    features.to_csv(FEATURE_OUTPUT, index=False, encoding="utf-8-sig")

    evaluation_train = features[features["date"].between(TRAIN_START, EVALUATION_TRAIN_END)].copy()
    evaluation_test = features[features["date"].between(EVALUATION_START, EVALUATION_END)].copy()
    production = features[features["date"].between(TRAIN_START, PRODUCTION_END)].copy()

    models = candidate_models()
    results = {}
    predictions = {}
    valid_baseline = evaluation_test["occupancy_lag_1"].notna()
    results["Baseline (前月住房率)"] = metrics(
        evaluation_test.loc[valid_baseline, "occupancy_rate"],
        evaluation_test.loc[valid_baseline, "occupancy_lag_1"],
    )

    for name, model in models.items():
        model.fit(evaluation_train[FEATURES], evaluation_train["occupancy_rate"])
        prediction = np.clip(model.predict(evaluation_test[FEATURES]), 0, 100)
        predictions[name] = prediction
        results[name] = metrics(evaluation_test["occupancy_rate"], prediction)

    selected_name = min(models, key=lambda name: results[name]["mae"])
    selected_evaluation_model = models[selected_name]
    rolling = evaluation_test[
        ["date", "year", "month", "city", "hotel_name", "occupancy_rate"]
    ].copy()
    rolling = rolling.rename(columns={"occupancy_rate": "actual_occupancy"})
    rolling["predicted_occupancy"] = predictions[selected_name]
    rolling["error"] = rolling["predicted_occupancy"] - rolling["actual_occupancy"]
    rolling["absolute_error"] = rolling["error"].abs()
    rolling.to_csv(ROLLING_OUTPUT, index=False, encoding="utf-8-sig")

    raw_with_dates = raw.copy()
    raw_with_dates["date"] = pd.to_datetime(
        dict(year=raw_with_dates.year, month=raw_with_dates.month, day=1)
    )
    fixed = recursive_fixed_origin(selected_evaluation_model, raw_with_dates)
    fixed.to_csv(FIXED_OUTPUT, index=False, encoding="utf-8-sig")

    horizon_metrics = {}
    cumulative_rmse = 0.0
    for horizon, group in fixed.groupby("horizon"):
        horizon_result = metrics(group["actual_occupancy"], group["predicted_occupancy"])
        cumulative_rmse = max(cumulative_rmse, horizon_result["rmse"])
        horizon_result["planning_rmse"] = round(cumulative_rmse, 2)
        horizon_metrics[str(int(horizon))] = horizon_result
    validation = {
        "rolling_one_month": results[selected_name],
        "fixed_origin_overall": metrics(fixed["actual_occupancy"], fixed["predicted_occupancy"]),
        "fixed_origin_by_horizon": horizon_metrics,
    }
    with open(VALIDATION_OUTPUT, "w", encoding="utf-8") as file:
        json.dump(validation, file, ensure_ascii=False, indent=2)

    production_models = candidate_models()
    for name, model in production_models.items():
        model.fit(production[FEATURES], production["occupancy_rate"])
        joblib.dump(
            model,
            MODEL_DIR / f"monthly_current_{name.lower().replace(' ', '_')}.pkl",
        )
    production_model = production_models[selected_name]
    joblib.dump(production_model, MODEL_OUTPUT)

    feature_names = production_model.named_steps["preprocessor"].get_feature_names_out()
    estimator = production_model.named_steps["model"]
    if hasattr(estimator, "feature_importances_"):
        importance = estimator.feature_importances_
    else:
        importance = np.abs(estimator.coef_)
    pd.DataFrame({"feature": feature_names, "importance": importance}).sort_values(
        "importance", ascending=False
    ).to_csv(IMPORTANCE_OUTPUT, index=False, encoding="utf-8-sig")

    with open(RESULTS_OUTPUT, "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    metadata = {
        "data_start": TRAIN_START.strftime("%Y-%m"),
        "data_end": PRODUCTION_END.strftime("%Y-%m"),
        "source_data_end": features["date"].max().strftime("%Y-%m"),
        "evaluation_train_end": EVALUATION_TRAIN_END.strftime("%Y-%m"),
        "holdout_start": EVALUATION_START.strftime("%Y-%m"),
        "holdout_end": EVALUATION_END.strftime("%Y-%m"),
        "evaluation_train_rows": int(len(evaluation_train)),
        "test_rows": int(len(evaluation_test)),
        "production_rows": int(len(production)),
        "hotel_count": int(production["hotel_name"].nunique()),
        "selected_model": selected_name,
        "model_version": "monthly-through-202606-v2",
        "test_input_policy": "前月已知營運欄位，不使用預測當月實際 ADR 或旅客比例",
    }
    with open(METADATA_OUTPUT, "w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)

    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    print(f"正式採用模型：{selected_name}")
    print(f"正式模型：{MODEL_OUTPUT}")


if __name__ == "__main__":
    train()
