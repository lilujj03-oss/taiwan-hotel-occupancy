# -*- coding: utf-8 -*-
"""
台灣觀光旅館住房率分析與預測 — 價值重構版（25 頁，完整內容）

依老師回饋重做「講法」，但內容不砍：
  1. 結論先行（BLUF）：每頁標題就是結論，先講「這代表什麼／該做什麼」，再講「為什麼」。
  2. 每張圖都要有「圖表背後的意義」，不做純描述。
  3. 每個結論都配一句「效益／對誰有用」。
  4. 新增「多基準對照」頁，證明模型比 3 種簡單方法都好。

沿用 build_deck.py 的全部基礎元件，只重寫投影片序列。輸出另存為「_價值重構版_…」。

執行：
  python 旅館分析-claude/build_deck_v2.py            # 白底（預設）
  python 旅館分析-claude/build_deck_v2.py darktheme  # 全深色
"""

import csv as _csv
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_src = (_HERE / "build_deck.py").read_text(encoding="utf-8")
_infra = _src.split("# ══ 01 封面")[0]
_infra = _infra.replace('[sys.executable, __file__, _st]',
                        '[sys.executable, str(_HERE / "build_deck_v2.py"), _st]')
exec(compile(_infra, "build_deck_infra", "exec"), globals())

TOTAL = 25
OUT = _HERE / f"台灣觀光旅館住房率分析與預測_價值重構版_{CFG['tag']}.pptx"
if OUT.exists():
    try:
        with open(OUT, "a"):
            pass
    except PermissionError:
        import time as _t
        OUT = OUT.with_name(OUT.stem + "_" + _t.strftime("%H%M%S") + OUT.suffix)
        print(f"（主檔被鎖定，改存：{OUT.name}）")

BL = F["baselines"]
YRS = [f"{y} 年" for y in A["years"]]
MON = [f"{m} 月" for m in SEA["months"]]
_small_cty = sum(1 for n in CITY["n"] if n <= 2)
_ti = CITY["names"].index("台北市")
_tyi = CITY["names"].index("桃園市")
_hli = CITY["names"].index("花蓮縣")


def head(slide, part, concl, means, src=None, hl=None):
    PAGE["n"] += 1
    bg_fill(slide, BG)
    text(slide, part, 0.62, 0.30, 7.0, 0.24, 11, BLUE, bold=True)
    rect(slide, 0.62, 0.555, 0.46, 0.030, BLUE, shape=MSO_SHAPE.RECTANGLE)
    if hl and hl[0] in concl:
        _tb = slide.shapes.add_textbox(X(0.60), Y(0.64), X(12.4), X(0.62))
        _tf = _tb.text_frame
        _tf.word_wrap = True
        _tf.margin_left = _tf.margin_right = _tf.margin_top = _tf.margin_bottom = Emu(0)
        _p = _tf.paragraphs[0]
        _p.line_spacing = 1.05
        _before, _after = concl.split(hl[0], 1)
        for _seg, _col in ((_before, T_TITLE), (hl[0], hl[1]), (_after, T_TITLE)):
            if not _seg:
                continue
            _r = _p.add_run()
            _r.text = _seg
            _r.font.name, _r.font.size, _r.font.bold, _r.font.color.rgb = FONT, FS(22), True, _col
    else:
        text(slide, concl, 0.60, 0.64, 12.4, 0.62, 22, T_TITLE, bold=True, spacing=1.05)
    tb = slide.shapes.add_textbox(X(0.62), Y(1.42), X(12.4), X(0.52))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    p.line_spacing = 1.16
    r1 = p.add_run()
    r1.text = "這代表　"
    r1.font.name, r1.font.size, r1.font.bold, r1.font.color.rgb = FONT, FS(13), True, BLUE
    r2 = p.add_run()
    r2.text = means
    r2.font.name, r2.font.size, r2.font.color.rgb = FONT, FS(13), T_BODY
    rect(slide, 0.62, 7.03, 12.1, 0.010, BORDER, shape=MSO_SHAPE.RECTANGLE)
    text(slide, src or SRC, 0.62, 7.10, 9.5, 0.26, 10, T_FAINT)
    text(slide, f"{PAGE['n']:02d} / {TOTAL}", 11.3, 7.10, 1.42, 0.26, 11, T_FAINT,
         bold=True, align=PP_ALIGN.RIGHT)
    return slide


def why(slide, txt, y=6.06, tag=None):
    rect(slide, 0.62, y, 12.1, 0.86, HEAD_BG)
    tb = slide.shapes.add_textbox(X(0.9), Y(y + 0.19), X(11.6), X(0.52))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    p.line_spacing = 1.2
    r2 = p.add_run()
    r2.text = txt
    r2.font.name, r2.font.size, r2.font.color.rgb = FONT, FS(12.5), T_BODY


def pcard(slide, l, t, w, title, items, accent=BLUE, h=3.15, size=12):
    x, y, ww = card(slide, l, t, w, h, title, accent)
    rich(slide, [("· ", it, accent) for it in items], x, y, ww, h - 0.9, size, 1.22, 7)


# ══ 01 封面 ═══════════════════════════════════════════════════
s = S()
PAGE["n"] = 1
bg_fill(s, BG)
_cbar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(PAGE_W), Inches(0.085))
_cbar.fill.solid()
_cbar.fill.fore_color.rgb = BLUE
_cbar.line.fill.background()
_cbar.shadow.inherit = False
text(s, "資料科學與旅宿收益管理專題", 0.95, 1.35, 7.0, 0.3, 12.5, CYAN, bold=True)
rect(s, 0.95, 1.82, 0.085, 1.66, BLUE, shape=MSO_SHAPE.RECTANGLE)
text(s, "台灣觀光旅館\n住房率分析與預測", 1.26, 1.80, 7.6, 1.7, 38, T_TITLE, bold=True, spacing=1.12)
text(s, f"2023–2025 營運實證　·　2026 上半年時間外驗證（{SC['rows_2026h1']} 筆盲測）",
     0.97, 3.82, 8.0, 0.32, 13.5, T_BODY)
text(s, f"{SC['months']} 個月 × {SC['hotels_all']} 間觀光旅館　|　{SC['rows_all']:,} 筆月度面板資料",
     0.97, 4.22, 8.0, 0.34, 14, T_MUTED)
rect(s, 0.95, 4.80, 7.1, 1.82, CARD, BORDER)
text(s, "重點摘要", 1.18, 4.98, 3.0, 0.26, 12, BLUE, bold=True)
rect(s, 1.18, 5.30, 0.34, 0.028, BLUE, shape=MSO_SHAPE.RECTANGLE)
text(s, "疫後復甦是「多賣房、尚未漲價」；\n"
        "只依賴旅館自己的歷史資訊，次月住房率平均誤差約 6 個百分點，能支援促銷時機、OTA 房量與排班等戰術決策。",
     1.18, 5.48, 6.7, 1.0, 15, T_BODY, spacing=1.35)
text(s, SRC, 0.97, 6.72, 8.0, 0.26, 10, T_MUTED)
_kv = [(f"{IDX['occ'][-1]} / {IDX['adr'][-1]}", "住房率 / ADR 指數（2023=100）", TEAL),
       (f"{M['best']['mae']} pp", "次月預測 MAE（勝 3 種簡單基準）", BLUE),
       (f"{FI['top3_sum']}%", "模型判斷來自住房率自身慣性", AMBER),
       (f"{RO['by_city']['台東縣']['MAE']} vs {RO['by_city']['台中市']['MAE']} pp", "台東 / 台中 預測誤差 MAE（東部風險 3×）", RED)]
text(s, "四個關鍵數字", 8.55, 1.35, 4.2, 0.34, 15, T_TITLE, bold=True)
for i, (v, lb, c) in enumerate(_kv):
    yy = 1.90 + i * 1.2625
    rect(s, 8.55, yy, 0.06, 0.95, c, shape=MSO_SHAPE.RECTANGLE)
    text(s, v, 8.85, yy + 0.04, 4.1, 0.60, 26, c, bold=True)
    text(s, lb, 8.85, yy + 0.68, 4.1, 0.50, 14, T_MUTED, spacing=1.15)
note(s, "開場 20 秒：這份報告用觀光署 42 個月、125 間觀光旅館的資料，回答兩個問題："
        "疫後復甦的真實樣貌，以及次月住房率能不能預測。左下角那句話就是全篇結論。")

