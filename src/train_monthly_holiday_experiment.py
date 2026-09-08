"""比較現行月度模型與官方假日特徵模型，改善時才輸出候選正式模型。"""

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

from train_monthly_current import (
    CATEGORICAL,
    EVALUATION_END,
    EVALUATION_START,
    EVALUATION_TRAIN_END,
    INPUT,
    LAGGED_INPUTS,
    NUMERIC as BASE_NUMERIC,
    PRODUCTION_END,
    TRAIN_START,
    build_features,
)


ROOT = Path(__file__).resolve().parent.parent
CALENDAR_INPUT = ROOT / "data" / "processed" / "taiwan_monthly_calendar_features.csv"
MODEL_DIR = ROOT / "models" / "experiments"
REPORT_DIR = ROOT / "reports"
RESULTS_OUTPUT = REPORT_DIR / "monthly_holiday_experiment_results.json"
PREDICTIONS_OUTPUT = REPORT_DIR / "monthly_holiday_2026h1_predictions.csv"
IMPORTANCE_OUTPUT = REPORT_DIR / "feature_importance_monthly_holiday_experiment.csv"
MODEL_OUTPUT = MODEL_DIR / "monthly_holiday_through_202606.pkl"

CALENDAR_NUMERIC = [
    "days_in_month",
    "weekend_days",
    "day_off_days",
    "weekday_day_off_days",
    "makeup_workdays",
    "long_weekend_count",
    "long_break_day_count",
    "longest_break_days",
    "day_off_ratio",
    "spring_festival_days",
    "has_spring_festival",
    "is_summer_month",
    "is_year_end_month",
]
HOLIDAY_NUMERIC = BASE_NUMERIC + CALENDAR_NUMERIC
BASE_FEATURES = BASE_NUMERIC + CATEGORICAL
HOLIDAY_FEATURES = HOLIDAY_NUMERIC + CATEGORICAL


def metric_values(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    valid = np.isfinite(actual) & np.isfinite(predicted)
    actual = actual[valid]
    predicted = predicted[valid]
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(mean_squared_error(actual, predicted) ** 0.5),
        "r2": float(r2_score(actual, predicted)),
        "bias": float(np.mean(predicted - actual)),
        "n": int(len(actual)),
    }


def rounded(values):
    return {
        key: round(value, 4 if key == "r2" else 2) if key != "n" else value
        for key, value in values.items()
    }


def build_model(estimator, numeric, scale=False):
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale:
        numeric_steps.append(("scaler", StandardScaler()))
    preprocessor = ColumnTransformer(
        [
            ("num", Pipeline(numeric_steps), numeric),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ]
    )
    return Pipeline([("preprocessor", preprocessor), ("model", estimator)])


def candidate_models(numeric):
    return {
        "Ridge": build_model(Ridge(alpha=10.0), numeric, scale=True),
        "Random Forest": build_model(
            RandomForestRegressor(
                n_estimators=300, max_depth=8, random_state=42, n_jobs=-1
            ),
            numeric,
        ),
        "Gradient Boosting": build_model(
            GradientBoostingRegressor(
                n_estimators=200, max_depth=3, learning_rate=0.04, random_state=42
            ),
            numeric,
        ),
    }


def evaluate_candidates(train, test, numeric, features):
    models = candidate_models(numeric)
    results = {}
    predictions = {}
    for name, model in models.items():
        model.fit(train[features], train["occupancy_rate"])
        prediction = np.clip(model.predict(test[features]), 0, 100)
        predictions[name] = prediction
        results[name] = metric_values(test["occupancy_rate"], prediction)
    selected = min(results, key=lambda name: results[name]["mae"])
    return models, results, predictions, selected


def calendar_values(calendar_lookup, forecast_date):
    key = (forecast_date.year, forecast_date.month)
    if key not in calendar_lookup.index:
        raise ValueError(f"官方月曆特徵缺少 {forecast_date:%Y-%m}")
    row = calendar_lookup.loc[key]
    return {column: row[column] for column in CALENDAR_NUMERIC}


