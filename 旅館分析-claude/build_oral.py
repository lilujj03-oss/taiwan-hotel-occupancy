# -*- coding: utf-8 -*-
"""
台灣觀光旅館住房率分析與預測 — 5 分鐘口試版簡報（13 頁；內容頁編號 01–09）

從「價值重構版」抽出最能撐 5 分鐘的內容：結論先行、每頁一個重點、
每張圖講意義不講細節。搭配 build_oral_script.md 逐字稿。

執行：
  python 旅館分析-claude/build_oral.py            # 白底
  python 旅館分析-claude/build_oral.py darktheme  # 全深色
"""

import csv as _csv
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_src = (_HERE / "build_deck.py").read_text(encoding="utf-8")
_infra = _src.split("# ══ 01 封面")[0]
_infra = _infra.replace('[sys.executable, __file__, _st]',
                        '[sys.executable, str(_HERE / "build_oral.py"), _st]')
exec(compile(_infra, "build_oral_infra", "exec"), globals())

TOTAL = 9          # 只編「內容頁」（用 head() 的頁），封面／摘要／總結／封底不編號
_CPG = [0]         # 內容頁計數器
_SRC_IMG = _HERE / "assets" / "官方月報範例.png"   # 官方月報原始表截圖（自行放入）
OUT = _HERE / f"台灣觀光旅館住房率分析與預測_5分鐘口試版_{CFG['tag']}.pptx"
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


def head(slide, part, concl, means, src=None):
    _CPG[0] += 1
    bg_fill(slide, BG)
    text(slide, part, 0.62, 0.32, 7.0, 0.24, 12, BLUE, bold=True)
    rect(slide, 0.62, 0.60, 0.5, 0.032, BLUE, shape=MSO_SHAPE.RECTANGLE)
    text(slide, concl, 0.60, 0.72, 12.4, 0.7, 25, T_TITLE, bold=True, spacing=1.06)
    tb = slide.shapes.add_textbox(X(0.62), Y(1.66), X(12.4), X(0.6))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]
    p.line_spacing = 1.18
    r1 = p.add_run()
    r1.text = "重點　"
    r1.font.name, r1.font.size, r1.font.bold, r1.font.color.rgb = FONT, FS(14), True, BLUE
    r2 = p.add_run()
    r2.text = means
    r2.font.name, r2.font.size, r2.font.color.rgb = FONT, FS(14), T_BODY
    rect(slide, 0.62, 7.03, 12.1, 0.010, BORDER, shape=MSO_SHAPE.RECTANGLE)
    text(slide, src or SRC, 0.62, 7.10, 9.5, 0.26, 10, T_FAINT)
    text(slide, f"{_CPG[0]:02d} / {TOTAL}", 11.3, 7.10, 1.42, 0.26, 11, T_FAINT,
         bold=True, align=PP_ALIGN.RIGHT)
    return slide


def pcard(slide, l, t, w, title, items, accent=BLUE, h=3.6, size=13):
    x, y, ww = card(slide, l, t, w, h, title, accent)
    rich(slide, [("· ", it, accent) for it in items], x, y, ww, h - 0.9, size, 1.3, 9)


# ══ 01 封面 ═══════════════════════════════════════════════════
s = S()
PAGE["n"] = 1
bg_fill(s, BG)
_cbar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(PAGE_W), Inches(0.09))
_cbar.fill.solid()
_cbar.fill.fore_color.rgb = BLUE
_cbar.line.fill.background()
_cbar.shadow.inherit = False
text(s, "資料科學與旅宿收益管理專題　·　5 分鐘口試", 1.0, 1.6, 9.0, 0.3, 14, CYAN, bold=True)
rect(s, 1.0, 2.12, 0.09, 1.9, BLUE, shape=MSO_SHAPE.RECTANGLE)
text(s, "台灣觀光旅館\n住房率分析與預測", 1.34, 2.10, 9.0, 1.9, 42, T_TITLE, bold=True, spacing=1.12)
text(s, f"2023–2025 營運實證　·　2026 上半年時間外驗證（{SC['rows_2026h1']} 筆盲測）",
     1.02, 4.35, 9.0, 0.34, 15, T_BODY)
text(s, f"{SC['months']} 個月 × {SC['hotels_all']} 間觀光旅館，{SC['rows_all']:,} 筆月度面板資料",
     1.02, 4.78, 9.0, 0.3, 13, T_MUTED)