# ══ 02 三個結論（純結論頁）═══════════════════════════════════
s = S()
PAGE["n"] = 2
bg_fill(s, BG)
text(s, "摘要", 0.62, 0.30, 7.0, 0.24, 11, BLUE, bold=True)
rect(s, 0.62, 0.555, 0.46, 0.030, BLUE, shape=MSO_SHAPE.RECTANGLE)
text(s, "三個結論，一個邊界", 0.60, 0.64, 12.4, 0.56, 24, T_TITLE, bold=True)
text(s, "5 分鐘只要記這一頁：先講結論，後面每一頁再展開原因。", 0.62, 1.24, 12.4, 0.3, 12, T_MUTED)
_concl = [
    ("結論 1　復甦是「量增」不是「漲價」", TEAL,
     [f"住房率指數升到 {IDX['occ'][-1]}、ADR 指數仍只有 {IDX['adr'][-1]}（2023 = 100）。",
      "效益：業者還有一輪「拉價」空間，下一步收益成長靠 ADR、不是再衝住房率。"]),
    ("結論 2　次月住房率平均誤差約 6 個百分點", BLUE,
     [f"MAE {M['best']['mae']} pp，勝過照抄上月（{BL['rows'][0]['mae']}）、去年同月（{BL['rows'][1]['mae']}）等 3 種簡單方法。",
      "效益：第 1 個月的預測能支援促銷時機、OTA 房量與排班等戰術決策。"]),
    ("結論 3　它是「預警雷達」，不是「因果搖桿」", AMBER,
     [f"模型 {FI['top3_sum']}% 靠住房率自身慣性；第 6 個月誤差擴大到 {M['horizons'][-1]['mae']} pp。",
      "效益：提前一個月看營運冷暖、排風險 SOP；不回答「該做什麼才能提升住房率」，也不作精準定價或承諾值。"]),
]
for i, (t_, c, its) in enumerate(_concl):
    yy = 1.58 + i * 1.56
    rect(s, 0.62, yy, 12.1, 1.38, CARD, BORDER)
    rect(s, 0.62, yy, 0.055, 1.38, c, shape=MSO_SHAPE.RECTANGLE)
    text(s, t_, 0.92, yy + 0.15, 11.6, 0.3, 13.5, T_TITLE, bold=True)
    rich(s, [("· ", x, c) for x in its], 0.92, yy + 0.52, 11.5, 0.8, 12, 1.22, 4)
rect(s, 0.62, 6.32, 12.1, 0.80, HEAD_BG)
text(s, "邊界　資料是「旅館 × 月」彙總，不是訂單紀錄 —— 全篇為相關非因果，"
        "無法分析單筆取消、也無法預測地震颱風等外生衝擊（東部旅館須人工覆核）。",
     0.9, 6.52, 11.6, 0.46, 12, RED, bold=True, spacing=1.2)
note(s, "40 秒：這頁是老師要的『先講結論』。三句話：一，復甦是量增不是漲價；"
        "二，次月能預測到正負六個百分點、贏過所有簡單方法；三，它是預警雷達不是因果工具。")

# ══ 03 問題與價值 ════════════════════════════════════════════
s = head(S(), "PART I · 專案緣起",
         "旅館的空房不能庫存，但營運報表永遠慢一個月",
         "若能在月初就預見次月住房率落點，調價、促銷與排班才有作用空間 —— 這就是本專案要補的時間差。")
pcard(s, 0.62, 1.88, 3.9, "問題：產能剛性", [
    "空房不可儲存：當晚未售出的客房，價值在午夜歸零。",
    "成本相對剛性：折舊、租金、固定編制人力不隨住房率同步下降。",
    "報表落後一個月：看到低谷時已無法補救。",
], RED, h=4.05)
pcard(s, 4.72, 1.88, 3.9, "作法：用歷史慣性做短期預警", [
    f"資料層：{SC['months']} 個月官方月報 → 旅館×月面板（{SC['rows_all']:,} 筆）。",
    "特徵層：只用 t-1 以前已公布的住房率滯後與季節特徵。",
    "模型層：四款候選模型在時間外資料上競賽、擇優。",
    "應用層：Streamlit 儀表板（歷史比較＋次月預測）。",
], BLUE, h=4.05)
pcard(s, 8.82, 1.88, 3.9, "效益：能用與不能用", [
    f"能用：提前一個月給住房率落點，平均誤差 {M['best']['mae']} pp。",
    "能用：辨識淡旺季節奏、星等與規模的結構差異，供市場定位與標竿比較。",
    f"不能用：只採第 1 個月的預測——多月遞迴誤差累積，第 6 個月退化到 {M['horizons'][-1]['mae']} pp、接近笨基準。",
    f"不能用：地震、颱風等結構性斷點會大幅失準，東部度假型誤差是都會的 {RO['by_city']['台東縣']['MAE'] / RO['by_city']['台中市']['MAE']:.0f} 倍。",
], TEAL, h=4.05)
why(s, "目標是補上「報表慢一個月」的時間差：給經理人一台提前一個月的空房預警——"
       "看落點、排應變，不是轉動住房率的搖桿。")
note(s, "30 秒：飯店最殘酷的是客房不能庫存、成本卻剛性，但報表永遠慢一個月。這就是我要解的時間差。"
        "請注意右邊『不能用』那欄——我先講清楚邊界。")

# ══ 04 端到端管線 ════════════════════════════════════════════
s = head(S(), "PART I · 技術架構",
         "四層模組化管線：任一層更新，只需重跑下游、不改邏輯",
         "從官方 XLSX 到 Streamlit 儀表板，每一步都以程式記錄、可完整重現。")
_layers = [
    ("Layer 1", "資料擷取與解析", BLUE,
     [f"抓取 {SC['raw_files']} 個月官方 XLSX", "解析月報 → hotel_monthly.csv", "館名標準化、改名對照"]),
    ("Layer 2", "特徵工程（防洩漏）", CYAN,
     ["lag_1 / lag_2 / lag_3 / lag_12", "roll3 = 前三月住房率均值", "月份循環 + 縣市、星等 One-Hot"]),
    ("Layer 3", "模型訓練與驗證", TEAL,
     [f"時間切分：訓練 {M['train_rows']:,} → 驗證 {M['val_rows']:,} → 盲測 {M['test_rows']}", "Pipeline 封裝 Imputer+Scaler+Encoder", "滾動一個月 + 固定六個月雙軌回測"]),
    ("Layer 4", "應用與交付", PURPLE,
     ["app.py：5 大營運分析主題", "pages/：年度／月度／每日皆上線，僅月度經本專題驗證", "Streamlit Community Cloud 部署"]),
]
_CARD_W, _GAP_W = 2.78, 0.32
_STEP = _CARD_W + _GAP_W
_TXT_W = _CARD_W - 0.48

# 先用一條「輸入 → 轉換 → 驗證 → 輸出」流程圖交代資料如何流動，
# 再於下方保留各層的實作細節；觀眾先看得懂流程，再決定要讀多深。
_flow = [
    ("輸入", "42 個月官方 XLSX", BLUE),
    ("轉換", "標準化面板 · t−1 特徵", CYAN),
    ("驗證", "時序回測 · 最佳模型", TEAL),
    ("輸出", "Streamlit 次月預警", PURPLE),
]
rect(s, 0.62, 1.91, 12.1, 0.88, HEAD_BG)
for i, (stage, output, col) in enumerate(_flow):
    l = 0.78 + i * _STEP
    rect(s, l, 2.04, 2.46, 0.62, CARD, BORDER)
    rect(s, l, 2.04, 0.055, 0.62, col, shape=MSO_SHAPE.RECTANGLE)
    text(s, stage, l + 0.18, 2.11, 0.62, 0.18, 8.5, col, bold=True)
    text(s, output, l + 0.18, 2.33, 2.12, 0.20, 10.2, T_TITLE, bold=True)
    if i < 3:
        rect(s, l + 2.54, 2.20, 0.30, 0.30, GREY, shape=MSO_SHAPE.RIGHT_ARROW)

_CARD_TOP, _CARD_H = 2.96, 2.94
for i, (tg, nm, col, its) in enumerate(_layers):
    l = 0.62 + i * _STEP
    rect(s, l, _CARD_TOP, _CARD_W, _CARD_H, CARD, BORDER)
    text(s, tg, l + 0.24, _CARD_TOP + 0.16, _TXT_W, 0.22, 9.5, col, bold=True)
    text(s, nm, l + 0.24, _CARD_TOP + 0.40, _TXT_W, 0.30, 12.5, T_TITLE, bold=True)
    rect(s, l + 0.24, _CARD_TOP + 0.78, 0.32, 0.026, col, shape=MSO_SHAPE.RECTANGLE)
    rich(s, [("· ", x, col) for x in its], l + 0.24, _CARD_TOP + 0.92,
         _TXT_W, 1.88, 10.5, 1.18, 5)
