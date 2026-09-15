"""三段式時間切分版月度模型：訓練 2023-2024 / 驗證選模 2025 / 測試 2026 上半年。

跟 train_monthly_current.py 的差別：選模階段完全不碰測試集（2026H1），
先在 2025 驗證集上比較候選模型（含 GB 的小型超參數搜尋），選出最佳設定後，
用 2023-2025 全部資料重新訓練一次，才拿 2026H1 做「只算一次」的最終測試。
"""

import json
import time
from itertools import product
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "data" / "processed" / "hotel_monthly.csv"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"

RESULTS_OUTPUT = REPORT_DIR / "model_results_monthly_3way.json"
METADATA_OUTPUT = REPORT_DIR / "monthly_model_3way_metadata.json"
IMPORTANCE_OUTPUT = REPORT_DIR / "feature_importance_monthly_3way.csv"
PERMUTATION_OUTPUT = REPORT_DIR / "permutation_importance_monthly_3way.csv"
ROLLING_OUTPUT = REPORT_DIR / "monthly_2026h1_rolling_backtest_3way.csv"
FIXED_OUTPUT = REPORT_DIR / "monthly_2026h1_fixed_backtest_3way.csv"
VALIDATION_OUTPUT = REPORT_DIR / "monthly_2026h1_validation_3way.json"
MODEL_OUTPUT = MODEL_DIR / "monthly_model_3way.pkl"

TRAIN_START = pd.Timestamp("2023-01-01")
TRAIN_END = pd.Timestamp("2024-12-01")
VAL_START = pd.Timestamp("2025-01-01")
VAL_END = pd.Timestamp("2025-12-01")
REFIT_END = pd.Timestamp("2025-12-01")  # 選模後，重訓用的資料含訓練+驗證
TEST_START = pd.Timestamp("2026-01-01")
TEST_END = pd.Timestamp("2026-06-01")
PRODUCTION_END = pd.Timestamp("2026-06-01")

LAGGED_INPUTS = [
    "total_rooms", "employees", "avg_price",
    "domestic_ratio", "international_ratio", "individual_ratio",
]
NUMERIC = [
    "month", "month_sin", "month_cos",
    *[f"input_{c}" for c in LAGGED_INPUTS],
    "occupancy_lag_1", "occupancy_lag_2", "occupancy_lag_3", "occupancy_lag_12",
    "occupancy_roll3",
]
CATEGORICAL = ["city", "star_rating"]
FEATURES = NUMERIC + CATEGORICAL


def add_calendar_lag(source, target, source_column, output_column, months):
    lookup = source[["hotel_name", "date", source_column]].copy()
    lookup["date"] = lookup["date"] + pd.DateOffset(months=months)
    return target.merge(
        lookup.rename(columns={source_column: output_column}),
        on=["hotel_name", "date"], how="left",
    )


def build_features(raw):
    data = raw.copy()
    data["date"] = pd.to_datetime(dict(year=data.year, month=data.month, day=1))
    data = data.sort_values(["hotel_name", "date"]).drop_duplicates(["hotel_name", "date"], keep="last")
    result = data.copy()
    for months in (1, 2, 3, 12):
        result = add_calendar_lag(data, result, "occupancy_rate", f"occupancy_lag_{months}", months)
    for column in LAGGED_INPUTS:
        result = add_calendar_lag(data, result, column, f"input_{column}", 1)
    result["occupancy_roll3"] = result[["occupancy_lag_1", "occupancy_lag_2", "occupancy_lag_3"]].mean(axis=1)
    result["month_sin"] = np.sin(2 * np.pi * result["month"] / 12)
    result["month_cos"] = np.cos(2 * np.pi * result["month"] / 12)
    return result