def recursive_fixed_origin(model, raw, features, calendar_lookup=None):
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
    for horizon, forecast_date in enumerate(
        pd.date_range(EVALUATION_START, EVALUATION_END, freq="MS"), 1
    ):
        rows = []
        hotel_names = []
        calendar_row = (
            calendar_values(calendar_lookup, forecast_date)
            if calendar_lookup is not None
            else {}
        )
        for hotel_name, latest_row in latest.iterrows():
            lags = [
                known.get((hotel_name, forecast_date - pd.DateOffset(months=months)), np.nan)
                for months in (1, 2, 3)
            ]
            row = {
                "month": forecast_date.month,
                "month_sin": np.sin(2 * np.pi * forecast_date.month / 12),
                "month_cos": np.cos(2 * np.pi * forecast_date.month / 12),
                **{
                    f"input_{column}": latest_row[column]
                    for column in LAGGED_INPUTS
                },
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
                **calendar_row,
            }
            rows.append(row)
            hotel_names.append(hotel_name)
        prediction = np.clip(model.predict(pd.DataFrame(rows)[features]), 0, 100)
        for hotel_name, predicted in zip(hotel_names, prediction):
            known[(hotel_name, forecast_date)] = float(predicted)
            actual_value = actual.get((hotel_name, forecast_date), np.nan)
            if pd.isna(actual_value):
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
                    "predicted_occupancy": float(predicted),
                }
            )
    return pd.DataFrame(records)


def monthly_metrics(frame, prediction_column):
    output = {}
    for month, group in frame.groupby("month"):
        output[str(int(month))] = rounded(
            metric_values(group["actual_occupancy"], group[prediction_column])
        )
    return output