why(s, "兩道防線讓分數不灌水：① 特徵不碰當期資料　② 前處理只學訓練集 —— "
       "這是整份簡報數字可信的前提。", y=6.03)
note(s, "20 秒：先沿著上方流程圖，從官方 XLSX 一路看到 Streamlit 次月預警；下方是四層實作。"
        "重點是 Layer 2 / Layer 3 的分界：特徵只能用前一個月以前的數字。")

# ══ 05 資料工程 ══════════════════════════════════════════════
s = head(S(), "PART I · 資料工程",
         f"把 {SC['months']} 個月官方月報清理成標準化的月度資料表，過程中揪出一個讓住客人次膨脹 3–5 倍的小計列解析漏洞",
         "清理不是形式功夫：沒抓到那列小計，各年住客人次會從約 1,150 萬虛報成 3,000 萬以上。",
         hl=("小計列", AMBER))
_k = [(f"{SC['rows_all']:,} 筆", "月度面板紀錄", f"{SC['months']} 個月 × {SC['hotels_all']} 間", BLUE),
      (f"{SC['raw_files']} 檔", "原始月報 XLSX", "data/raw/monthly/", CYAN),
      (f"{SC['rows_hist']:,} / {SC['rows_2026h1']}", "訓練 / 盲測筆數", "2023-01~2025-12 / 2026 H1", TEAL),
      (f"{RO['present_all_three_years']} 間", "三年皆在榜（2023–2025）", f"2025 全年 12 月完整 {A['hotels_12m'][-1]} 間", AMBER)]
for i, (v, lb, sub, c) in enumerate(_k):
    kpi(s, 0.62 + i * 3.09, 1.98, 2.92, v, lb, sub, c)
pcard(s, 0.62, 3.60, 6.0, "三個實際處理過的資料問題", [
    "館名不一致：同一旅館跨年改名，以對照表合併。",
    "彙總列誤計：住客國籍年報在縣市尾端夾帶「小計」列，一律以「第二欄為空」規則排除，避免重複加總。",
    "樣本進出：旅館逐年進出場，另以平衡樣本驗證其對模型指標的影響。",
], AMBER, h=2.4)
pcard(s, 6.72, 3.60, 6.0, "口徑宣告", [
    "加權＝總量相除（Σ已售房晚 ÷ Σ可售房晚；ADR、RevPAR 同理）——大型旅館（房晚量大）分量重。",
    "簡單平均＝每個「旅館 × 月」各算一票，不論規模。",
    "住房率兩種口徑在本資料上差約 3 個百分點；本簡報涉及住房率的圖都標明用哪個。",
], BLUE, h=2.4)
note(s, "25 秒：資料規模在上排。下面右邊是我真正動手處理的三個問題——特別是住客國籍年報夾帶小計列、"
        "害人次膨脹三到五倍，我比對原始 XLSX 才抓到。")

# ══ 06 三年營運大表 ══════════════════════════════════════════
s = head(S(), "PART II · 營運實證",
         f"2025 加權住房率 {A['occ'][-1]}% 創疫後高點——靠多賣房晚，ADR 兩年仍低於 2023",
         "後面所有結論都建立在這張三年加權總表上——每格數字與儀表板「年度營運總覽」一致。")
_rows = [["指標（加權）", f"{A['years'][0]} 年", f"{A['years'][1]} 年", f"{A['years'][2]} 年", "2023→2025"],
         ["加權住房率", f"{A['occ'][0]}%", f"{A['occ'][1]}%", f"{A['occ'][2]}%", f"+{A['occ_delta_pp']} pp"],
         ["平均房價 ADR", f"NT${A['adr'][0]:,.0f}", f"NT${A['adr'][1]:,.0f}", f"NT${A['adr'][2]:,.0f}", f"{A['adr'][2] - A['adr'][0]:+,.0f}"],
         ["每可售房收益 RevPAR", f"NT${A['revpar'][0]:,.0f}", f"NT${A['revpar'][1]:,.0f}", f"NT${A['revpar'][2]:,.0f}", f"{A['revpar'][2] - A['revpar'][0]:+,.0f}"],
         ["已售房晚", f"{A['sold_wan'][0]:,.0f} 萬", f"{A['sold_wan'][1]:,.0f} 萬", f"{A['sold_wan'][2]:,.0f} 萬", f"+{A['sold_wan'][2] - A['sold_wan'][0]:,.0f} 萬"],
         ["客房營收", f"{A['room_rev_yi'][0]:,.0f} 億", f"{A['room_rev_yi'][1]:,.0f} 億", f"{A['room_rev_yi'][2]:,.0f} 億", f"+{A['room_rev_yi'][2] - A['room_rev_yi'][0]:,.0f} 億"],
         ["總營收（含餐飲及其他）", f"{A['total_rev_yi'][0]:,.0f} 億", f"{A['total_rev_yi'][1]:,.0f} 億", f"{A['total_rev_yi'][2]:,.0f} 億", f"+{A['total_rev_yi'][2] - A['total_rev_yi'][0]:,.0f} 億"]]
table(s, _rows, 0.62, 1.98, 8.0, 3.0, widths=[2.4, 1.2, 1.2, 1.2, 1.3], fs=11)
pcard(s, 8.75, 1.98, 3.97, "怎麼讀", [
    f"看「2023→2025」欄：住房率 +{A['occ_delta_pp']} pp、已售房晚 +{A['sold_wan'][2] - A['sold_wan'][0]:,.0f} 萬，量的變化最明顯。",
    f"ADR {A['adr'][2] - A['adr'][0]:+,.0f} 元、RevPAR {A['revpar'][2] - A['revpar'][0]:+,.0f} 元；RevPAR = 住房率 × ADR，成長來自哪一項看下頁資訊。",
    f"營收分兩種：客房 {A['room_rev_yi'][-1]:,.0f} 億 vs 含餐飲及其他 {A['total_rev_yi'][-1]:,.0f} 億，RevPAR／ADR 只用客房。",
], TEAL, h=3.0)
why(s, "2025 年住房率、RevPAR、已售房晚同創三年新高，唯獨 ADR 仍低於 2023 —— 這就是「量增、價未漲」的起點。", y=5.5)
note(s, "35 秒：這是全篇的事實底座。2024 年住房率沒動、房價還跌，2025 才真正放量。營收要分口徑。")

# ══ 07 指數化 ════════════════════════════════════════════════
s = head(S(), "PART II · 成長動能",
         "2025 的復甦是「多賣房」，不是「漲價」——ADR 兩年仍低於 2023",
         "量已補回、價還在缺口——下一輪收益成長靠把 ADR 拉回 2023，不是再衝住房率。")
chart(s, XL_CHART_TYPE.LINE_MARKERS, YRS,
      [("住房率指數", IDX["occ"]), ("ADR 指數", IDX["adr"]), ("RevPAR 指數", IDX["revpar"])],
      0.62, 1.96, 7.5, 3.9, colors=[TEAL, AMBER, BLUE], numfmt="0.0", ymin=94, ymax=108,
      point_label_pos={0: "above", 2: "above", 1: "below", (2, 2): "below"})
text(s, "加權口徑，2023 = 100", 0.80, 5.86, 4.0, 0.24, 11, T_FAINT)
pcard(s, 8.35, 1.96, 4.37, "三個指標怎麼讀", [
    f"住房率 {IDX['occ'][-1]}：三線裡唯一站上 100；2025 單年跳 +{IDX['occ'][-1] - IDX['occ'][-2]:.1f} 個指數點——回升集中在 2025。",
    f"ADR {IDX['adr'][-1]}：名目沒回 2023；扣 2024–25 通膨後，實質指數約 96，等於實質降價。",
    f"RevPAR {IDX['revpar'][-1]}：≈ 住房率 × ADR；ADR 若守住 100，RevPAR 本可到 ~{IDX['occ'][-1]:.1f}。",
], TEAL, h=3.0)
why(s, "就全台觀光旅館的加權平均而言，2025 ADR 名目、實質都低於 2023——「全面漲價」在這個層級不成立。"
       "個別高檔旅館或熱門景點漲價不會被這張圖否證。")
note(s, "30 秒：三個指標都以 2023 當 100。住房率衝到 105.6、房價指數只有 99.3 —— 成長完全是多賣房換來的。")

# ══ 08 月份季節性 ════════════════════════════════════════════
s = head(S(), "PART II · 季節節奏",
         "都會商務旅館的淡旺季落差 14 pp，反而比度假旅館的 9 pp 還大",
         "排班與促銷的季節節奏，都會型用「月」就能規劃；度假型要看到日層級（週末 vs 平日）才準。")