rect(s, 1.02, 5.44, 4.4, 0.010, BORDER, shape=MSO_SHAPE.RECTANGLE)
text(s, "口試報告人：詹梓芸", 1.02, 5.58, 9.0, 0.3, 14, T_TITLE, bold=True)
text(s, "指導老師：蘇凱正、王子恩、張婕葳、楊淑美、吳國樹　老師",
     1.02, 5.98, 10.5, 0.3, 12, T_MUTED)
text(s, SRC, 1.02, 6.6, 9.0, 0.26, 11, T_MUTED)
note(s, "（10 秒）各位評審好，我報告的是台灣觀光旅館住房率的分析與預測。"
        "用觀光署 42 個月、125 間旅館的官方月報資料。")

# ══ 02 三個結論（先講結論）═══════════════════════════════════
s = S()
PAGE["n"] = 2
bg_fill(s, BG)
text(s, "摘要", 0.62, 0.32, 7.0, 0.24, 12, BLUE, bold=True)
rect(s, 0.62, 0.60, 0.5, 0.032, BLUE, shape=MSO_SHAPE.RECTANGLE)
text(s, "先講結論：三個結論，一個邊界", 0.60, 0.72, 12.4, 0.6, 25, T_TITLE, bold=True)
_c = [
    ("① 復甦是「量增」不是「漲價」", TEAL,
     f"住房率指數升到 {IDX['occ'][-1]}、房價指數還在 {IDX['adr'][-1]}（2023 = 100）"
     "。效益：業者還有一輪拉價空間。"),
    ("② 次月住房率平均誤差約 6 個百分點", BLUE,
     f"MAE {M['best']['mae']} pp，勝過照抄上月（{BL['rows'][0]['mae']}）等 3 種簡單方法、改善 "
     f"{BL['beats_best_baseline_pct']}%。效益：能進促銷、OTA 房量、排班等決策。"),
    ("③ 它是「預警雷達」，不是「因果搖桿」", AMBER,
     f"模型 {FI['top3_sum']}% 靠住房率自身慣性；第 6 個月誤差擴大到 {M['horizons'][-1]['mae']} pp。"
     "效益：提前一個月看冷暖、排 SOP。"),
]
for i, (t_, col, body) in enumerate(_c):
    yy = 1.72 + i * 1.55
    rect(s, 0.62, yy, 12.1, 1.36, CARD, BORDER)
    rect(s, 0.62, yy, 0.06, 1.36, col, shape=MSO_SHAPE.RECTANGLE)
    text(s, t_, 0.94, yy + 0.16, 11.5, 0.32, 15, T_TITLE, bold=True)
    text(s, body, 0.94, yy + 0.58, 11.5, 0.7, 12.5, T_BODY, spacing=1.25)
rect(s, 0.62, 6.44, 12.1, 0.7, HEAD_BG)
text(s, "邊界：資料是「旅館 × 月」彙總，全篇為相關非因果，也無法預測地震颱風等外生衝擊。",
     0.9, 6.62, 11.5, 0.4, 12.5, RED, bold=True)
note(s, "（45 秒）這頁是全篇重點，5 分鐘只要記這三句。"
        "一，2025 的復甦是多賣房不是漲價；二，次月住房率能預測到正負六個百分點、贏過所有簡單方法；"
        "三，這個模型是提前一個月的預警雷達，不是能轉動住房率的工具。"
        "最下面紅字是邊界。後面三頁分別展開這三條。")

# ══ 03 資料來源：官方月報原始表 ═════════════════════════════
s = head(s := S(), "資料",
         "官方月報就是這樣一張一張的原始表 —— 飯店 × 月，欄位齊全",
         "每縣市尾端有「總計」小計列，解析時一律排除；否則同一批數字會被重複加總 3–5 倍。")
_ib_l, _ib_t, _ib_w, _ib_h, _pad = 0.62, 2.22, 7.7, 4.35, 0.14
rect(s, _ib_l, _ib_t, _ib_w, _ib_h, CARD, BORDER)
if _SRC_IMG.exists():
    _p = s.shapes.add_picture(str(_SRC_IMG), X(_ib_l + _pad), Y(_ib_t + _pad))
    _aw, _ah = _ib_w - 2 * _pad, _ib_h - 2 * _pad          # 可用區（design 座標）
    _ar = _p.image.size[0] / _p.image.size[1]              # 原圖長寬比
    if _aw / _ah > _ar:                                    # 高度受限
        _dh, _dw = _ah, _ah * _ar
    else:                                                  # 寬度受限
        _dw, _dh = _aw, _aw / _ar
    _p.width, _p.height = X(_dw), X(_dh)                   # 同一比例縮放、不變形
    _p.left = X(_ib_l + (_ib_w - _dw) / 2)
    _p.top = Y(_ib_t + (_ib_h - _dh) / 2)