def build_model(estimator, scale=False):
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale:
        numeric_steps.append(("scaler", StandardScaler()))
    preprocessor = ColumnTransformer([
        ("num", Pipeline(numeric_steps), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])
    return Pipeline([("preprocessor", preprocessor), ("model", estimator)])


def metrics(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    valid = np.isfinite(actual) & np.isfinite(predicted)
    actual, predicted = actual[valid], predicted[valid]
    return {
        "mae": round(mean_absolute_error(actual, predicted), 2),
        "rmse": round(mean_squared_error(actual, predicted) ** 0.5, 2),
        "r2": round(r2_score(actual, predicted), 4),
        "bias": round(float(np.mean(predicted - actual)), 2),
        "n": int(len(actual)),
    }


def recursive_fixed_origin(model, raw, origin_end, horizon_start, horizon_end):
    history = raw[raw["date"] <= origin_end].copy()
    latest = history.sort_values("date").groupby("hotel_name", as_index=False).tail(1)
    latest = latest[latest["date"].eq(origin_end)].set_index("hotel_name")
    actual = raw[raw["date"].between(horizon_start, horizon_end)].set_index(["hotel_name", "date"])["occupancy_rate"]
    known = {
        (row.hotel_name, pd.Timestamp(row.date)): float(row.occupancy_rate)
        for row in history.itertuples() if pd.notna(row.occupancy_rate)
    }
    records = []
    dates = pd.date_range(horizon_start, horizon_end, freq="MS")
    for horizon, forecast_date in enumerate(dates, 1):
        rows, hotel_names = [], []
        for hotel_name, latest_row in latest.iterrows():
            lags = [known.get((hotel_name, forecast_date - pd.DateOffset(months=m)), np.nan) for m in (1, 2, 3)]
            rows.append({
                "month": forecast_date.month,
                "month_sin": np.sin(2 * np.pi * forecast_date.month / 12),
                "month_cos": np.cos(2 * np.pi * forecast_date.month / 12),
                "input_total_rooms": latest_row["total_rooms"],
                "input_employees": latest_row["employees"],
                "input_avg_price": latest_row["avg_price"],
                "input_domestic_ratio": latest_row["domestic_ratio"],
                "input_international_ratio": latest_row["international_ratio"],
                "input_individual_ratio": latest_row["individual_ratio"],
                "occupancy_lag_1": lags[0], "occupancy_lag_2": lags[1], "occupancy_lag_3": lags[2],
                "occupancy_lag_12": known.get((hotel_name, forecast_date - pd.DateOffset(months=12)), np.nan),
                "occupancy_roll3": np.nanmean(lags) if any(pd.notna(v) for v in lags) else np.nan,
                "city": latest_row["city"], "star_rating": latest_row["star_rating"],
            })
            hotel_names.append(hotel_name)
        preds = np.clip(model.predict(pd.DataFrame(rows)[FEATURES]), 0, 100)
        for hotel_name, prediction in zip(hotel_names, preds):
            known[(hotel_name, forecast_date)] = float(prediction)
            try:
                actual_value = actual.loc[(hotel_name, forecast_date)]
            except KeyError:
                continue
            records.append({
                "date": forecast_date, "year": forecast_date.year, "month": forecast_date.month,
                "horizon": horizon, "city": latest.loc[hotel_name, "city"], "hotel_name": hotel_name,
                "actual_occupancy": float(actual_value), "predicted_occupancy": float(prediction),
            })
    result = pd.DataFrame(records)
    result["error"] = result["predicted_occupancy"] - result["actual_occupancy"]
    result["absolute_error"] = result["error"].abs()
    return result


def main():
    t0 = time.time()
    MODEL_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    raw = pd.read_csv(INPUT)
    features = build_features(raw)

    train = features[features["date"].between(TRAIN_START, TRAIN_END)].copy()
    val = features[features["date"].between(VAL_START, VAL_END)].copy()
    test = features[features["date"].between(TEST_START, TEST_END)].copy()
    refit_set = features[features["date"].between(TRAIN_START, REFIT_END)].copy()
    production = features[features["date"].between(TRAIN_START, PRODUCTION_END)].copy()

    print(f"train={len(train)} val={len(val)} test={len(test)} refit={len(refit_set)}")

    # ── 步驟一：只在訓練集上 fit，只在驗證集(2025)上比較 ──────
    candidates = {
        "Ridge": build_model(Ridge(alpha=10.0), scale=True),
        "Random Forest": build_model(RandomForestRegressor(n_estimators=300, max_depth=8, random_state=42, n_jobs=-1)),
    }
    gb_grid = list(product([150, 180, 200, 250], [2, 3], [0.03, 0.04, 0.05]))
    val_results = {}
    for name, model in candidates.items():
        model.fit(train[FEATURES], train["occupancy_rate"])
        pred = np.clip(model.predict(val[FEATURES]), 0, 100)
        val_results[name] = metrics(val["occupancy_rate"], pred)

    best_gb_key, best_gb_mae, best_gb_model = None, 1e9, None
    for n_est, depth, lr in gb_grid:
        gb = build_model(GradientBoostingRegressor(
            n_estimators=n_est, max_depth=depth, learning_rate=lr, random_state=42))
        gb.fit(train[FEATURES], train["occupancy_rate"])
        pred = np.clip(gb.predict(val[FEATURES]), 0, 100)
        mae = mean_absolute_error(val["occupancy_rate"], pred)
        if mae < best_gb_mae:
            best_gb_mae, best_gb_key, best_gb_model = mae, (n_est, depth, lr), gb
    val_results["Gradient Boosting"] = metrics(val["occupancy_rate"],
        np.clip(best_gb_model.predict(val[FEATURES]), 0, 100))
    print(f"GB 驗證集最佳超參數：n_estimators={best_gb_key[0]}, max_depth={best_gb_key[1]}, learning_rate={best_gb_key[2]}")

    valid_baseline_val = val["occupancy_lag_1"].notna()
    val_results["Baseline (前月住房率)"] = metrics(
        val.loc[valid_baseline_val, "occupancy_rate"], val.loc[valid_baseline_val, "occupancy_lag_1"])

    selected_name = min(["Ridge", "Random Forest", "Gradient Boosting"], key=lambda n: val_results[n]["mae"])
    print(f"驗證集選出的模型：{selected_name}（MAE={val_results[selected_name]['mae']}）")

    # ── 步驟二：選模後，用 2023-2025（train+val）整批重訓 ─────
    if selected_name == "Gradient Boosting":
        final_estimator = GradientBoostingRegressor(
            n_estimators=best_gb_key[0], max_depth=best_gb_key[1], learning_rate=best_gb_key[2], random_state=42)
        final_model = build_model(final_estimator)
    elif selected_name == "Random Forest":
        final_model = build_model(RandomForestRegressor(n_estimators=300, max_depth=8, random_state=42, n_jobs=-1))
    else:
        final_model = build_model(Ridge(alpha=10.0), scale=True)
    final_model.fit(refit_set[FEATURES], refit_set["occupancy_rate"])

    # ── 步驟三：只在這裡碰一次測試集（2026H1）─────────────────
    test_pred = np.clip(final_model.predict(test[FEATURES]), 0, 100)
    test_metrics_by_model = {selected_name: metrics(test["occupancy_rate"], test_pred)}
    valid_baseline_test = test["occupancy_lag_1"].notna()
    test_metrics_by_model["Baseline (前月住房率)"] = metrics(
        test.loc[valid_baseline_test, "occupancy_rate"], test.loc[valid_baseline_test, "occupancy_lag_1"])

    rolling = test[["date", "year", "month", "city", "hotel_name", "occupancy_rate"]].copy()
    rolling = rolling.rename(columns={"occupancy_rate": "actual_occupancy"})
    rolling["predicted_occupancy"] = test_pred
    rolling["error"] = rolling["predicted_occupancy"] - rolling["actual_occupancy"]
    rolling["absolute_error"] = rolling["error"].abs()
    rolling.to_csv(ROLLING_OUTPUT, index=False, encoding="utf-8-sig")

    # ── bootstrap：改善幅度（前月基準 - 模型）的 95% CI，依旅館 cluster ──
    rolling_valid = rolling.dropna(subset=["actual_occupancy"]).copy()
    baseline_lag = test.set_index(["hotel_name", "date"])["occupancy_lag_1"]
    rolling_valid["baseline_pred"] = rolling_valid.apply(
        lambda r: baseline_lag.get((r["hotel_name"], r["date"]), np.nan), axis=1)
    rolling_valid["baseline_ae"] = (rolling_valid["baseline_pred"] - rolling_valid["actual_occupancy"]).abs()
    rolling_valid = rolling_valid.dropna(subset=["baseline_ae"])
    hotels = rolling_valid["hotel_name"].unique()
    rng = np.random.default_rng(0)
    improvements = []
    for _ in range(1000):
        picked = rng.choice(hotels, size=len(hotels), replace=True)
        sample = pd.concat([rolling_valid[rolling_valid["hotel_name"] == h] for h in picked], ignore_index=True)
        improvements.append(sample["baseline_ae"].mean() - sample["absolute_error"].mean())
    improvements = np.array(improvements)
    ci_lo, ci_hi = np.percentile(improvements, [2.5, 97.5])
    point_improve = rolling_valid["baseline_ae"].mean() - rolling_valid["absolute_error"].mean()

    # ── 固定起點六個月遞迴回測（用 2025-12 為起點，跟原版對齊）───
    raw_with_dates = raw.copy()
    raw_with_dates["date"] = pd.to_datetime(dict(year=raw_with_dates.year, month=raw_with_dates.month, day=1))
    fixed = recursive_fixed_origin(final_model, raw_with_dates, REFIT_END, TEST_START, TEST_END)
    fixed.to_csv(FIXED_OUTPUT, index=False, encoding="utf-8-sig")
    horizon_metrics = {}
    cumulative_rmse = 0.0
    for horizon, group in sorted(fixed.groupby("horizon"), key=lambda kv: kv[0]):
        horizon_result = metrics(group["actual_occupancy"], group["predicted_occupancy"])
        cumulative_rmse = max(cumulative_rmse, horizon_result["rmse"])
        horizon_result["planning_rmse"] = round(cumulative_rmse, 2)
        horizon_metrics[str(int(horizon))] = horizon_result

    # ── 縣市別 MAE（用 rolling 測試集結果）─────────────────────
    city_metrics = {}
    for city, group in rolling_valid.groupby("city"):
        city_metrics[city] = metrics(group["actual_occupancy"], group["predicted_occupancy"])
        city_metrics[city]["hotels"] = int(group["hotel_name"].nunique())

    validation = {
        "rolling_one_month": test_metrics_by_model[selected_name],
        "baseline": test_metrics_by_model["Baseline (前月住房率)"],
        "improve_pp": round(float(point_improve), 2),
        "improve_pct": round(float(point_improve / test_metrics_by_model["Baseline (前月住房率)"]["mae"] * 100), 1),
        "improve_ci_lo": round(float(ci_lo), 2),
        "improve_ci_hi": round(float(ci_hi), 2),
        "fixed_origin_by_horizon": horizon_metrics,
        "fixed_origin_overall": metrics(fixed["actual_occupancy"], fixed["predicted_occupancy"]),
        "by_city": city_metrics,
    }
    with open(VALIDATION_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(validation, f, ensure_ascii=False, indent=2)

    # ── 特徵重要性：內建 + 置換重要性（在驗證集上算，避免用測試集）──
    feature_names = final_model.named_steps["preprocessor"].get_feature_names_out()
    estimator = final_model.named_steps["model"]
    if hasattr(estimator, "feature_importances_"):
        builtin_importance = estimator.feature_importances_
    else:
        builtin_importance = np.abs(estimator.coef_)
    pd.DataFrame({"feature": feature_names, "importance": builtin_importance}).sort_values(
        "importance", ascending=False).to_csv(IMPORTANCE_OUTPUT, index=False, encoding="utf-8-sig")

    perm = permutation_importance(final_model, val[FEATURES], val["occupancy_rate"],
                                   n_repeats=8, random_state=42, scoring="neg_mean_absolute_error", n_jobs=-1)
    perm_df = pd.DataFrame({
        "feature": FEATURES,
        "mae_increase": perm.importances_mean,
        "mae_increase_std": perm.importances_std,
    }).sort_values("mae_increase", ascending=False)
    perm_df.to_csv(PERMUTATION_OUTPUT, index=False, encoding="utf-8-sig")

    joblib.dump(final_model, MODEL_OUTPUT)

    with open(RESULTS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump({"validation_selection": val_results, "final_test": test_metrics_by_model}, f, ensure_ascii=False, indent=2)

    metadata = {
        "train_start": TRAIN_START.strftime("%Y-%m"), "train_end": TRAIN_END.strftime("%Y-%m"),
        "val_start": VAL_START.strftime("%Y-%m"), "val_end": VAL_END.strftime("%Y-%m"),
        "test_start": TEST_START.strftime("%Y-%m"), "test_end": TEST_END.strftime("%Y-%m"),
        "train_rows": int(len(train)), "val_rows": int(len(val)), "test_rows": int(len(test)),
        "refit_rows": int(len(refit_set)), "production_rows": int(len(production)),
        "selected_model": selected_name,
        "gb_hyperparams": {"n_estimators": best_gb_key[0], "max_depth": best_gb_key[1], "learning_rate": best_gb_key[2]}
                          if selected_name == "Gradient Boosting" else None,
        "model_version": "monthly-3way-v1",
        # 與舊版 metadata 相容的欄位名稱，讓網頁端不用整段改寫
        "data_start": TRAIN_START.strftime("%Y-%m"),
        "data_end": PRODUCTION_END.strftime("%Y-%m"),
        "holdout_start": TEST_START.strftime("%Y-%m"),
        "holdout_end": TEST_END.strftime("%Y-%m"),
        "hotel_count": int(
            production["hotel_name"].str.strip()
            .replace({"礁溪老爺大酒店": "礁溪老爺酒店", "寒舍艾麗酒店": "台北艾麗酒店"})
            .nunique()
        ),
        "test_input_policy": "前月已知營運欄位，不使用預測當月實際 ADR 或旅客比例",
        "split_note": "訓練 2023-2024（選模不碰測試集）／驗證選模 2025／測試 2026上半年（只用一次）",
    }
    with open(METADATA_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(json.dumps(val_results, ensure_ascii=False, indent=2))
    print(json.dumps(validation["rolling_one_month"], ensure_ascii=False, indent=2))
    print(f"改善幅度 {validation['improve_pp']}pp ({validation['improve_pct']}%)，95% CI [{validation['improve_ci_lo']}, {validation['improve_ci_hi']}]")
    print(f"耗時 {time.time()-t0:.1f} 秒")


if __name__ == "__main__":
    main()