chart(s, XL_CHART_TYPE.LINE_MARKERS, MON,
      [("都會商務聚落", SEA["urban"]), ("風景度假聚落", SEA["resort"])],
      0.62, 1.96, 7.5, 3.9, colors=[BLUE, AMBER], numfmt="0", ymin=40, ymax=75, lbl_size=8)
text(s, "簡單平均住房率 (%)，2023–2025 合計", 0.80, 5.86, 5.0, 0.24, 11, T_FAINT)
pcard(s, 8.35, 1.96, 4.37, "三個事實", [
    f"水準：都會全年 {SEA['urban_mean']:.1f}%、度假 {SEA['resort_mean']:.1f}%——度假常年低約 {SEA['avg_gap']} pp。",
    f"高低點：都會高點 {SEA['urban_peak_month']} 月、低點 {SEA['urban_trough_month']} 月；度假低點 {SEA['resort_trough_month']} 月，高點分散在暑假與年底兩個平台。",
    f"都會的線斜（年初 {SEA['urban'][0]:.0f}% → 年底 {SEA['urban'][-1]:.0f}%），度假的線平（全年多在 {min(SEA['resort']):.0f}–{max(SEA['resort']):.0f}%）。",
], BLUE, h=3.0)
why(s, f"兩種口徑都成立：簡單平均下都會淡旺季落差 {SEA['urban_swing']} pp、度假 {SEA['resort_swing']} pp；"
       f"加權下 {SEA['urban_swing_w']} pp、{SEA['resort_swing_w']} pp。故此結論不隨統計口徑改變。")
note(s, f"40 秒——月資料上都會的淡旺季擺盪 {SEA['urban_swing']} pp 比度假的 {SEA['resort_swing']} pp 大；兩類都在 {SEA['urban_peak_month']} 月見頂，低點都會在 {SEA['urban_trough_month']} 月、度假在 {SEA['resort_trough_month']} 月。度假型最劇烈的是週末與平日的落差，月平均把它抹平了。")

# ══ 09 聚落財務結構 ══════════════════════════════════════════
s = head(S(), "PART II · 聚落結構",
         f"度假型住房率低 {SEA['urban_mean_w']-SEA['resort_mean_w']:.0f} pp，RevPAR 反而高 NT${SEA['resort_revpar_w']-SEA['urban_revpar_w']:,.0f} —— 「低周轉、高房價」是另一種賺法",
         "RevPAR = 住房率 × 房價，把「量」和「價」合成一個可比的收益指標，跨模式比較才公平。")
chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED, ["平均房價 ADR", "每可售房收益 RevPAR"],
      [("都會商務聚落", [SEA["urban_adr_w"], SEA["urban_revpar_w"]]),
       ("風景度假聚落", [SEA["resort_adr_w"], SEA["resort_revpar_w"]])],
      0.62, 1.96, 6.7, 3.85, colors=[BLUE, AMBER], numfmt='#,##0', gap=80)
text(s, "加權口徑，單位 NT$", 0.80, 5.81, 4.0, 0.24, 11, T_FAINT)
pcard(s, 7.55, 1.96, 5.17, "怎麼讀", [
    f"度假 ADR 高 {SEA['resort_adr_w']/SEA['urban_adr_w']-1:+.0%}、住房率低 {SEA['resort_mean_w']/SEA['urban_mean_w']-1:+.0%}，"
    f"兩者相乘 RevPAR 淨高 {SEA['resort_revpar_w']/SEA['urban_revpar_w']-1:+.0%}（≈ NT${SEA['resort_revpar_w']-SEA['urban_revpar_w']:,.0f}／房晚）。",
    "本圖只計客房收入；度假旅館的餐飲／宴會佔比通常較高，含全部營收差距會更大。",
    "住房率是「產能利用率」，不是「獲利指標」。",
], AMBER, h=3.0)
why(s, "風景度假縣市納入了目的地型高價旅館（日勝生加賀屋、涵碧樓、漢來日月行館），以「高房價、低周轉」經營；"
       "都會商務型則是「低房價、高周轉」。兩種模式在 RevPAR 上不對稱。")
note(s, f"25 秒：度假型住房率比都會低約 {SEA['urban_mean_w']-SEA['resort_mean_w']:.0f} 個百分點，但房價高、RevPAR 也高。結論：跨模式比較要看 RevPAR。")

# ══ 10 縣市排行 ══════════════════════════════════════════════
s = head(S(), "PART II · 區域差異",
         "住房率最高的兩個縣市各只有 1–2 間旅館 —— 有規模又有代表性的是台北",
         f"看縣市排名前先看家數 —— 台北以 {CITY['n'][_ti]} 間、全台 {CITY['taipei_rev_share']}% 總營收，是唯一兼具規模與代表性的市場。")
_n = 12
chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED,
      [f"{c}\n({n} 間)" for c, n in zip(CITY["names"][:_n], CITY["n"][:_n])],
      [("加權住房率 (%)", CITY["occ_weighted"][:_n])],
      0.62, 1.96, 8.15, 3.75, colors=[BLUE], numfmt="0.0", gap=45, ymax=90, lbl_size=9)
text(s, "加權住房率，2023–2025 合計；括號為涵蓋觀光旅館家數", 0.80, 5.71, 7.6, 0.24, 11, T_FAINT)
pcard(s, 8.95, 1.96, 3.77, "怎麼讀", [
    f"台北 {CITY['occ_weighted'][_ti]}%、{CITY['n'][_ti]} 間：旅館數最多、佔全台營收一半，是基準市場。",
    f"桃園 {CITY['occ_weighted'][_tyi]}%、{CITY['n'][_tyi]} 間：台北以外第一個「大樣本又排前段」的縣市 —— 前段名次不全是小樣本造成的。",
    f"花蓮 {CITY['occ_weighted'][_hli]}%：觀光大縣卻墊底，0403 地震後兩年跌 {CITY['hualien_drop_pp']} pp。",
], BLUE, h=3.0)
why(s, "剔掉家數不足 3 間的縣市後，剩下的呈「北部與台南居前、東部（花蓮、台東）居後」的穩定格局 —— "
       "這個區域差距才是可用的訊號。")
note(s, f"25 秒：排行冠亞軍基隆、新竹市各只有 1–2 間，數字等於單一旅館。看家數足夠的縣市，"
       f"台北（{CITY['occ_weighted'][_ti]}%、{CITY['n'][_ti]} 間、佔全台營收一半）與桃園居前、"
       f"東部的花蓮（{CITY['occ_weighted'][_hli]}%，0403 地震後兩年跌 {CITY['hualien_drop_pp']} pp）與台東居後 —— "
       f"這個北高東低的區域差距才是穩定訊號。")

# ══ 11 客源結構 ══════════════════════════════════════════════
s = head(S(), "PART II · 客源結構",
         f"國際旅客三年 +{GU['intl_delta_pp']} pp、站上 {GU['intl_ratio'][-1]}%——日本是最大成長來源",
         f"客源結構沒有跟著國際化改變：散客比例三年穩定在 {GU['fit_ratio'][-1]}% —— "
         "OTA 收益管理與數位評價才是飯店競爭的主戰場，不是低價團客。")
chart(s, XL_CHART_TYPE.COLUMN_STACKED, YRS,
      [("本國旅客", GU["dom_ratio"]), ("國際旅客", GU["intl_ratio"])],
      0.62, 1.96, 5.35, 3.85, colors=[GREY, BLUE], numfmt="0.0", gap=110, overlap=100, ymax=100)
text(s, "住客人次結構 (%)，加權", 0.80, 5.81, 4.0, 0.24, 11, T_FAINT)
chart(s, XL_CHART_TYPE.LINE_MARKERS, YRS,
      [("日本", GU["japan_wan"]), ("美國", GU["usa_wan"]), ("韓國", GU["korea_wan"]), ("港澳", GU["hkmo_wan"])],
      6.55, 1.96, 6.05, 3.85, colors=[RED, BLUE, TEAL, AMBER], numfmt="0.0", ymin=20)
text(s, "主要外籍客源住客人次（萬人次）", 6.73, 5.81, 5.0, 0.24, 11, T_FAINT)
why(s, "國際佔比回升填平了都會飯店平日的空房；港澳是唯一衰退的客源。"
       "數字為「旅館住客人次」，同一旅客多晚會重複計，遠大於移民署入境人數。")