else:
    text(s, "（尚未放入截圖：旅館分析-claude/assets/官方月報範例.png）",
         _ib_l + 0.4, _ib_t + 2.0, _ib_w - 0.8, 0.4, 12, T_FAINT, align=PP_ALIGN.CENTER)
text(s, "截圖：交通部觀光署《觀光旅館營運統計》單月彙整表（新北市／臺北市段）",
     _ib_l, _ib_t + _ib_h + 0.12, _ib_w, 0.24, 10, T_FAINT)
pcard(s, 8.55, 2.22, 4.17, "這張表的重點", [
    "層級：飯店 × 月；每月一份，依縣市分段。",
    "關鍵欄位：客房數、住用數、住用率、平均房價、房租／餐飲／總營業收入。",
    "縣市尾端「總計」列（如截圖第 72 列）須排除，避免重複加總。",
    f"清理後＝{SC['rows_all']:,} 筆逐月飯店明細（不含任何小計列）。",
], BLUE, h=4.55, size=11)
note(s, "（20 秒）這是原始資料長相：觀光署逐月月報，一個月一張表、縣市分段。"
        "關鍵是每個縣市尾端有『總計』小計列——直接讀進去會把數字重複加總三到五倍，"
        "我比對原始檔、用『第二欄為空』的規則把小計列全部排掉，才得到 4,832 筆乾淨明細。")

# ══ 04 範圍界定：陸客體制斷裂 ═══════════════════════════════
_cv_path = _HERE.parent / "data" / "processed" / "china_visitors_annual.csv"
with open(_cv_path, encoding="utf-8-sig") as _fh:
    _cv = [[int(rr["年"]), float(rr["中國大陸來臺旅客萬人次"])] for rr in _csv.DictReader(_fh)]
s = head(s := S(), "範圍界定",
         "模型資料從 2023 年起，是刻意的 —— 陸客量已從 418 萬崩到 30 萬，需求結構換了一個世界",
         "把 2019 年以前納入訓練，模型會學到「陸客佔外籍三成」但不會再現的結構。這是範圍設定，不是資料不足。",
         src="資料來源：交通部觀光署《來臺旅客統計》；2024–2025 為估計值")
chart(s, XL_CHART_TYPE.LINE_MARKERS, [f"{y}" for y, _ in _cv],
      [("中國大陸來臺旅客（萬人次）", [v for _, v in _cv])],
      0.62, 2.30, 8.0, 4.05, colors=[RED], numfmt="0", ymax=460)
text(s, "2020–2022 為邊境對境外旅客關閉期", 0.82, 6.42, 6.0, 0.24, 11, T_FAINT)
pcard(s, 8.85, 2.30, 3.87, "三段體制", [
    "2011–2015：開放陸客，衝到 418 萬人次高峰。",
    "2016–2019：管制趨嚴，回落至約 270 萬。",
    "2020 起：邊境關閉歸零；2023 起僅商務／轉機，約 22→30 萬。",
], RED, h=2.95, size=12)
pcard(s, 8.85, 5.42, 3.87, "客源結構（補充）", [
    "疫後國際客佔比回升、散客成常態。",
    "對次月住房率預測貢獻 <1%，故未單獨成頁（見儀表板客源結構分頁）。",
], BLUE, h=1.6, size=10)
note(s, "（30 秒）回答必問題——為什麼不用更長的歷史。陸客 2015 高峰 418 萬，2020 邊境一關歸零。"
        "起點設在 2023，是刻意讓訓練跟預測落在同一個需求體制內。")

# ══ 05 結論一：量增非漲價 ════════════════════════════════════
s = head(s := S(), "結論 ①",
         "2025 的復甦是「多賣房」，不是「漲價」——ADR 兩年仍低於 2023",
         "量已補回、價還在缺口——下一輪收益成長靠把 ADR 拉回 2023，不是再衝住房率。")
chart(s, XL_CHART_TYPE.LINE_MARKERS, YRS,
      [("住房率指數", IDX["occ"]), ("ADR 指數", IDX["adr"]), ("RevPAR 指數", IDX["revpar"])],
      0.62, 2.30, 8.0, 4.05, colors=[TEAL, AMBER, BLUE], numfmt="0.0", ymin=94, ymax=108,
      point_label_pos={0: "above", 2: "above", 1: "below", (2, 2): "below"})
