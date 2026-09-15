# -*- coding: utf-8 -*-
"""
把簡報要用的每一個數字，全部從 data/processed/hotel_monthly.csv 與 reports/*.json 重算，
輸出 facts.json。簡報生成器只讀 facts.json，不得在投影片裡寫死任何數字。

口徑規則（與 app.py 儀表板一致）：
  加權平均住房率 = Σ已售房晚 / Σ可售房晚
  加權 ADR       = Σ客房營收 / Σ已售房晚
  加權 RevPAR    = Σ客房營收 / Σ可售房晚
  簡單平均       = df.groupby(...).mean()，每「旅館×月」算一票
"""

import calendar
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "facts.json"

# 與 app.py load_data() 完全相同的設定
HOTEL_NAME_ALIASES = {"礁溪老爺大酒店": "礁溪老爺酒店", "寒舍艾麗酒店": "台北艾麗酒店"}
RESORT_CITIES = ["宜蘭縣", "花蓮縣", "南投縣", "屏東縣", "台東縣", "澎湖縣", "金門縣", "嘉義縣"]
STAR_ORDER = ["卓越五星", "五星級", "四星級", "三星級", "無星等/未評鑑"]


def r(x, n=2):
    return None if pd.isna(x) else round(float(x), n)


def main():
    raw = pd.read_csv(ROOT / "data" / "processed" / "hotel_monthly.csv")
    raw["clean_hotel_name"] = raw["hotel_name"].str.strip().replace(HOTEL_NAME_ALIASES)
    raw["cluster"] = raw["city"].apply(lambda c: "風景度假" if c in RESORT_CITIES else "都會商務")
    raw["days"] = [calendar.monthrange(int(y), int(m))[1] for y, m in zip(raw["year"], raw["month"])]
    raw["avail"] = raw["total_rooms"] * raw["days"]
    raw["sold"] = raw["rooms_used"]

    f = {}
    f["_note"] = "全部數字由 compute_facts.py 自 data/processed/hotel_monthly.csv 與 reports/ 重算"

    # ── 資料規模 ────────────────────────────────────────────
    hist = raw[raw["year"].between(2023, 2025)].copy()
    f["scope"] = {
        "rows_all": int(len(raw)),
        "rows_hist": int(len(hist)),
        "rows_2026h1": int(len(raw[raw["year"] == 2026])),
        "months": int(raw.groupby(["year", "month"]).ngroups),
        "hotels_all": int(raw["clean_hotel_name"].nunique()),
        "hotels_hist": int(hist["clean_hotel_name"].nunique()),
        "raw_files": len(list((ROOT / "data" / "raw" / "monthly").glob("*"))),
    }

    # ── 年度加權總表 ────────────────────────────────────────
    g = hist.groupby("year").agg(
        avail=("avail", "sum"), sold=("sold", "sum"),
        rev=("room_revenue", "sum"), food=("food_revenue", "sum"),
        total=("total_revenue", "sum"), guests=("total_guests", "sum"),
        n=("clean_hotel_name", "nunique"),
    )
    g["occ"] = g["sold"] / g["avail"] * 100
    g["adr"] = g["rev"] / g["sold"]
    g["revpar"] = g["rev"] / g["avail"]
    # 12 個月完整在榜的旅館數
    mc = hist.groupby(["year", "clean_hotel_name"]).size()
    g["n12"] = mc[mc >= 12].groupby(level="year").size()

    f["annual"] = {
        "years": [int(y) for y in g.index],
        "occ": [r(v) for v in g["occ"]],
        "adr": [r(v, 0) for v in g["adr"]],
        "revpar": [r(v, 0) for v in g["revpar"]],
        "sold_wan": [r(v / 1e4, 1) for v in g["sold"]],
        "avail_wan": [r(v / 1e4, 1) for v in g["avail"]],
        "room_rev_yi": [r(v / 1e8, 1) for v in g["rev"]],
        "food_rev_yi": [r(v / 1e8, 1) for v in g["food"]],
        "total_rev_yi": [r(v / 1e8, 1) for v in g["total"]],
        "guests_wan": [r(v / 1e4, 1) for v in g["guests"]],
        "hotels": [int(v) for v in g["n"]],
        "hotels_12m": [int(v) for v in g["n12"]],
    }
    f["annual"]["occ_delta_pp"] = r(g["occ"].iloc[-1] - g["occ"].iloc[0])
    f["annual"]["sold_delta_wan"] = r((g["sold"].iloc[-1] - g["sold"].iloc[-2]) / 1e4, 1)

    # ── 指數化（2023 = 100，加權口徑）───────────────────────
    f["index"] = {
        "years": [int(y) for y in g.index],
        "occ": [r(v / g["occ"].iloc[0] * 100, 1) for v in g["occ"]],
        "adr": [r(v / g["adr"].iloc[0] * 100, 1) for v in g["adr"]],
        "revpar": [r(v / g["revpar"].iloc[0] * 100, 1) for v in g["revpar"]],
    }

    # ── 月份季節性（簡單平均，與 app.py 同圖一致）───────────
    season = hist.pivot_table(index="month", columns="cluster", values="occupancy_rate", aggfunc="mean")
    f["season"] = {
        "months": [int(m) for m in season.index],
        "urban": [r(v, 1) for v in season["都會商務"]],
        "resort": [r(v, 1) for v in season["風景度假"]],
        "urban_mean": r(hist.loc[hist["cluster"] == "都會商務", "occupancy_rate"].mean()),
        "resort_mean": r(hist.loc[hist["cluster"] == "風景度假", "occupancy_rate"].mean()),
        "urban_swing": r(season["都會商務"].max() - season["都會商務"].min(), 1),
        "resort_swing": r(season["風景度假"].max() - season["風景度假"].min(), 1),
        "urban_peak_month": int(season["都會商務"].idxmax()),
        "resort_peak_month": int(season["風景度假"].idxmax()),
        "urban_trough_month": int(season["都會商務"].idxmin()),
        "resort_trough_month": int(season["風景度假"].idxmin()),
        "avg_gap": r((season["都會商務"] - season["風景度假"]).mean(), 1),
    }
    cl = hist.groupby("cluster").agg(a=("avail", "sum"), s=("sold", "sum"), rv=("room_revenue", "sum"))
    f["season"]["urban_adr_w"] = r(cl.loc["都會商務", "rv"] / cl.loc["都會商務", "s"], 0)
    f["season"]["resort_adr_w"] = r(cl.loc["風景度假", "rv"] / cl.loc["風景度假", "s"], 0)
    f["season"]["urban_revpar_w"] = r(cl.loc["都會商務", "rv"] / cl.loc["都會商務", "a"], 0)
    f["season"]["resort_revpar_w"] = r(cl.loc["風景度假", "rv"] / cl.loc["風景度假", "a"], 0)

    # 加權口徑的同一條月曲線（供簡報說明「換口徑結論不變」）
    ws = hist.groupby(["cluster", "month"]).agg(a=("avail", "sum"), s=("sold", "sum"))
    ws = (ws["s"] / ws["a"] * 100).unstack(0)
    f["season"]["urban_swing_w"] = r(ws["都會商務"].max() - ws["都會商務"].min(), 1)
    f["season"]["resort_swing_w"] = r(ws["風景度假"].max() - ws["風景度假"].min(), 1)
    f["season"]["urban_mean_w"] = r(cl.loc["都會商務", "s"] / cl.loc["都會商務", "a"] * 100)
    f["season"]["resort_mean_w"] = r(cl.loc["風景度假", "s"] / cl.loc["風景度假", "a"] * 100)

    # ── 縣市 ────────────────────────────────────────────────
    city = hist.groupby("city").agg(
        n=("clean_hotel_name", "nunique"), occ=("occupancy_rate", "mean"),
        a=("avail", "sum"), s=("sold", "sum"), rv=("room_revenue", "sum"),
        tot=("total_revenue", "sum"),
    )
    city["occ_w"] = city["s"] / city["a"] * 100
    city["rev_share"] = city["tot"] / city["tot"].sum() * 100
    city = city.sort_values("occ_w", ascending=False)
    city_yr = hist.pivot_table(index="city", columns="year", values="occupancy_rate", aggfunc="mean")
    f["city"] = {
        "names": city.index.tolist(),
        "n": [int(v) for v in city["n"]],
        "occ_simple": [r(v, 1) for v in city["occ"]],
        "occ_weighted": [r(v, 1) for v in city["occ_w"]],
        "rev_share": [r(v, 1) for v in city["rev_share"]],
        "by_year": {c: [r(city_yr.loc[c, y], 1) for y in [2023, 2024, 2025]] for c in city.index},
    }
    f["city"]["taipei_rev_share"] = r(city.loc["台北市", "rev_share"], 1)
    f["city"]["hualien_drop_pp"] = r(city_yr.loc["花蓮縣", 2023] - city_yr.loc["花蓮縣", 2024], 1)

    # ── 客源結構（加權人次）─────────────────────────────────
    ng = hist.groupby("year").agg(
        dom=("domestic_guests", "sum"), tot=("total_guests", "sum"),
        ind=("individual_guests", "sum"), grp=("group_guests", "sum"),
        jp=("japan_guests", "sum"), kr=("korea_guests", "sum"),
        hk=("hk_mo_guests", "sum"), us=("usa_guests", "sum"),
    )
    f["guests"] = {
        "years": [int(y) for y in ng.index],
        "intl_ratio": [r((t - d) / t * 100, 1) for d, t in zip(ng["dom"], ng["tot"])],
        "dom_ratio": [r(d / t * 100, 1) for d, t in zip(ng["dom"], ng["tot"])],
        "fit_ratio": [r(i / (i + p) * 100, 1) for i, p in zip(ng["ind"], ng["grp"])],
        "group_ratio": [r(p / (i + p) * 100, 1) for i, p in zip(ng["ind"], ng["grp"])],
        "japan_wan": [r(v / 1e4, 1) for v in ng["jp"]],
        "korea_wan": [r(v / 1e4, 1) for v in ng["kr"]],
        "hkmo_wan": [r(v / 1e4, 1) for v in ng["hk"]],
        "usa_wan": [r(v / 1e4, 1) for v in ng["us"]],
    }
    f["guests"]["intl_delta_pp"] = r(f["guests"]["intl_ratio"][-1] - f["guests"]["intl_ratio"][0], 1)

    # ── 星等（加權，與 app.py star_summary 一致）────────────
    st_ = hist.groupby("star_rating").agg(
        n=("clean_hotel_name", "nunique"), a=("avail", "sum"),
        s=("sold", "sum"), rv=("room_revenue", "sum"),
    )
    st_["occ"] = st_["s"] / st_["a"] * 100
    st_["adr"] = st_["rv"] / st_["s"]
    st_["revpar"] = st_["rv"] / st_["a"]
    st_["rev_share"] = st_["rv"] / st_["rv"].sum() * 100
    st_ = st_.reindex([s for s in STAR_ORDER if s in st_.index])
    f["star"] = {
        "names": st_.index.tolist(),
        "n": [int(v) for v in st_["n"]],
        "occ": [r(v, 1) for v in st_["occ"]],
        "adr": [r(v, 0) for v in st_["adr"]],
        "revpar": [r(v, 0) for v in st_["revpar"]],
        "rev_share": [r(v, 1) for v in st_["rev_share"]],
    }
    f["star"]["revpar_5_over_3"] = r(st_.loc["五星級", "revpar"] / st_.loc["三星級", "revpar"])
    f["star"]["adr_5_over_3"] = r(st_.loc["五星級", "adr"] / st_.loc["三星級", "adr"])
    f["star"]["five_rev_share"] = r(st_.loc["五星級", "rev_share"], 1)
    f["star"]["five_plus_rev_share"] = r(st_.loc["五星級", "rev_share"] + st_.loc["卓越五星", "rev_share"], 1)
    f["star"]["n_starred"] = int(hist.loc[hist["has_star"] == 1, "clean_hotel_name"].nunique())
    f["star"]["n_unstarred"] = int(hist.loc[hist["has_star"] == 0, "clean_hotel_name"].nunique())

    # ── 有星等 vs 無星等（兩種口徑都給，避免混用）──────────
    hs_simple = hist.groupby("has_star")["occupancy_rate"].mean()
    hs_price = hist.groupby("has_star")["avg_price"].mean()
    hw = hist.groupby("has_star").agg(a=("avail", "sum"), s=("sold", "sum"), rv=("room_revenue", "sum"))
    f["star_gap"] = {
        "occ_simple": {"star": r(hs_simple[1]), "nostar": r(hs_simple[0]),
                       "gap_pp": r(hs_simple[1] - hs_simple[0])},
        "occ_weighted": {"star": r(hw.loc[1, "s"] / hw.loc[1, "a"] * 100),
                         "nostar": r(hw.loc[0, "s"] / hw.loc[0, "a"] * 100),
                         "gap_pp": r(hw.loc[1, "s"] / hw.loc[1, "a"] * 100 - hw.loc[0, "s"] / hw.loc[0, "a"] * 100)},
        "adr_simple": {"star": r(hs_price[1], 0), "nostar": r(hs_price[0], 0),
                       "gap_pct": r((hs_price[1] / hs_price[0] - 1) * 100, 1)},
        "adr_weighted": {"star": r(hw.loc[1, "rv"] / hw.loc[1, "s"], 0),
                         "nostar": r(hw.loc[0, "rv"] / hw.loc[0, "s"], 0),
                         "gap_pct": r(((hw.loc[1, "rv"] / hw.loc[1, "s"]) / (hw.loc[0, "rv"] / hw.loc[0, "s"]) - 1) * 100, 1)},
    }

    # ── 星等溢價：OLS 控制縣市＋房間數＋月份＋客源結構，依旅館 cluster bootstrap 95% CI ──
    _ols_need = ["occupancy_rate", "has_star", "star_rating", "city", "total_rooms", "month",
                 "domestic_ratio", "international_ratio", "individual_ratio", "clean_hotel_name"]
    do = hist.dropna(subset=_ols_need).copy()

    def _ols_design(df):
        X = pd.DataFrame(index=df.index)
        X["const"] = 1.0
        X["has_star"] = df["has_star"].astype(float)
        X["log_rooms"] = np.log(df["total_rooms"].astype(float))
        X["domestic_ratio"] = df["domestic_ratio"].astype(float)
        X["international_ratio"] = df["international_ratio"].astype(float)
        X["individual_ratio"] = df["individual_ratio"].astype(float)
        X = X.join(pd.get_dummies(df["city"], prefix="city", drop_first=True).astype(float))
        X = X.join(pd.get_dummies(df["month"], prefix="m", drop_first=True).astype(float))
        return X

    def _ols_beta(df, col="has_star"):
        X = _ols_design(df)
        beta, *_ = np.linalg.lstsq(X.values, df["occupancy_rate"].astype(float).values, rcond=None)
        return dict(zip(X.columns, beta))[col]

    _b_hasstar = _ols_beta(do)
    _hotels = do["clean_hotel_name"].unique()
    _rng = np.random.default_rng(0)
    _boot = []
    for _ in range(600):
        _pick = _rng.choice(_hotels, size=len(_hotels), replace=True)
        _samp = pd.concat([do[do["clean_hotel_name"] == h] for h in _pick], ignore_index=True)
        try:
            _boot.append(_ols_beta(_samp))
        except Exception:
            pass
    _boot = np.array(_boot)
    _lo, _hi = np.percentile(_boot, [2.5, 97.5])

    _by_star = do.groupby("star_rating")["occupancy_rate"].mean()
    _order = ["三星級", "四星級", "五星級", "卓越五星"]
    _Xs = _ols_design(do).drop(columns=["has_star"])
    _Xs = _Xs.join(pd.get_dummies(do["star_rating"], prefix="star").astype(float)[[f"star_{s}" for s in _order]])
    _beta_s, *_ = np.linalg.lstsq(_Xs.values, do["occupancy_rate"].astype(float).values, rcond=None)
    _bm = dict(zip(_Xs.columns, _beta_s))

    f["star_ols"] = {
        "n_rows": int(len(do)), "n_hotels": int(do["clean_hotel_name"].nunique()),
        "raw_gap_pp": r(do.loc[do["has_star"] == 1, "occupancy_rate"].mean()
                        - do.loc[do["has_star"] == 0, "occupancy_rate"].mean()),
        "controlled_pp": r(_b_hasstar),
        "ci_lo": r(_lo), "ci_hi": r(_hi),
        "confound_pp": r(do.loc[do["has_star"] == 1, "occupancy_rate"].mean()
                          - do.loc[do["has_star"] == 0, "occupancy_rate"].mean() - _b_hasstar),
        "by_star": {
            s: {"raw_pp": r(_by_star[s] - _by_star["無星等/未評鑑"]), "controlled_pp": r(_bm[f"star_{s}"])}
            for s in _order
        },
    }

    # ── 房價 8 分位（簡單平均，與 app.py fig_price 一致）────
    pr = hist[hist["avg_price"] > 0].copy()
    pr["bin"] = pd.qcut(pr["avg_price"], 8)
    pb = pr.groupby("bin", observed=True).agg(occ=("occupancy_rate", "mean"), n=("occupancy_rate", "size"))
    f["price_bins"] = {
        "labels": [f"{int(i.left):,}–{int(i.right):,}" for i in pb.index],
        "occ": [r(v, 1) for v in pb["occ"]],
        "n": [int(v) for v in pb["n"]],
    }
    f["price_bins"]["best_label"] = f["price_bins"]["labels"][int(pb["occ"].values.argmax())]
    f["price_bins"]["best_occ"] = r(pb["occ"].max(), 1)
    f["price_bins"]["worst_occ"] = r(pb["occ"].iloc[0], 1)
    f["price_bins"]["top_occ"] = r(pb["occ"].iloc[-1], 1)
    f["price_bins"]["plateau_min"] = r(pb["occ"].iloc[1:].min(), 1)
    f["price_bins"]["plateau_max"] = r(pb["occ"].iloc[1:].max(), 1)

    # ── 客房規模（固定級距 + 分位，兩者都給）───────────────
    rb = hist.copy()
    rb["bin"] = pd.cut(rb["total_rooms"], [0, 80, 200, 350, 10**6],
                       labels=["< 80 間", "80–200 間", "200–350 間", "> 350 間"])
    rg = rb.groupby("bin", observed=True).agg(
        occ=("occupancy_rate", "mean"), adr=("avg_price", "mean"),
        n=("clean_hotel_name", "nunique"), a=("avail", "sum"),
        s=("sold", "sum"), rv=("room_revenue", "sum"),
    )
    f["room_bins"] = {
        "labels": rg.index.astype(str).tolist(),
        "occ_simple": [r(v, 1) for v in rg["occ"]],
        "occ_weighted": [r(s / a * 100, 1) for s, a in zip(rg["s"], rg["a"])],
        "adr_simple": [r(v, 0) for v in rg["adr"]],
        "adr_weighted": [r(v / s, 0) for v, s in zip(rg["rv"], rg["s"])],
        "hotels": [int(v) for v in rg["n"]],
    }

    # ── 模型指標（直接讀 reports/；三段式時間切分：訓練2023-2024／驗證選模2025／盲測2026H1）──
    rep = ROOT / "reports"
    val = json.loads((rep / "monthly_2026h1_validation_3way.json").read_text(encoding="utf-8"))
    mres = json.loads((rep / "model_results_monthly_3way.json").read_text(encoding="utf-8"))
    meta3 = json.loads((rep / "monthly_model_3way_metadata.json").read_text(encoding="utf-8"))
    panel = json.loads((rep / "panel_stability_check_3way.json").read_text(encoding="utf-8"))
    vsel = mres["validation_selection"]
    base_mae_val = vsel["Baseline (前月住房率)"]["mae"]
    base_mae = val["baseline"]["mae"]
    gb = val["rolling_one_month"]
    f["model"] = {
        # 候選模型比較在「驗證集（2025）」上做，選模階段完全沒碰過測試集
        "candidates": [
            {"name": k, "mae": v["mae"], "rmse": v["rmse"], "r2": round(v["r2"], 4),
             "bias": v["bias"], "n": v["n"],
             "improve_pct": r((base_mae_val - v["mae"]) / base_mae_val * 100, 1)}
            for k, v in vsel.items()
        ],
        "baseline_mae": base_mae,
        "baseline_mae_val": base_mae_val,
        "best": {"name": meta3["selected_model"], **gb, "improve_pct": r((base_mae - gb["mae"]) / base_mae * 100, 1)},
        "improve_ci_lo": val["improve_ci_lo"],
        "improve_ci_hi": val["improve_ci_hi"],
        "horizons": [
            {"h": int(h), "mae": v["mae"], "rmse": v["rmse"], "r2": round(v["r2"], 4), "bias": v["bias"]}
            for h, v in sorted(val["fixed_origin_by_horizon"].items(), key=lambda x: int(x[0]))
        ],
        "fixed_overall": val["fixed_origin_overall"],
        "train_rows": meta3["train_rows"],
        "val_rows": meta3["val_rows"],
        "test_rows": meta3["test_rows"],
        "refit_rows": meta3["refit_rows"],
        "train_period": f"{meta3['train_start']}~{meta3['train_end']}",
        "val_period": f"{meta3['val_start']}~{meta3['val_end']}",
        "test_period": f"{meta3['test_start']}~{meta3['test_end']}",
        "gb_hyperparams": meta3["gb_hyperparams"],
    }

    fi = pd.read_csv(rep / "feature_importance_monthly_3way.csv")
    fi["name"] = fi["feature"].str.replace(r"^(num|cat)__", "", regex=True)
    top = fi.head(8)
    _ops_cols = ["num__input_avg_price", "num__input_domestic_ratio", "num__input_international_ratio",
                 "num__input_individual_ratio", "num__input_employees"]
    f["importance"] = {
        "names": top["name"].tolist(),
        "values": [r(v * 100, 1) for v in top["importance"]],
        "top3_sum": r(fi["importance"].head(3).sum() * 100, 1),
        "ops_levers_pct": r(fi.loc[fi["feature"].isin(_ops_cols), "importance"].sum() * 100, 2),
    }

    # 置換重要性（permutation importance）：驗證集上算，改善負責任地歸因於「拿掉這個特徵後 MAE 惡化多少」
    perm = pd.read_csv(rep / "permutation_importance_monthly_3way.csv")
    perm_top = perm.head(8)
    _ops_feats = ["input_avg_price", "input_domestic_ratio", "input_international_ratio",
                  "input_individual_ratio", "input_employees"]
    f["perm_importance"] = {
        "names": perm_top["feature"].tolist(),
        "mae_increase": [r(v, 3) for v in perm_top["mae_increase"]],
        "top3_sum_mae_increase": r(perm["mae_increase"].head(3).sum(), 2),
        "ops_levers_mae_increase": r(perm.loc[perm["feature"].isin(_ops_feats), "mae_increase"].sum(), 2),
    }

    # ── 多基準對照（次月預測，2026 H1）：GB 是否真的比簡單方法好 ──
    _b = raw.sort_values(["clean_hotel_name", "year", "month"]).copy()
    _g = _b.groupby("clean_hotel_name")["occupancy_rate"]
    _b["_lag1"] = _g.shift(1)
    _b["_lag12"] = _g.shift(12)
    _b["_roll3"] = _g.shift(1).groupby(_b["clean_hotel_name"]).rolling(3, min_periods=3).mean().reset_index(level=0, drop=True)
    _te = _b[(_b["year"] == 2026) & (_b["month"].between(1, 6))]

    def _mae(col):
        a, p = _te["occupancy_rate"], _te[col]
        k = a.notna() & p.notna()
        return r(float((a[k] - p[k]).abs().mean()))

    f["baselines"] = {
        "rows": [
            {"name": "照抄上月", "mae": _mae("_lag1")},
            {"name": "去年同月", "mae": _mae("_lag12")},
            {"name": "近 3 個月平均", "mae": _mae("_roll3")},
            {"name": "Gradient Boosting（本模型）", "mae": gb["mae"]},
        ],
    }
    _best_base = min(x["mae"] for x in f["baselines"]["rows"][:3])
    f["baselines"]["beats_best_baseline_pp"] = r(_best_base - gb["mae"])
    f["baselines"]["beats_best_baseline_pct"] = r((_best_base - gb["mae"]) / _best_base * 100, 1)
    f["baselines"]["improve_ci_lo"] = val["improve_ci_lo"]
    f["baselines"]["improve_ci_hi"] = val["improve_ci_hi"]

    pr_ = panel["backtests"]["rolling_one_month"]
    f["robust"] = {
        "all": pr_["all"], "balanced": pr_["balanced_panel"], "unbalanced": pr_["unbalanced_only"],
        "present_all_three_years": panel["presence"]["present_all_three_years"],
        "hotels_per_year": panel["presence"]["hotels_per_year"],
        "by_city": {k: v for k, v in sorted(pr_["by_city"].items(), key=lambda x: x[1]["MAE"])},
        "by_room_size": pr_["by_room_size"],
        "balanced_gap_pp": r(pr_["all"]["MAE"] - pr_["balanced_panel"]["MAE"]),
        "fixed_by_city": panel["backtests"]["fixed_six_month"]["by_city"],
    }

    OUT.write_text(json.dumps(f, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"facts.json written: {OUT}")
    print(f"  年度加權住房率 {f['annual']['occ']}")
    print(f"  指數 住房率{f['index']['occ']} ADR{f['index']['adr']} RevPAR{f['index']['revpar']}")
    print(f"  季節擺盪 都會{f['season']['urban_swing']}pp / 度假{f['season']['resort_swing']}pp")
    print(f"  星等家數 {dict(zip(f['star']['names'], f['star']['n']))}")
    print(f"  GB MAE {f['model']['best']['mae']} 改善 {f['model']['best']['improve_pct']}%")


if __name__ == "__main__":
    main()