note(s, "30 秒：國際旅客從 34% 回到 40.7%。日本從 76 萬漲到 111 萬。散客團客三年都是 77:23。"
        "所以主戰場是 OTA 跟數位評價。")

# ══ 12 星等階梯 ══════════════════════════════════════════════
s = head(S(), "PART III · 星等效益",
         f"五星每房收益是三星 {ST['revpar_5_over_3']} 倍，八成差距來自房價、不是住房率",
         "提升 RevPAR 的槓桿是「撐得起更高的房價定位」，把房間填滿的空間有限。")
_rows = [["星等", "家數", "加權住房率", "平均房價 ADR", "每房收益 RevPAR", "營收佔比"]]
for i, nm in enumerate(ST["names"]):
    _rows.append([nm, f"{ST['n'][i]} 間", f"{ST['occ'][i]}%", f"NT$ {ST['adr'][i]:,.0f}",
                  f"NT$ {ST['revpar'][i]:,.0f}", f"{ST['rev_share'][i]}%"])
table(s, _rows, 0.62, 1.98, 8.15, 2.55, widths=[1.5, 0.8, 1.15, 1.3, 1.35, 1.0], fs=11)
pcard(s, 8.95, 1.98, 3.77, "拆解", [
    f"五星對三星：住房率只高 {ST['occ'][1] - ST['occ'][3]:.1f} pp。",
    f"五星對三星：ADR 高 {ST['adr_5_over_3']} 倍 ← 主要動力。",
    f"RevPAR＝住房率 × ADR，同向相乘 → 差距放大成 {ST['revpar_5_over_3']} 倍。",
    f"五星級 {ST['n'][1]} 間即佔客房營收 {ST['five_rev_share']}%。",
    f"無星等組 ADR（NT${ST['adr'][4]:,.0f}）反高於三星級（NT${ST['adr'][3]:,.0f}）——"
    "組內混了未評鑑的高價旅館，不是單純『沒星等＝差』。",
], PURPLE, h=4.05)
why(s, f"各星等的住房率天花板有限（都在 {min(ST['occ'])}–{max(ST['occ'])}% 之間）；"
       "真正決定 RevPAR 高低的是房價定位。卓越五星僅 1 間，不宜當類別比較；"
       "無星等組同樣不宜視為『墊底』——組內混了高價精品旅館，把 ADR 拉高。", y=6.07)
note(s, "35 秒：RevPAR 等於住房率乘房價，五星房價高 1.98 倍、住房率又高 8.9 pp，兩者相乘放大成 2.29 倍。"
        "無星等組 ADR 反而比三星級高——不是乾淨的階梯，講的時候順便帶到。")

# ══ 13 星等 RevPAR 三視角 ════════════════════════════════════
s = head(S(), "PART III · 星等效益",
         "無星等的房價長條反而比三星級高——三張圖一次看懂異常在哪",
         "跟第 12 頁的表格對照著看：階梯在五星以下大致成立，無星等組是唯一反過來的例外。")
chart(s, XL_CHART_TYPE.BAR_CLUSTERED, list(reversed(ST["names"])),
      [("每可售房收益 RevPAR (NT$)", list(reversed(ST["revpar"])))],
      0.62, 1.96, 6.25, 3.85, colors=[BLUE], numfmt='#,##0', gap=55, panel_pad=0.05)
text(s, "加權 RevPAR＝Σ客房營收 ÷ Σ可售房晚", 0.80, 5.81, 5.0, 0.24, 11, T_FAINT)
chart(s, XL_CHART_TYPE.BAR_CLUSTERED, list(reversed(ST["names"])),
      [("加權住房率 (%)", list(reversed(ST["occ"])))],
      7.22, 1.96, 5.5, 1.85, colors=[TEAL], numfmt="0.0", gap=45, lbl_size=9, panel_pad=0.05)
text(s, f"住房率：五星對三星僅差 {ST['occ'][1] - ST['occ'][3]:.1f} pp", 7.40, 3.86, 5.0, 0.24, 11, T_FAINT)
chart(s, XL_CHART_TYPE.BAR_CLUSTERED, list(reversed(ST["names"])),
      [("平均房價 ADR (NT$)", list(reversed(ST["adr"])))],
      7.22, 4.15, 5.5, 1.70, colors=[AMBER], numfmt='#,##0', gap=45, lbl_size=9, panel_pad=0.05)
text(s, f"房價：五星對三星 {ST['adr_5_over_3']} 倍；無星等反超三星", 7.40, 5.81, 5.0, 0.24, 11, T_FAINT)
why(s, f"三張圖對照著看：住房率階梯平緩（{ST['occ'][1] - ST['occ'][3]:.1f} pp）、房價階梯陡（{ST['adr_5_over_3']} 倍）——"
       f"但房價圖最後一根，無星等（NT${ST['adr'][4]:,.0f}）反超三星（NT${ST['adr'][3]:,.0f}），是組成異質造成的，跟第 12 頁一致。",
       y=6.14)
note(s, "25 秒：三張圖對照著看，住房率階梯平緩、房價階梯陡。但看房價那張圖最後一根——"
        "無星等反而比三星高，是組成異質造成的，第 12 頁拆解卡已經解釋過。")

# ══ 14 選擇偏誤 ══════════════════════════════════════════════
s = head(S(), "PART III · 科學邊界",
         f"星等溢價控制混淆後仍有約 {SO['controlled_pp']:.0f} pp —— 是穩健關聯，不是已證實的因果",
         "星等和住房率的關聯經得起控制檢驗，但因果方向未定 —— 別急著當成「摘星必賺」的行銷保證。")
x, y, w = card(s, 0.62, 1.96, 5.95, 3.9, "表象：巨大但危險的差距", AMBER)
rich(s, [("住房率　", f"有星等 {SG['occ_simple']['star']:.1f}%、無星等 {SG['occ_simple']['nostar']:.1f}%，差 {SG['occ_simple']['gap_pp']} pp。", AMBER),
         ("房價　", f"加權 ADR：有星等 NT${SG['adr_weighted']['star']:,.0f}、無星等 NT${SG['adr_weighted']['nostar']:,.0f}（+{SG['adr_weighted']['gap_pct']}%）。", AMBER),
         ("口徑提醒　", f"同一差距在加權下縮為 {SG['occ_weighted']['gap_pp']} pp —— 量級會隨口徑改變。", AMBER)],
     x, y, w, 3.0, 10.5)
x, y, w = card(s, 6.77, 1.96, 5.95, 3.9, "控制後仍有 12 pp", RED)
rich(s, [("有測的　", f"控制縣市、房數、月份、客源後，溢價從 {SO['raw_gap_pp']} pp 只降到 {SO['controlled_pp']} pp —— 看得到的條件解釋不了大半。", RED),
         ("沒測的　", "品牌形象、服務品質、行銷預算等看不到的因素，仍可能跟星等綁在一起。", RED),
         ("不精確　", f"樣本僅 {SO['n_hotels']} 家，依旅館 cluster 的 95% 信賴區間達 {SO['ci_lo']}–{SO['ci_hi']} pp，範圍很寬。", RED),
         ("本專案立場　", "星等是「穩健關聯、強預測特徵」，不是「已證實的因果槓桿」；報告一律用「相關」不用「造成」。", RED)],
     x, y, w, 3.0, 10.5)
text(s, f"＊左卡 {SG['occ_simple']['gap_pp']} pp 為全樣本（{SC['rows_hist']:,} 筆）差距；"
        f"右卡 {SO['raw_gap_pp']}→{SO['controlled_pp']} pp 為迴歸可用樣本（{SO['n_rows']:,} 筆，缺值行已剔除）"
        "—— 定義相同，樣本略有出入。", 0.62, 6.0, 12.1, 0.4, 10.5, T_FAINT)
note(s, f"40 秒：左邊承認差距很大、也標了口徑。右邊是補跑的 OLS：控制混淆後溢價只從 {SO['raw_gap_pp']} pp 降到 "
        f"{SO['controlled_pp']} pp，代表這不是純選擇偏誤，但樣本小、信賴區間寬，仍不能說是已證實的因果。")

# ══ 15 房價 + 規模非線性 ════════════════════════════════════
s = head(S(), "PART III · 結構特徵",
         "最低價組住房率明顯落後、規模越大房價不一定越高 —— 兩個結構都是非線性的",
         "這是跨旅館的橫斷面分組，不是同一間旅館調價前後的比較——房價、規模都無法線性外推住房率，這正是選用樹模型而非線性迴歸的理由。")
chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED, PB["labels"],
      [("住房率 (%)", PB["occ"])],
      0.62, 1.98, 6.15, 3.7, colors=[BLUE], numfmt="0.0", gap=35, ymax=72, lbl_size=8)