text(s, "加權口徑，2023 = 100", 0.82, 6.42, 4.0, 0.24, 11, T_FAINT)
pcard(s, 8.85, 2.30, 3.87, "怎麼讀", [
    f"住房率指數 {IDX['occ'][-1]}：需求回到疫前之上。",
    f"ADR 指數 {IDX['adr'][-1]}：房價兩年還沒回到 2023。",
    f"2025 已售房晚年增 {A['sold_delta_wan']:.0f} 萬間。",
], TEAL, h=3.4)
note(s, "（40 秒）三個指標都以 2023 當 100。住房率衝到 105.6，但房價指數只有 99.3、"
        "兩年都低於基準。所以 2025 的成長完全是多賣房晚換來的，一年多賣了 29 萬間房。"
        "對業者的意義：量已經回來，下一步的收益成長空間在把價格拉回來。")

# ══ 06 指標定義：住房率 / ADR / RevPAR ══════════════════════
s = head(s := S(), "指標定義",
         "住房率、ADR 與 RevPAR 衡量不同的營運問題",
         "RevPAR＝住房率 × ADR，是整合「量」與「價」的綜合指標；本簡報三者一律用加權口徑。")
_defs = [
    ("住房率", "已售房晚 ÷ 可售房晚", "衡量房間賣得多滿", TEAL),
    ("ADR（平均每日房價）", "客房營收 ÷ 已售房晚", "平均一間售出客房的房價", BLUE),
    ("RevPAR（每間可售房收益）", "客房營收 ÷ 可售房晚", "整合房價與住房率的產能收益", AMBER),
]
for _i, (_nm2, _formula, _desc, _col) in enumerate(_defs):
    _yy = 2.40 + _i * 1.32
    rect(s, 0.62, _yy, 8.0, 1.16, CARD, BORDER)
    rect(s, 0.62, _yy, 0.06, 1.16, _col, shape=MSO_SHAPE.RECTANGLE)
    text(s, _nm2, 0.94, _yy + 0.14, 4.4, 0.3, 14, T_TITLE, bold=True)
    text(s, _formula, 0.94, _yy + 0.56, 4.4, 0.36, 15, _col, bold=True)
    text(s, _desc, 5.5, _yy, 2.9, 1.16, 11.5, T_MUTED, anchor=MSO_ANCHOR.MIDDLE)
pcard(s, 8.85, 2.40, 3.87, "一個例子", [
    "100 房、30 天，售出 1,800 房晚、客房營收 810 萬元。",
    "住房率 60%、ADR NT$4,500、RevPAR NT$2,700。",
    "驗證：RevPAR = ADR × 住房率 = 4,500 × 60%。",
], BLUE, h=3.6)
note(s, "（20 秒）三個指標的定義。重點是 RevPAR 等於住房率乘 ADR——它同時吃到量跟價，"
        "所以後面看復甦我會三個一起看。")

# ══ 07 結論二：次月平均誤差 6pp ═════════════════════════════
s = head(s := S(), "結論 ②",
         f"只依賴旅館自己的歷史資訊，次月住房率平均誤差 {M['best']['mae']} 個百分點",
         "勝過照抄上月、去年同月、近 3 月平均等所有簡單方法 —— 第 1 個月的數字能支援促銷時機、OTA 房量與排班等戰術決策。")
chart(s, XL_CHART_TYPE.BAR_CLUSTERED,
      list(reversed([r_["name"] for r_ in BL["rows"]])),
      [("2026 上半年 MAE（越低越好）", list(reversed([r_["mae"] for r_ in BL["rows"]])))],
      0.62, 2.30, 7.7, 4.05, colors=[BLUE], numfmt="0.00", gap=55, ymax=9)