def save_importance(model):
    feature_names = model.named_steps["preprocessor"].get_feature_names_out()
    estimator = model.named_steps["model"]
    importance = (
        estimator.feature_importances_
        if hasattr(estimator, "feature_importances_")
        else np.abs(estimator.coef_)
    )
    pd.DataFrame({"feature": feature_names, "importance": importance}).sort_values(
        "importance", ascending=False
    ).to_csv(IMPORTANCE_OUTPUT, index=False, encoding="utf-8-sig")


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(INPUT)
    featured = build_features(raw)
    calendar = pd.read_csv(CALENDAR_INPUT, encoding="utf-8-sig")
    featured = featured.merge(calendar, on=["year", "month"], how="left", validate="many_to_one")
    if featured[CALENDAR_NUMERIC].isna().any().any():
        missing = featured.loc[featured[CALENDAR_NUMERIC].isna().any(axis=1), ["year", "month"]]
        raise ValueError(f"月曆特徵無法配對：{missing.drop_duplicates().to_dict('records')}")

    train = featured[featured["date"].between(TRAIN_START, EVALUATION_TRAIN_END)].copy()
    test = featured[featured["date"].between(EVALUATION_START, EVALUATION_END)].copy()
    production = featured[featured["date"].between(TRAIN_START, PRODUCTION_END)].copy()

    base_models, base_results, base_predictions, base_selected = evaluate_candidates(
        train, test, BASE_NUMERIC, BASE_FEATURES
    )
    holiday_models, holiday_results, holiday_predictions, holiday_selected = evaluate_candidates(
        train, test, HOLIDAY_NUMERIC, HOLIDAY_FEATURES
    )

    calendar_lookup = calendar.set_index(["year", "month"])
    raw_with_dates = raw.copy()
    raw_with_dates["date"] = pd.to_datetime(
        dict(year=raw_with_dates.year, month=raw_with_dates.month, day=1)
    )
    fixed_base = recursive_fixed_origin(
        base_models[base_selected], raw_with_dates, BASE_FEATURES
    )
    fixed_holiday = recursive_fixed_origin(
        holiday_models[holiday_selected],
        raw_with_dates,
        HOLIDAY_FEATURES,
        calendar_lookup,
    )
    key_columns = ["date", "year", "month", "horizon", "city", "hotel_name", "actual_occupancy"]
    fixed = fixed_base[key_columns + ["predicted_occupancy"]].rename(
        columns={"predicted_occupancy": "base_prediction"}
    )
    fixed = fixed.merge(
        fixed_holiday[key_columns + ["predicted_occupancy"]].rename(
            columns={"predicted_occupancy": "holiday_prediction"}
        ),
        on=key_columns,
        how="inner",
        validate="one_to_one",
    )
    lag12 = featured[featured["date"].between(EVALUATION_START, EVALUATION_END)][
        ["hotel_name", "date", "occupancy_lag_12"]
    ]
    fixed = fixed.merge(lag12, on=["hotel_name", "date"], how="left", validate="one_to_one")
    fixed = fixed.rename(columns={"occupancy_lag_12": "seasonal_naive_prediction"})
    fixed["base_absolute_error"] = (fixed["base_prediction"] - fixed["actual_occupancy"]).abs()
    fixed["holiday_absolute_error"] = (
        fixed["holiday_prediction"] - fixed["actual_occupancy"]
    ).abs()
    fixed.to_csv(PREDICTIONS_OUTPUT, index=False, encoding="utf-8-sig")

    seasonal_metrics = metric_values(
        test["occupancy_rate"], test["occupancy_lag_12"]
    )
    previous_month_metrics = metric_values(
        test["occupancy_rate"], test["occupancy_lag_1"]
    )
    fixed_base_metrics = metric_values(fixed["actual_occupancy"], fixed["base_prediction"])
    fixed_holiday_metrics = metric_values(
        fixed["actual_occupancy"], fixed["holiday_prediction"]
    )
    fixed_seasonal_metrics = metric_values(
        fixed["actual_occupancy"], fixed["seasonal_naive_prediction"]
    )

    # 正式切換門檻：逐月滾動 MAE 改善，且真正固定起點的 MAE、RMSE 都改善。
    adopted = (
        holiday_results[holiday_selected]["mae"] < base_results[base_selected]["mae"]
        and fixed_holiday_metrics["mae"] < fixed_base_metrics["mae"]
        and fixed_holiday_metrics["rmse"] < fixed_base_metrics["rmse"]
    )

    experiment = {
        "evaluation_period": "2026-01~2026-06",
        "training_period": "2023-01~2025-12",
        "selection_metric": "MAE",
        "baselines": {
            "previous_month": rounded(previous_month_metrics),
            "seasonal_naive_previous_year_same_month": rounded(seasonal_metrics),
        },
        "rolling_one_month": {
            "base_selected_model": base_selected,
            "holiday_selected_model": holiday_selected,
            "base_candidates": {name: rounded(value) for name, value in base_results.items()},
            "holiday_candidates": {
                name: rounded(value) for name, value in holiday_results.items()
            },
        },
        "fixed_origin_2025_12": {
            "seasonal_naive": rounded(fixed_seasonal_metrics),
            "base_model": rounded(fixed_base_metrics),
            "holiday_model": rounded(fixed_holiday_metrics),
            "base_by_month": monthly_metrics(fixed, "base_prediction"),
            "holiday_by_month": monthly_metrics(fixed, "holiday_prediction"),
        },
        "calendar_features": CALENDAR_NUMERIC,
        "adoption_rule": "rolling MAE、fixed-origin MAE 與 fixed-origin RMSE 均須優於基礎模型",
        "adopt_holiday_model": adopted,
        "decision": (
            "假日模型通過門檻，可作為正式模型候選"
            if adopted
            else "假日模型未同時通過三項門檻，維持現行正式模型"
        ),
    }
    with RESULTS_OUTPUT.open("w", encoding="utf-8-sig") as file:
        json.dump(experiment, file, ensure_ascii=False, indent=2)

    production_models = candidate_models(HOLIDAY_NUMERIC)
    production_model = production_models[holiday_selected]
    production_model.fit(production[HOLIDAY_FEATURES], production["occupancy_rate"])
    joblib.dump(production_model, MODEL_OUTPUT)
    save_importance(production_model)

    print(json.dumps(experiment, ensure_ascii=False, indent=2))
    print(f"假日候選模型（不覆蓋正式模型）：{MODEL_OUTPUT}")


if __name__ == "__main__":
    main()