text(s, f"房價 8 分位；最低價組 {PB['worst_occ']}% 斷崖，第 2～8 組全在 {PB['plateau_min']}–{PB['plateau_max']}% 窄帶 → 非倒 U",
     0.80, 5.75, 6.2, 0.4, 11, T_FAINT, spacing=1.15)
chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED,
      [f"{lb}\n({n} 間)" for lb, n in zip(RB["labels"], RB["hotels"])],
      [("住房率 (%)", RB["occ_simple"])],
      7.22, 1.98, 5.4, 3.7, colors=[TEAL], numfmt="0.0", gap=55, ymax=78, lbl_size=8)
text(s, f"住房率隨規模升（{RB['occ_simple'][0]}%→{RB['occ_simple'][-1]}%），但加權 ADR 呈 U 型——最小組"
        f" NT${RB['adr_weighted'][0]:,.0f} 最高（混入高價度假旅館）", 7.40, 5.75, 5.3, 0.4, 11, T_FAINT, spacing=1.15)
why(s, "房價分組唯一的斷點在最低價那組，其餘七組幾乎打平——這種形狀線性迴歸只能畫一條斜線，抓不到斷點。"
       "小型規模組（<80 間）內部也極度異質，同樣抓不到。", y=6.14)
note(s, "30 秒：左圖房價八等分——第一組 41.8% 斷崖，其餘持平。右圖規模——住房率單向升，但 ADR 是 U 型。")

# ══ 16 陸客體制斷裂 ══════════════════════════════════════════
_cv_path = _HERE.parent / "data" / "processed" / "china_visitors_annual.csv"
with open(_cv_path, encoding="utf-8-sig") as _fh:
    _cv = [[int(rr["年"]), float(rr["中國大陸來臺旅客萬人次"])] for rr in _csv.DictReader(_fh)]
s = head(S(), "PART III · 範圍界定",
         "陸客量已從 418 萬崩到 30 萬——模型只從 2023 年訓練，是刻意的範圍設定",
         "把 2019 年以前納入訓練，模型會學到一個「陸客佔外籍三成」但不會再現的結構。這是範圍設定，不是資料不足。",
         src="資料來源：交通部觀光署《來臺旅客統計》；2024–2025 為估計值")
chart(s, XL_CHART_TYPE.LINE_MARKERS, [f"{y}" for y, _ in _cv],
      [("中國大陸來臺旅客（萬人次）", [v for _, v in _cv])],
      0.62, 1.98, 8.05, 3.7, colors=[RED], numfmt="0", ymax=460, lbl_size=8)
text(s, "灰底區間為 2020–2022 邊境對境外旅客關閉期", 0.80, 5.68, 6.0, 0.24, 11, T_FAINT)
pcard(s, 8.87, 1.98, 3.85, "四段體制", [
    "2011–2015：開放陸客，衝到 418 萬人次高峰。",
    "2016–2019：管制趨嚴，回落至約 270 萬。",
    "2020–2022：邊境關閉，歸零（0.9–11.1 萬）。",
    "2023–2025：僅商務／轉機的新體制，22→30 萬——這才是模型訓練的區間。",
], RED, h=3.5)
why(s, "此圖同時是儀表板「住客國籍與客源結構分析」分頁的一張圖；報告中作為「為何模型只從 2023 年訓練」的視覺後盾。")
note(s, "30 秒：回答必問題——為什麼不用更長的歷史資料。陸客 2015 高峰 418 萬，2020 邊境一關直接歸零。"
        "把起點設在 2023 是刻意讓訓練跟預測在同一個體制內。")

# ══ 17 驗證設計（防洩漏 + 特徵工程）══════════════════════════
s = head(S(), "PART IV · 驗證設計",
         "訓練／驗證選模／盲測三段切開，選模全程不碰 2026 上半年",
         f"時間序列若用隨機 K-Fold，等於用未來預測過去；選模若偷看盲測，回報值會偏樂觀 —— 這兩步做錯，後面的 {M['best']['mae']} 就沒有意義。")