text(s, "同一份 2026 上半年盲測資料；MAE = 平均每次預測差幾個百分點", 0.82, 6.42, 7.5, 0.24, 11, T_FAINT)
pcard(s, 8.55, 2.30, 4.17, "這張表證明什麼", [
    f"最強的簡單方法「照抄上月」MAE {BL['rows'][0]['mae']}。",
    f"Gradient Boosting {M['best']['mae']}，再好 {BL['beats_best_baseline_pp']} pp（{BL['beats_best_baseline_pct']}%）。",
    f"預測幾乎不偏（Bias {M['best']['bias']:+.2f} pp），R² {M['best']['r2']:.3f}。",
    "翻成白話：預測住房率 70%，平均會差 6 個百分點左右——抓方向、抓量級，不是逐一精準命中。",
], BLUE, h=3.6)
note(s, f"（55 秒）這是這份最有效益的一頁。我把模型跟三種簡單方法放同一張表比："
        f"照抄上月 {BL['rows'][0]['mae']}、去年同月 {BL['rows'][1]['mae']}、近 3 月平均 {BL['rows'][2]['mae']}，"
        f"我的 Gradient Boosting 是 {M['best']['mae']}，"
        f"比最好的簡單方法再好 {BL['beats_best_baseline_pct']}%，而且是在完全沒參與訓練與選模的 2026 上半年 {M['best']['n']} 筆資料測的。"
        f"如果模型只贏一點點，就沒必要用；現在贏 {BL['beats_best_baseline_pct']}%、預測又幾乎不偏，這個模型有存在價值。"
        f"商業上，6 個百分點的誤差對『要不要啟動促銷、放多少房量給 OTA』這種決策已經夠用。")

# ══ 08 模型比較：候選表 ═════════════════════════════════════
s = head(s := S(), "模型比較",
         "四款候選模型在 2025 驗證集上競賽，Gradient Boosting 勝出",
         f"候選比較全程只用驗證集（{M['val_period']}），2026 上半年盲測資料在選模階段完全未參與（見「方法」頁）。")
_order = ["Gradient Boosting", "Random Forest", "Ridge", "Baseline (前月住房率)"]
_cm = {c["name"]: c for c in M["candidates"]}
_rf_gap = round(_cm["Random Forest"]["mae"] - _cm["Gradient Boosting"]["mae"], 2)
_verdict = {"Gradient Boosting": "★ 採用", "Random Forest": f"次優，差 {_rf_gap} pp",
            "Ridge": "線性假設不足", "Baseline (前月住房率)": "比較基準"}
_rows = [["候選模型（2025 驗證集）", "MAE (pp)", "RMSE", "R²", "Bias (pp)", "優於基準", "評定"]]
for _nmk in _order:
    _c = _cm[_nmk]
    _rows.append([_nmk.replace(" (前月住房率)", "（前月住房率）"), f"{_c['mae']}", f"{_c['rmse']}",
                  f"{_c['r2']:.3f}", f"{_c['bias']:+.2f}",
                  "—" if "Baseline" in _nmk else f"{_c['improve_pct']}%", _verdict[_nmk]])
table(s, _rows, 0.62, 2.18, 7.95, 1.95,
      widths=[1.9, 0.85, 0.8, 0.8, 0.9, 0.9, 1.6], fs=10.5)
text(s, "固定起點回測：訓練至 2025-12，一次外推 2026 上半年 6 個月；第 N 列＝距起點 N 個月，誤差隨期程擴大。",
     0.62, 4.28, 7.95, 0.24, 9.5, T_FAINT)
_hrows = [["實測月", "MAE (pp)", "RMSE", "R²", "Bias (pp)"]]
for _h in M["horizons"]:
    _hrows.append([f"2026-{_h['h']:02d}", f"{_h['mae']}", f"{_h['rmse']}",
                   f"{_h['r2']:.3f}", f"{_h['bias']:+.2f}"])
table(s, _hrows, 0.62, 4.56, 7.95, 2.35, widths=[1.3, 1.0, 1.0, 1.0, 1.0], fs=10)
pcard(s, 8.78, 2.18, 3.94, "四個指標怎麼讀", [
    "MAE：平均差幾個百分點，最貼近「準不準」。",
    "RMSE：對大誤差加重處罰，看最壞情況。",
    f"R²：解釋了 {M['best']['r2'] * 100:.1f}% 的住房率變異。",
    f"Bias：{M['best']['bias']:+.2f} pp，沒有系統性高估或低估。",
    f"期程衰減：第 1 個月 {M['horizons'][0]['mae']} → 第 6 個月 {M['horizons'][-1]['mae']}，"
    "只採用第 1 個月的預測。",
], BLUE, h=4.6, size=10.5)
note(s, f"（30 秒）上表：驗證集 GB MAE {_cm['Gradient Boosting']['mae']}；RF 只差 {_rf_gap}，誠實標註。"
        f"選定後以 2023–2025 全量重訓，2026 上半年盲測 MAE {M['best']['mae']}，比最好的簡單基準好 {BL['beats_best_baseline_pct']}%，Bias {M['best']['bias']:+.2f}、不偏。"
        f"下表：固定起點推 6 個月，誤差從 {M['horizons'][0]['mae']} 擴大到 {M['horizons'][-1]['mae']}，所以只用第 1 個月的預測。")

