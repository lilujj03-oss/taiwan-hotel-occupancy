# 台灣觀光旅館月度住房率預測與影響因素分析
## — 2026 上半年外部時間驗證

## 專題簡介

本專題使用交通部觀光署逐月觀光旅館營運統計資料，建立**月度住房率模型**。
模型先以 2023-01～2025-12 訓練，使用完全未參與訓練的 2026-01～2026-06
進行滾動一個月與固定起點六個月回測；驗證完成後，再使用截至 2026-06 的資料
重訓正式模型，未來預測自 2026-07 開始。

主體分析（Streamlit 儀表板）呈現 2023–2025 的歷史事實與比較；預測分為
**年度、月度、每日**三個獨立分頁，彼此不互相覆蓋。

## 資料來源

- [觀光旅館營運統計](https://admin.taiwan.net.tw/businessinfo/FilePage?a=10425)
- 資料期間：2023 年 1 月 – 2026 年 6 月
- 資料層級：每間旅館、每個月份
- 原始月度資料：4,832 筆、127 間觀光旅館
- 旅館類型：包含有星等（卓越五星～三星級）與無星等／未評鑑旅館
- 住客國籍：`data/processed/hotel_guest_nationality_detail.csv`（逐旅館逐年），彙總為
  `guest_nationality_summary.csv`；數字為**旅館住客人次**（同一旅客多晚／多間會重複計），
  與移民署「入境旅客人數」不同、數值明顯較高
- 政府辦公日曆：行政院人事行政總處 2023–2027（用於假日特徵實驗）

## 專案結構

```
├── data/
│   ├── raw/              # 原始 XLSX 下載檔
│   └── processed/        # 合併清理後的 CSV（hotel_monthly.csv 為主檔）
├── notebooks/
│   ├── 01_data_check.ipynb           # 資料品質檢查
│   ├── 02_eda.ipynb                  # 探索性資料分析
│   ├── 03_feature_engineering.ipynb  # 特徵工程
│   └── 04_modeling.ipynb             # 模型訓練與評估
├── src/
│   ├── download_monthly_data.py          # 下載觀光署逐月 XLSX
│   ├── build_monthly_data.py             # 解析月報 → hotel_monthly.csv
│   ├── build_monthly_calendar_features.py# 政府辦公日曆 → 月度日曆特徵
│   ├── export_nationality_summary.py     # 住客國籍明細 → 彙總表
│   ├── features.py                       # 年度模型特徵工程函式
│   ├── preprocessing.py                  # 年度資料清理
│   ├── train.py                          # 年度候選模型比較（採 Decision Tree）
│   ├── train_monthly_current.py          # ★ 正式月度模型與 2026 上半年時間外驗證
│   ├── train_monthly_holiday_experiment.py# 官方假日特徵實驗（未通過門檻、未採用）
│   ├── check_panel_stability.py          # 涵蓋旅館數變動對驗證指標的影響檢查
│   ├── build_daily_features.py / train_daily.py # 每日模型（尚未啟用）
│   └── predict.py                        # 儀表板呼叫的推論函式
├── pages/
│   ├── 1_年度預測分析.py   # 年度情境估算（Decision Tree，R² 約 0.40，可信度有限）
│   ├── 2_月度預測分析.py   # ★ 正式月度模型預測 + 2026 上半年回測
│   └── 3_每日預測分析.py   # 每日模型頁（無旅館端逐日實際住房率，目前僅顯示資料狀態）
├── models/                 # 訓練完成的模型 .pkl（正式月度：monthly_model_through_202606.pkl）
├── reports/                # 評估結果 JSON、特徵重要性 CSV、回測 CSV、figures/
├── app.py                  # Streamlit 主體分析儀表板（5 個分析主題）
├── requirements.txt
└── README.md
```

> 註：`src/` 另有若干探索用途的一次性腳本（`inspect_*`、`check_*`、`debug_*`、
> `parse_structure.py`、`find_months.py` 等），非主要流程。

## 安裝與執行

```bash
# 安裝套件
pip install -r requirements.txt

# 下載資料（執行一次即可）
python src/download_monthly_data.py

# 解析月報與訓練正式月度模型（含 2026 上半年時間外驗證）
python src/build_monthly_data.py
python src/train_monthly_current.py

# （選用）建立月度日曆特徵、住客國籍彙總、年度模型
python src/build_monthly_calendar_features.py
python src/export_nationality_summary.py
python src/train.py

# （選用）樣本穩定性檢查
python src/check_panel_stability.py

# 啟動 Streamlit 儀表板（app.py + pages/ 三個預測分頁一起啟動）
streamlit run app.py
```

> 全程指令以專案根目錄為工作目錄；若使用虛擬環境，請先啟用該環境的 `python`
> （Windows：`venv\Scripts\activate`），再執行上述 `python src/...`。

## 儀表板內容

**主體分析 `app.py`（5 個主題）**
1. 📊 整體營運與住房趨勢：年度指數化走勢、月份季節性（都會 vs 度假）、年度營運總覽、縣市排行
2. 🏨 個別旅館年度實績：單一旅館的年度營收、人力效率、逐月住房率、同儕比較
3. ⭐ 星級認證效益分析：各星等住房率／ADR／RevPAR、有星等 vs 無星等分布（關聯非因果）
4. 🌍 住客國籍與客源結構分析：本國 vs 國際、散客 vs 團體、主要客源疫後回流
5. 🔍 影響因素與特徵解析：房價／規模分箱、機器學習特徵重要性、2026 上半年時間外測試

**預測分頁**
- 年度：情境估算工具，非精確承諾（Decision Tree，R² 約 0.40、RMSE 約 15 個百分點）
- 月度：正式模型（Gradient Boosting），一個月預測最可靠；六個月遞迴誤差擴大
- 每日：尚未取得旅館端逐日實際住房率，目前不產出預測，僅顯示資料累積狀態

## 分析項目

1. **整體住房率趨勢**：各月份、各年度住房率變化
2. **地區比較**：各縣市住房率、RevPAR 差異（部分縣市僅 1–2 間觀光旅館）
3. **星等比較**：不同星等住房率與房價關係
4. **季節性分析**：月份、前月、近 3 月與去年同月效果
5. **旅客結構**：本國 vs 國際旅客對住房率影響
6. **住房率預測**：使用 ML 模型預測下個月住房率
7. **特徵重要性**：找出模型最依賴的因素（前 1／近 3／去年同月住房率合計約 94%）
8. **星級認證效益**：有星等 vs 無星等觀光旅館住房率、房價、RevPAR 比較
9. **疫後恢復分析**：2023→2025 國際旅客回流與住房率恢復趨勢

## 模型

| 模型 | 演算法 | 用途 | 現況 |
|------|------|------|------|
| 前月住房率（Baseline） | — | 比較基準 | 月度回測 MAE 7.51 |
| Ridge / Random Forest / Gradient Boosting | 線性 / 隨機森林 / 梯度提升 | 月度候選模型 | **Gradient Boosting 為正式月度模型**（2026 上半年滾動 MAE 6.08、R² 0.845） |
| 年度候選模型 | Baseline（縣市平均）/ Decision Tree / RF / GB | 年度情境估算 | **採 Decision Tree**（R² 約 0.40）；Linear Regression / Ridge 因年度特徵未標準化而 R² 為極大負值，僅列於程式輸出、儀表板已隱藏 |
| 每日模型 | Gradient Boosting（規劃中） | 每日住房率預測 | **未啟用**（無旅館端逐日實際住房率） |
| 假日特徵實驗 | 在月度模型加官方辦公日曆特徵 | 檢驗連假效果 | **未採用**（未同時通過 rolling MAE、fixed MAE、fixed RMSE 三門檻） |

## 資料與模型限制

- 資料為飯店層級彙總資料，非單筆訂單紀錄；無法分析單筆取消原因或個人行為
- 星等以**現行**認證回填全期間，少數旅館歷史星等可能不同
- 目前未納入連假、重大活動、天氣、即時訂房進度與取消率（假日特徵已做實驗但未採用）
- 一個月預測最可靠；多月遞迴預測會隨距離增加而擴大誤差（六個月 MAE 約 7.5）
- 特徵重要性代表模型依賴程度，不代表因果關係；模型約 94% 依賴住房率自身慣性與季節性，
  房價、旅客結構、員工數等營運輸入合計影響 < 3%
- 年度模型僅有 3 年資料，「三年趨勢」訓練樣本為 0，實用價值有限；建議未來以月度模型 12 個月預測彙總成年度
- 「都會 vs 度假」為依縣市所在地的人工分類，非旅館實際定位或分群模型結果
- 住客國籍數字為「旅館住客人次」，遠大於移民署入境旅客人數
- 涵蓋旅館數逐年不同（改名、換品牌、極少數歇業）；經平衡樣本檢查，對月度模型驗證指標影響 < 0.1 個百分點
- 地區誤差差異大：都會商務型縣市 MAE 約 4–6，東部度假型（尤其台東）約 8–13