_steps = [
    ("三段時間切分", BLUE,
     f"訓練 {M['train_period']}（{M['train_rows']:,} 筆）→ 驗證選模 {M['val_period']}（{M['val_rows']:,} 筆）→ "
     f"盲測 {M['test_period']}（{M['test_rows']} 筆，只算一次）；選模全程未碰盲測資料。"),
    ("Pipeline 封裝", CYAN, "SimpleImputer(median) + StandardScaler + OneHotEncoder，三者封裝於 Pipeline、僅以訓練集 fit。"),
    ("特徵僅取 t-1 以前", TEAL, "occupancy_lag_1/2/3/12、roll3 均由 groupby(旅館).shift() 產生；預測當期時所有特徵皆已公布。"),
    ("雙軌回測", PURPLE, "滾動一個月：每月餵入真實上月值；固定起點六個月：遞迴餵入自己的預測（反映多月衰減）。"),
]
for i, (nm, c, body) in enumerate(_steps):
    l = 0.62 + (i % 2) * 6.15
    t = 1.98 + (i // 2) * 2.10
    rect(s, l, t, 5.98, 1.88, CARD, BORDER)
    text(s, nm, l + 0.24, t + 0.16, 5.5, 0.3, 13, T_TITLE, bold=True)
    rect(s, l + 0.24, t + 0.48, 0.30, 0.026, c, shape=MSO_SHAPE.RECTANGLE)
    text(s, body, l + 0.24, t + 0.62, 5.5, 1.2, 11.5, T_BODY, spacing=1.24)
why(s, "「不納入當期資訊」是底線：預測 2026-06 時，只能用 2026-05 及更早已公布的數值 —— "
       "當月房價、當月旅客結構一律不可作為特徵。", y=6.14)
note(s, "35 秒：時間序列最常見的作弊就是隨機切 K-Fold，那等於用未來預測過去。我用時間外驗證。")

# ══ 18 多基準對照（效益證明）════════════════════════════════
s = head(S(), "PART IV · 模型效益",
         f"只依賴旅館自己的歷史資訊，次月住房率平均誤差 {M['best']['mae']} 個百分點 —— 勝過所有簡單方法",
         "第 1 個月的數字能支援促銷時機、OTA 房量與排班等戰術決策。")
chart(s, XL_CHART_TYPE.BAR_CLUSTERED,
      list(reversed([rr["name"] for rr in BL["rows"]])),
      [("2026 上半年 MAE（住房率百分點，越低越好）", list(reversed([rr["mae"] for rr in BL["rows"]])))],
      0.62, 1.98, 7.6, 3.7, colors=[BLUE], numfmt="0.00", gap=55, ymax=9)
text(s, "同一份 2026 上半年盲測資料；MAE = 平均每次預測差幾個百分點", 0.80, 5.68, 7.2, 0.24, 11, T_FAINT)
pcard(s, 8.45, 1.98, 4.27, "這張表證明什麼", [
    f"最好的簡單方法是「照抄上月」（MAE {BL['rows'][0]['mae']}）；「近 3 個月平均」次之（{BL['rows'][2]['mae']}）；「去年同月」最差（{BL['rows'][1]['mae']}）。",
    f"Gradient Boosting MAE {M['best']['mae']}，比最好的簡單方法再好 {BL['beats_best_baseline_pp']} pp（{BL['beats_best_baseline_pct']}%）。",
    f"預測值幾乎不偏（Bias {M['best']['bias']:+.2f} pp），R² {M['best']['r2']:.3f}。",
    "商業翻譯：預測某旅館住房率 70%，平均會差 6 個百分點左右——不是逐一精準命中的預測，是抓方向、抓量級。",
], BLUE, h=3.7)
why(s, f"GB 同時用了短期慣性（前 1 / 近 3 月）、年度季節（去年同月）與地理／星等 —— "
       f"任何「單一規則」都只抓到其中一塊，所以合起來會更準；1,000 次旅館分群拔靴法顯示改善幅度的 95% 信賴區間為 "
       f"[{M['improve_ci_lo']}, {M['improve_ci_hi']}] pp，不是碰巧贏一次。")
note(s, f"40 秒——這是老師說的『有效益的東西』。GB 跟三種簡單方法放同一張表比，再好 {BL['beats_best_baseline_pct']}%，"
        f"而且是在完全沒參與訓練與選模的 2026 上半年測的。")

# ══ 19 模型對決（候選表）════════════════════════════════════
s = head(S(), "PART IV · 模型比較",
         "四款候選模型在 2025 驗證集上競賽，Gradient Boosting 勝出",
         f"候選比較全程只用驗證集（{M['val_period']}），2026 上半年盲測資料在選模、調參階段完全未參與。")
_order = ["Gradient Boosting", "Random Forest", "Ridge", "Baseline (前月住房率)"]
_cm = {c["name"]: c for c in M["candidates"]}
_rf_gap = round(_cm["Random Forest"]["mae"] - _cm["Gradient Boosting"]["mae"], 2)
_verdict = {"Gradient Boosting": "★ 採用", "Random Forest": f"次優，差 {_rf_gap} pp",
            "Ridge": "線性假設不足", "Baseline (前月住房率)": "比較基準"}
_rows = [["候選模型（2025 驗證集）", "MAE (pp)", "RMSE", "R²", "Bias (pp)", "評定"]]
for nm in _order:
    c = _cm[nm]
    _rows.append([nm.replace(" (前月住房率)", "（前月住房率）"), f"{c['mae']}", f"{c['rmse']}",
                  f"{c['r2']:.3f}", f"{c['bias']:+.2f}", _verdict[nm]])
table(s, _rows, 0.62, 1.98, 7.95, 2.35, widths=[2.3, 0.9, 0.85, 0.85, 0.95, 1.4], fs=11)
chart(s, XL_CHART_TYPE.BAR_CLUSTERED,
      list(reversed([n.replace(" (前月住房率)", "") for n in _order])),
      [("2025 驗證集 MAE（越低越好）", list(reversed([_cm[n]["mae"] for n in _order])))],
      0.62, 4.55, 7.95, 2.2, colors=[BLUE], numfmt="0.00", gap=55, ymax=8.5)
pcard(s, 8.78, 1.98, 3.94, "四個指標怎麼讀", [
    "MAE：平均差幾個百分點，最貼近「準不準」的直覺。",
    "RMSE：對大誤差加重處罰，評估最壞情況。",
    f"R²：模型抓住了多少住房率的變化規律，越接近 100% 越準；GB 盲測 R² 是 {M['best']['r2'] * 100:.1f}%。",
    f"選定 GB 後以 2023–2025 全量重新訓練，2026 上半年盲測 MAE {M['best']['mae']}（見上一頁），Bias {M['best']['bias']:+.2f} pp。",
], BLUE, h=3.7)
note(s, f"30 秒：驗證集上 GB MAE {_cm['Gradient Boosting']['mae']}，比基準好；RF 只差 {_rf_gap}，我誠實標註。"
        f"選定後重訓、盲測 MAE {M['best']['mae']}，跟驗證集表現一致，沒有跳動。")

# ══ 20 期程衰減 ══════════════════════════════════════════════
s = head(S(), "PART IV · 期程衰減",
         f"第 1 個月的預測能用，第 6 個月別用 —— 誤差從 {M['horizons'][0]['mae']} 擴大到 {M['horizons'][-1]['mae']}、且不單調",
         "每月官方月報公布後重跑模型，決策只採用「第 1 個月」的預測。")
_hs = [f"第 {h['h']} 個月" for h in M["horizons"]]
chart(s, XL_CHART_TYPE.LINE_MARKERS, _hs,
      [("MAE (pp)", [h["mae"] for h in M["horizons"]]), ("RMSE", [h["rmse"] for h in M["horizons"]])],
      0.62, 1.98, 7.3, 3.7, colors=[BLUE, AMBER], numfmt="0.00", ymin=4)
text(s, "固定起點遞迴回測，2026-01 為起點", 0.80, 5.68, 6.0, 0.24, 11, T_FAINT)
pcard(s, 8.15, 1.98, 4.57, "三個誠實的觀察", [
    f"整體擴大：MAE 第 1 個月 {M['horizons'][0]['mae']} → 第 6 個月 {M['horizons'][-1]['mae']}，"
    f"R² {M['horizons'][0]['r2']:.2f} → {M['horizons'][-1]['r2']:.2f}（R² 出自同一批回測，圖上未畫）。",
    f"但不單調：第 3、4 個月（{M['horizons'][2]['mae']}、{M['horizons'][3]['mae']}）反而優於第 2 個月 —— 每期僅 115 筆，是噪聲。",
    f"六個月整體 MAE {M['fixed_overall']['mae']}，已接近「照抄上月」的 {M['baseline_mae']}。",
], AMBER, h=3.7)
why(s, "第 2 個月起，模型改用「自己上個月的預測」當輸入，誤差在遞迴中被自己放大 —— 這是整體趨勢往上的原因；"
       "月與月之間的小起伏（如第 3、4 個月）則是樣本噪聲，兩者不衝突。")
note(s, "30 秒：不美化。整體誤差擴大，但第三、四個月反而比第二個月好——它不是平滑曲線，是噪聲。")

# ══ 21 特徵重要性 ════════════════════════════════════════════
_nm_map = {"occupancy_lag_1": "前 1 月住房率", "occupancy_roll3": "近 3 月均值",
           "occupancy_lag_12": "去年同月", "month": "月份", "month_sin": "月份循環",
           "occupancy_lag_2": "前 2 月住房率", "input_domestic_ratio": "本國客佔比",
           "input_international_ratio": "國際客佔比", "input_employees": "員工數",
           "city": "縣市", "input_total_rooms": "客房數"}
s = head(S(), "PART IV · 模型本質",
         f"打亂前 1 月住房率，MAE 惡化 {PI['mae_increase'][0]} pp —— 它是預警雷達，不是因果搖桿",
         "置換重要性：把某特徵的值打亂重測，MAE 惡化越多代表模型越依賴它；比內建重要度更能回答「拿掉會怎樣」。")
chart(s, XL_CHART_TYPE.BAR_CLUSTERED,
      list(reversed([_nm_map.get(n, n) for n in PI["names"]])),
      [("打亂後 MAE 惡化 (pp)", list(reversed(PI["mae_increase"])))],
      0.62, 1.98, 7.0, 3.9, colors=[PURPLE], numfmt="0.00", gap=45)
text(s, "來源：reports/permutation_importance_monthly_3way.csv（2025 驗證集、8 次重複取平均）", 0.80, 5.90, 6.8, 0.24, 11, T_FAINT)
pcard(s, 7.85, 1.98, 4.87, "這代表什麼", [
    f"前 3 項打亂後 MAE 各惡化：前 1 月 +{PI['mae_increase'][0]} pp、近 3 月 +{PI['mae_increase'][1]} pp、去年同月 +{PI['mae_increase'][2]} pp。",
    f"房價、旅客結構、員工數全部打亂，MAE 合計只惡化 +{PI['ops_levers_mae_increase']} pp —— 調整它們，預測值幾乎不動。",
    "把國際客佔比拉高 10 pp、預測值變化微乎其微：這是模型結構的必然，不是 bug。",
    "它的價值：在官方數字出來前一個月，先給一個有根據的落點。",
], PURPLE, h=3.9)
note(s, f"35 秒：我把模型的弱點直接講出來。前三項全是住房率自己的歷史，打亂前 1 月就讓 MAE 惡化 {PI['mae_increase'][0]} pp，"
        f"是最大的單一因素（內建重要度口徑下佔 {FI['top3_sum']}%，兩種方法結論一致）。")

# ══ 22 穩健性 / 東部 ═════════════════════════════════════════
s = head(S(), "PART V · 穩健性",
         f"東部度假型的預測風險是都會型的 3 倍（台東 MAE {RO['by_city']['台東縣']['MAE']} vs 台中 {RO['by_city']['台中市']['MAE']}）",
         "東部旅館預測值標為低信賴；發生天災、交通中斷時停用模型輸出、改人工覆核。")
_cities = list(RO["by_city"].items())
chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED,
      [f"{c}\n({v['hotels']} 間)" for c, v in _cities],
      [("滾動一個月 MAE (pp)", [v["MAE"] for _, v in _cities])],
      0.62, 1.98, 8.15, 3.7, colors=[BLUE], numfmt="0.00", gap=45, ymax=15)