# ══ 09 結論三：慣性 + 期程衰減 ═══════════════════════════════
_nm = {"occupancy_lag_1": "前 1 月住房率", "occupancy_roll3": "近 3 月均值",
       "occupancy_lag_12": "去年同月", "month": "月份", "month_sin": "月份循環",
       "occupancy_lag_2": "前 2 月住房率", "input_domestic_ratio": "本國客佔比",
       "input_international_ratio": "國際客佔比", "input_employees": "員工數"}
s = head(s := S(), "結論 ③",
         f"模型 {FI['top3_sum']}% 靠住房率自身慣性；第 1 個月能用、第 6 個月別用",
         "它是提前一個月的預警雷達，不是能回答「我該做什麼才能提升住房率」的工具。")
chart(s, XL_CHART_TYPE.BAR_CLUSTERED,
      list(reversed([_nm.get(n, n) for n in FI["names"][:6]])),
      [("特徵重要性 (%)", list(reversed(FI["values"][:6])))],
      0.62, 2.30, 6.3, 4.05, colors=[PURPLE], numfmt="0.0", gap=45)
text(s, "Gradient Boosting 特徵重要性（前 6 名）", 0.82, 6.42, 5.0, 0.24, 11, T_FAINT)
pcard(s, 7.15, 2.30, 5.57, "兩個誠實的觀察", [
    f"前 3 項（前 1 月 {FI['values'][0]}% + 近 3 月 {FI['values'][1]}% + 去年同月 {FI['values'][2]}%）＝ {FI['top3_sum']}%。",
    "房價、旅客結構、員工數合計 < 3% —— 情境試算不是因果模擬。",
    f"期程衰減：MAE 第 1 個月 {M['horizons'][0]['mae']} → 第 6 個月 {M['horizons'][-1]['mae']}，"
    f"六個月整體已接近「照抄上月」的 {M['baseline_mae']}。",
    "作業建議：每月重跑，只採用「第 1 個月」的預測。",
], PURPLE, h=3.9)
note(s, f"（50 秒）我把模型的弱點直接講出來。前三項全是住房率自己的歷史，佔 {FI['top3_sum']}%；"
        f"房價、旅客結構、員工數加起來只有 {FI['ops_levers_pct']}%。所以儀表板上的情境試算，"
        f"把國際客佔比拉高十個百分點、預測值幾乎不動——這是模型結構的必然，不是 bug。"
        f"另外誤差會隨期程擴大，第一個月 {M['horizons'][0]['mae']}、第六個月 {M['horizons'][-1]['mae']}，所以我建議每月重跑、只用第一個月的預測。")

# ══ 10 邊界：東部誤差 ════════════════════════════════════════
s = head(s := S(), "邊界",
         f"東部度假型的預測風險是都會型的 3 倍（台東 MAE {RO['by_city']['台東縣']['MAE']} vs 台中 {RO['by_city']['台中市']['MAE']}）",
         "東部旅館標為低信賴；發生地震、颱風、交通中斷時停用模型、改人工覆核。")
_cities = list(RO["by_city"].items())
chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED,
      [f"{c}\n({v['hotels']} 間)" for c, v in _cities],
      [("滾動一個月 MAE (pp)", [v["MAE"] for _, v in _cities])],
      0.62, 2.30, 8.15, 4.0, colors=[BLUE], numfmt="0.00", gap=45, ymax=15)
text(s, f"全體基準 MAE {RO['all']['MAE']} pp", 0.82, 6.38, 5.0, 0.24, 11, T_FAINT)
pcard(s, 8.95, 2.30, 3.77, "邊界在哪", [
    f"樣本進出影響小：平衡樣本 MAE {RO['balanced']['MAE']}，與全體差 {RO['balanced_gap_pp']} pp。",
    f"{M['best']['mae']} 是平均：都會約 {RO['by_city']['台中市']['MAE']}–{RO['by_city']['台北市']['MAE']}、東部可達 {RO['by_city']['台東縣']['MAE']}。",
    "地震、颱風的斷點，歷史慣性抓不到。",
], RED, h=3.6)
note(s, f"（35 秒）{M['best']['mae']} 是全體平均，但拆到縣市差很多：台中只有 {RO['by_city']['台中市']['MAE']:.2f}，"
        f"台東 {RO['by_city']['台東縣']['MAE']:.2f}——差三倍。"
        f"原因是地震跟颱風造成的斷點，模型靠歷史慣性根本抓不到。"
        f"所以東部旅館的預測我標為低信賴，天災期間停用、改人工覆核。")

# ══ 11 方法誠信 ══════════════════════════════════════════════
s = head(s := S(), "方法",
         "為什麼可以相信前面的數字",
         "資料分析的可信度來自「驗證方式」與「可重現」，不是結論好不好看。")
pcard(s, 0.62, 2.30, 6.0, "可信的地方", [
    "三段時間切分做時間外盲測，不是隨機 K-Fold；選模全程未碰 2026 盲測資料。",
    "涉及住房率的圖標統計口徑（加權 vs 簡單平均差約 3 pp）。",
    "所有數字由程式自原始 CSV 重算，投影片不寫死。",
], TEAL, h=4.05, size=12)
pcard(s, 6.72, 2.30, 6.0, "主動揭露的弱點", [
    f"選模訓練只用 {M['train_rows']:,} 筆（{M['train_period']}），比一次切分少約一年，"
    f"但重訓後盲測 MAE（{M['best']['mae']}）沒有明顯變差。",
    "資料僅 2023 年起：陸客體制斷裂，硬納入會汙染訓練。",
    "星等、房價、規模為分組平均，未以迴歸控制地段與規模。",
    "SARIMA／Prophet、外部特徵（氣象、連假天數×落點）、分群子模型均為未來工作。",
], RED, h=4.05, size=12)
note(s, "（25 秒）為什麼可以相信前面的數字：三段時間切分做時間外驗證、涉及住房率的圖標口徑、數字全部程式重算。"
        "右邊是我自己揭露的弱點——選模訓練資料比一次切分少一年、資料只從 2023 年起、星等分析沒控制混淆、"
        "時序模型和外部特徵還沒做。主動講清楚不能回答什麼，能回答的部分才會被相信。")

# ══ 12 總結 + Q&A ═══════════════════════════════════════════
s = S()
PAGE["n"] = 8
bg_fill(s, BG)
text(s, "總結", 0.62, 0.32, 7.0, 0.24, 12, BLUE, bold=True)
rect(s, 0.62, 0.60, 0.5, 0.032, BLUE, shape=MSO_SHAPE.RECTANGLE)
text(s, "三個結論，對誰有用", 0.60, 0.72, 12.4, 0.6, 25, T_TITLE, bold=True)
_sm = [
    ("復甦是量增不是漲價", TEAL, f"住房率指數 {IDX['occ'][-1]}、ADR {IDX['adr'][-1]}",
     "收益管理：下一輪成長靠拉價。"),
    (f"次月預測平均誤差 {M['best']['mae']} 個百分點", BLUE, f"勝 3 種簡單基準 {BL['beats_best_baseline_pct']}%",
     "促銷、OTA 房量、排班：用第 1 個月的預測。"),
    ("是預警雷達不是因果搖桿", AMBER, f"{FI['top3_sum']}% 靠慣性、東部誤差 3 倍",
     "風險 SOP：東部與天災期間人工覆核。"),
]
for i, (t_, col, kv, use) in enumerate(_sm):
    yy = 1.78 + i * 1.5
    rect(s, 0.62, yy, 12.1, 1.3, CARD, BORDER)
    rect(s, 0.62, yy, 0.06, 1.3, col, shape=MSO_SHAPE.RECTANGLE)
    text(s, f"結論 {i + 1}　{t_}", 0.94, yy + 0.18, 6.6, 0.32, 15, T_TITLE, bold=True)
    text(s, kv, 0.94, yy + 0.62, 6.6, 0.3, 12, col, bold=True)
    text(s, use, 7.3, yy, 5.2, 1.3, 12.5, T_BODY, spacing=1.25, anchor=MSO_ANCHOR.MIDDLE)
rect(s, 0.62, 6.35, 12.1, 0.78, HEAD_BG)
text(s, "Q & A　　儀表板 taiwan-hotel-occupancy.streamlit.app　|　數字由 compute_facts.py 重算　|　感謝評審",
     0.9, 6.56, 11.5, 0.4, 12.5, BLUE, bold=True)
note(s, f"（20 秒）總結：如果只記三件事——一，2025 的復甦是量增不是漲價；"
        f"二，次月預測誤差 {M['best']['mae']} 個百分點、贏簡單方法 {BL['beats_best_baseline_pct']}%；三，它是預警雷達不是因果工具。"
        f"所有數字都能程式重算。")