text(s, f"全體基準 MAE {RO['all']['MAE']} pp；僅列出盲測期間有觀測值的縣市", 0.80, 5.68, 7.8, 0.24, 11, T_FAINT)
pcard(s, 8.95, 1.98, 3.77, "邊界在哪", [
    f"樣本進出影響極小：三年皆在榜 {RO['present_all_three_years']} 間，MAE {RO['balanced']['MAE']}，與全體差 {RO['balanced_gap_pp']} pp。",
    f"真正的問題在東部：台東 {RO['by_city']['台東縣']['MAE']}（R² {RO['by_city']['台東縣']['R2']:.2f}）、"
    f"花蓮 {RO['by_city']['花蓮縣']['MAE']}（R² {RO['by_city']['花蓮縣']['R2']:.2f}，出自同一批回測，圖上未畫）。",
    f"{M['best']['mae']} 是平均：都會型約 {RO['by_city']['台中市']['MAE']}–{RO['by_city']['高雄市']['MAE']}、東部可達 {RO['by_city']['台東縣']['MAE']}。",
], RED, h=3.7)
why(s, f"地震、颱風造成的住房率斷點，是模型 {FI['top3_sum']}% 靠歷史慣性（見第 21 頁）抓不到的情況；"
       f"東部樣本雖小（各縣市僅 4 家），但這個落差不只是噪聲，是慣性模型的結構性限制。")
note(s, f"30 秒：三年都在榜的 MAE {RO['balanced']['MAE']}、跟全體差 {RO['balanced_gap_pp']}。"
        f"誤差在哪裡特別大？台東 {RO['by_city']['台東縣']['MAE']:.0f}、台中只有 {RO['by_city']['台中市']['MAE']:.0f}。")

# ══ 23 系統落地 + 後續規劃 ══════════════════════════════════
s = head(S(), "PART V · 系統與後續",
         "分析與模型都交付成 Streamlit 儀表板；後續五個方向已設計、尚未執行",
         "主體分析 5 個主題呈現歷史事實；儀表板只上線經過本專題驗證的月度預測；年度預測為早期版本，未列入本次報告範圍。")
pcard(s, 0.62, 1.96, 6.0, "app.py — 主體分析（5 主題）", [
    "整體營運與住房趨勢：年度指數、月份季節、縣市排行。",
    "個別旅館年度實績：營收、人力效率、逐月住房率、同儕比較。",
    "星級認證效益分析：住房率／ADR／RevPAR、有無星等分布。",
    "住客國籍與客源結構：本國 vs 國際、散客 vs 團體、客源回流。",
    "影響因素與特徵解析：房價／規模分箱、特徵重要性、盲測結果。",
], BLUE, h=3.9, size=11)
pcard(s, 6.72, 1.96, 6.0, "後續五個方向（已設計、未執行）", [
    "回補 2016–2019 月報，檢驗陸客體制轉換（門檻：三項指標都改善才替換模型）。",
    "整合連假與氣象外部特徵（官方日曆已實驗、未通過門檻）。",
    "客源國籍與餐飲／人效結構深鑽。",
    "次月預測落入歷史後 20% 分位時觸發自動告警。",
    "用月度模型遞迴預測取代獨立的年度 decision tree 模型，需先驗證第 7～12 個月的準確度。",
], AMBER, h=3.9, size=11)
why(s, "每日預測分頁目前不產出預測、僅顯示資料累積狀態 —— 寧可標「尚未就緒」，也不輸出無法驗證的數字。")
note(s, "25 秒：主體分析五個主題都是歷史事實。後續五個方向是規劃、不是成果，我會講清楚。")

# ══ 24 方法誠信與限制 ═══════════════════════════════════════
s = head(S(), "PART VI · 方法誠信",
         "為什麼可以相信前面的每一個數字 —— 以及主動揭露的弱點",
         "資料分析的可信度來自「驗證方式」與「可重現」，不是結論好不好看。")
_m = [
    ("可信的地方", TEAL, [
        "三段時間切分做時間外驗證，不是隨機 K-Fold；選模全程未碰 2026 盲測資料，特徵僅取 t-1 以前。",
        "涉及住房率的圖都標明統計口徑（加權 / 簡單平均）。",
        "數字全部由 compute_facts.py 自原始資料與模型報表計算。",
        "涉及推論的宣稱（如星等效應、模型改善幅度）附 cluster bootstrap 信賴區間，不只給單一數字。",
    ]),
    ("主動揭露的弱點", RED, [
        f"選模訓練只用 {M['train_rows']:,} 筆（{M['train_period']}），比舊版一次切分少約一年；"
        f"重訓後盲測 MAE（{M['best']['mae']}）與舊版（6.08）幾乎相同，可信度提升沒有明顯犧牲準確度。",
        "資料僅 2023 年起：陸客體制斷裂，硬納入會汙染訓練訊號。",
        "「都會／度假」為人工縣市分類；星等以現行認證回填全期間。",
        "SARIMA／Prophet、分群子模型均為未來工作（外部特徵已在系統頁具體規劃，見第 23 頁）。",
    ]),
]
for i, (nm, c, its) in enumerate(_m):
    l = 0.62 + i * 6.15
    rect(s, l, 1.98, 5.98, 4.35, CARD, BORDER)
    text(s, nm, l + 0.26, 2.16, 5.5, 0.3, 13.5, T_TITLE, bold=True)
    rect(s, l + 0.26, 2.50, 0.32, 0.026, c, shape=MSO_SHAPE.RECTANGLE)
    rich(s, [("· ", x, c) for x in its], l + 0.26, 2.68, 5.4, 3.4, 11.5, 1.26, 8)
note(s, "30 秒：這頁回答『憑什麼相信』。左邊是可信的地方，右邊是我自己揭露的弱點。")

# ══ 25 總結 ══════════════════════════════════════════════════
s = S()
PAGE["n"] = 25
bg_fill(s, BG)
text(s, "總結", 0.62, 0.30, 7.0, 0.24, 11, BLUE, bold=True)
rect(s, 0.62, 0.555, 0.46, 0.030, BLUE, shape=MSO_SHAPE.RECTANGLE)
text(s, "三個結論，對誰有用", 0.60, 0.64, 12.4, 0.56, 24, T_TITLE, bold=True)
_sum = [
    ("復甦是量增不是漲價", TEAL, f"住房率指數 {IDX['occ'][-1]}、ADR {IDX['adr'][-1]}",
     "收益管理：下一輪成長靠拉價，不是再衝住房率。"),
    ("次月預測平均誤差約 6 pp", BLUE, f"MAE {M['best']['mae']}，勝 3 種簡單基準 {BL['beats_best_baseline_pct']}%",
     "戰術決策：第 1 個月的預測可進促銷時機、OTA 房量與排班；第 6 個月只作趨勢參考。"),
    ("是預警雷達不是因果搖桿", AMBER, f"{FI['top3_sum']}% 靠慣性、東部誤差 3 倍",
     "風險 SOP：東部旅館與天災期間改人工覆核。"),
]
for i, (t_, c, kpi_, use) in enumerate(_sum):
    yy = 1.58 + i * 1.34
    rect(s, 0.62, yy, 12.1, 1.16, CARD, BORDER)
    rect(s, 0.62, yy, 0.055, 1.16, c, shape=MSO_SHAPE.RECTANGLE)
    text(s, f"結論 {i + 1}　{t_}", 0.92, yy + 0.17, 6.4, 0.3, 13.5, T_TITLE, bold=True)
    text(s, kpi_, 0.92, yy + 0.58, 6.4, 0.3, 10.5, c, bold=True)
    text(s, use, 7.15, yy, 5.35, 1.16, 11.5, T_BODY, spacing=1.25, anchor=MSO_ANCHOR.MIDDLE)
rect(s, 0.62, 6.02, 12.1, 0.66, CARD, BORDER)
text(s, "資料來源", 0.9, 6.10, 2.0, 0.24, 10, T_TITLE, bold=True)
text(s, "觀光署《觀光旅館營運統計》逐月報表 2023-01～2026-06　|　《來臺旅客統計》　|　"
        "人事行政總處辦公日曆（假日特徵實驗、未採用）",
     2.4, 6.10, 10.1, 0.48, 8.5, T_MUTED, spacing=1.25)
text(s, "Q & A　　儀表板 taiwan-hotel-occupancy.streamlit.app　|　數字由 compute_facts.py 計算　|　感謝指教",
     0.62, 6.84, 12.1, 0.3, 10, BLUE, bold=True)
note(s, f"30 秒收尾：三個結論回顧。如果只記三件事：一，復甦是量增不是漲價；"
        f"二，次月預測誤差 {M['best']['mae']}、贏簡單方法 {BL['beats_best_baseline_pct']}%；三，它是預警雷達不是因果工具。謝謝，請指教。")

prs.save(OUT)
_nc = sum(1 for sl in prs.slides for sh in sl.shapes if sh.has_chart)
_nt = sum(1 for sl in prs.slides for sh in sl.shapes if sh.has_table)
print(f"[{STYLE}] 已產出：{OUT}")
print(f"投影片數：{len(prs.slides._sldIdLst)}　原生圖表：{_nc}　原生表格：{_nt}")