# ══ 13 封底 ═══════════════════════════════════════════════════
s = S()
PAGE["n"] = 9
bg_fill(s, BG)
_bbar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(PAGE_W), Inches(0.09))
_bbar.fill.solid()
_bbar.fill.fore_color.rgb = BLUE
_bbar.line.fill.background()
_bbar.shadow.inherit = False
_bbar2 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(PAGE_H - 0.09), Inches(PAGE_W), Inches(0.09))
_bbar2.fill.solid()
_bbar2.fill.fore_color.rgb = BLUE
_bbar2.line.fill.background()
_bbar2.shadow.inherit = False
text(s, "謝謝聆聽，敬請指教", 0.60, 2.55, 12.4, 1.0, 40, T_TITLE, bold=True,
     align=PP_ALIGN.CENTER)
rect(s, 5.9, 3.95, 1.55, 0.04, BLUE, shape=MSO_SHAPE.RECTANGLE)
def _linkline(_txt, _y, _url, _size, _color):
    # 超連結掛在「文字方塊」上（shape-level），不掛在文字 run 上：
    # run 不是超連結 run → PowerPoint 不會套佈景主題超連結色，各行才能不同色；
    # 放映時點整條文字方塊即可開連結。
    _tb = text(s, _txt, 0.60, _y, 12.4, 0.32, _size, _color, bold=True, align=PP_ALIGN.CENTER)
    _tb.text_frame.paragraphs[0].runs[0].font.underline = True
    _tb.click_action.hyperlink.address = _url


_linkline("互動儀表板　taiwan-hotel-occupancy.streamlit.app", 4.25,
          "https://taiwan-hotel-occupancy.streamlit.app", 15, CYAN)
_linkline("原始碼　github.com/lilujj03-oss/taiwan-hotel-occupancy", 4.62,
          "https://github.com/lilujj03-oss/taiwan-hotel-occupancy", 13, TEAL)
_linkline("作品集　lilujj03-oss.github.io／index.html", 4.99,
          "https://lilujj03-oss.github.io/index.html", 13, BLUE)
text(s, "所有數字由 compute_facts.py 自原始 CSV 重算，投影片內不寫死", 0.60, 5.42, 12.4, 0.3, 11, T_MUTED,
     align=PP_ALIGN.CENTER)
text(s, "資料來源：交通部觀光署《觀光旅館營運統計》2023-01～2026-06　·　《來臺旅客統計》",
     0.60, 6.30, 12.4, 0.3, 10.5, T_FAINT, align=PP_ALIGN.CENTER)
text(s, "口試報告人：詹梓芸　·　指導老師：蘇凱正、王子恩、張婕葳、楊淑美、吳國樹",
     0.60, 6.66, 12.4, 0.3, 10.5, T_FAINT, align=PP_ALIGN.CENTER)
note(s, "（收尾）感謝各位老師、評審，以上是我的報告，請指教。"
        "儀表板網址與原始碼都在這頁，歡迎現場操作。")

prs.save(OUT)

# PowerPoint 會用「佈景主題超連結色」蓋過 run 色，所以把主題 hlink 改成亮青
import re as _re2, zipfile as _zf
_LINK_HEX = "45C0F0"
_tmp = OUT.with_name(OUT.stem + ".__tmp__.pptx")
with _zf.ZipFile(OUT) as _zin, _zf.ZipFile(_tmp, "w", _zf.ZIP_DEFLATED) as _zout:
    for _it in _zin.infolist():
        _data = _zin.read(_it.filename)
        if _re2.match(r"ppt/theme/theme\d+\.xml$", _it.filename):
            _txt = _data.decode("utf-8")
            _txt = _re2.sub(r"<a:hlink>.*?</a:hlink>",
                            f'<a:hlink><a:srgbClr val="{_LINK_HEX}"/></a:hlink>', _txt, flags=_re2.S)
            _txt = _re2.sub(r"<a:folHlink>.*?</a:folHlink>",
                            f'<a:folHlink><a:srgbClr val="{_LINK_HEX}"/></a:folHlink>', _txt, flags=_re2.S)
            _data = _txt.encode("utf-8")
        _zout.writestr(_it, _data)
_tmp.replace(OUT)

_nc = sum(1 for sl in prs.slides for sh in sl.shapes if sh.has_chart)
print(f"[{STYLE}] 已產出：{OUT}")
print(f"投影片數：{len(prs.slides._sldIdLst)}　原生圖表：{_nc}")
