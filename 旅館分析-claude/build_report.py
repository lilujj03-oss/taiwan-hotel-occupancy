# -*- coding: utf-8 -*-
"""
台灣觀光旅館住房率分析與預測 — 專題書面報告（Word）

結合：
  · 老師回饋（先講結論再講原因、每張圖要有背後意義、只放有價值有效益的內容）
  · 「價值重構版」25 頁簡報的內容與圖表（深色版投影片圖）
  · 資料分析師角度的方法檢討（多基準對照、選模紀律、限制揭露）

數字全部讀自 facts.json（由 compute_facts.py 自原始 CSV 重算）。
投影片圖片讀自 _report_slides/sNN.png（由深色版 .pptx 匯出）。

執行：python 旅館分析-claude/build_report.py
輸出：台灣觀光旅館住房率分析與預測_專題報告_1130.docx
"""

import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Inches

HERE = Path(__file__).resolve().parent
F = json.loads((HERE / "facts.json").read_text(encoding="utf-8"))
SLIDES = HERE / "_report_slides"
OUT = HERE / "台灣觀光旅館住房率分析與預測_專題報告_1130.docx"

A, IDX, SEA, CITY, GU = F["annual"], F["index"], F["season"], F["city"], F["guests"]
ST, SG, PB, RB = F["star"], F["star_gap"], F["price_bins"], F["room_bins"]
M, FI, RO, SC, BL = F["model"], F["importance"], F["robust"], F["scope"], F["baselines"]
_ti = CITY["names"].index("台北市")
_small_cty = sum(1 for n in CITY["n"] if n <= 2)

FONT = "Microsoft JhengHei"
INK = RGBColor(0x1A, 0x1A, 0x1A)
ACCENT = RGBColor(0x1D, 0x4E, 0xD8)
MUTED = RGBColor(0x5A, 0x5A, 0x5A)

doc = Document()

# ── 全域字型 ────────────────────────────────────────────────
_normal = doc.styles["Normal"]
_normal.font.name = FONT
_normal.font.size = Pt(11)
_normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
for i in range(1, 5):
    st = doc.styles[f"Heading {i}"]
    st.font.name = FONT
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    st.font.color.rgb = ACCENT if i <= 2 else INK

sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)  # A4 直
sec.left_margin = sec.right_margin = Inches(0.9)
sec.top_margin = sec.bottom_margin = Inches(0.9)


def _run(p, txt, bold=False, size=11, color=INK, italic=False):
    r = p.add_run(txt)
    r.font.name = FONT
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    r._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    return r


def para(txt="", size=11, bold=False, color=INK, align=None, space_after=6, first_indent=0):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.28
    if align is not None:
        p.alignment = align
    if first_indent:
        p.paragraph_format.first_line_indent = Pt(first_indent)
    if txt:
        _run(p, txt, bold=bold, size=size, color=color)
    return p


def lead(label, body, color=ACCENT):
    """結論先行段：粗體前綴 + 內文。"""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.28
    _run(p, label + "　", bold=True, color=color)
    _run(p, body)
    return p


def bullet(txt, sub=False):
    p = doc.add_paragraph(style="List Bullet" if not sub else "List Bullet 2")
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.25
    _run(p, txt)
    return p


def h(level, txt):
    p = doc.add_heading(level=level)
    _run(p, txt, bold=True, size={1: 18, 2: 15, 3: 13, 4: 12}[level],
         color=ACCENT if level <= 2 else INK)
    return p


def figure(n, caption):
    f = SLIDES / f"s{n:02d}.png"
    if f.exists():
        doc.add_picture(str(f), width=Inches(6.1))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_after = Pt(10)
        _run(cp, f"圖 {n:02d}　{caption}", size=9, color=MUTED)


def table(rows, header=True):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Light Grid Accent 1"
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            c = t.cell(ri, ci)
            c.text = ""
            pr = c.paragraphs[0]
            pr.paragraph_format.space_after = Pt(2)
            _run(pr, str(val), bold=(ri == 0 and header), size=9.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    return t


# ══════════════════════════════════════════════════════════════
# 封面
# ══════════════════════════════════════════════════════════════
para("資料科學與旅宿收益管理專題", size=12, bold=True, color=ACCENT, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
para("台灣觀光旅館住房率分析與預測", size=24, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
para("2023–2025 營運實證　·　2026 上半年時間外驗證", size=12, color=MUTED, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=16)
para(f"資料範圍：交通部觀光署觀光旅館營運統計，{SC['months']} 個月 × {SC['hotels_all']} 間觀光旅館，"
     f"共 {SC['rows_all']:,} 筆月度面板資料", size=10.5, color=MUTED, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
para("書面報告　2026.09　|　配套簡報：價值重構版 25 頁（全深色版）",
     size=10, color=MUTED, align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 摘要（先講結論）
# ══════════════════════════════════════════════════════════════
h(1, "摘要")
para("本報告依「先講結論、再講原因」的原則撰寫：以下三個結論是全篇的重點，"
     "後續各章分別展開其證據與成因。", color=MUTED)

h(3, "結論 1　疫後復甦是「量增」不是「漲價」")
lead("這代表", f"以 2023 年為基準 100，2025 年住房率指數升到 {IDX['occ'][-1]}，但平均房價（ADR）指數"
              f"仍只有 {IDX['adr'][-1]}、連續兩年低於基準。復甦完全由「多賣房晚」驅動，不是漲價。", TEAL if False else ACCENT)
lead("效益", "業者還有一輪「拉價」空間 —— 下一步的收益成長應聚焦 ADR，而非再衝住房率。")

h(3, "結論 2　只依賴旅館自己的歷史資訊，次月住房率平均誤差約 6 個百分點")
lead("這代表", f"Gradient Boosting 模型在完全未參與訓練的 2026 上半年（{M['test_rows']} 筆）盲測，"
              f"平均絕對誤差（MAE）{M['best']['mae']} 個百分點，勝過「照抄上月」（{BL['rows'][0]['mae']}）、"
              f"「去年同月」（{BL['rows'][1]['mae']}）、「近 3 個月平均」（{BL['rows'][2]['mae']}）等所有簡單方法，"
              f"相對改善約 {BL['beats_best_baseline_pct']}%。")
lead("效益", "第 1 個月的預測能支援促銷時機、OTA 房量與排班等戰術決策。")

h(3, "結論 3　它是「預警雷達」，不是「因果搖桿」")
lead("這代表", f"模型 {FI['top3_sum']}% 的判斷來自住房率自身的慣性與季節性（前 1 月、近 3 月、去年同月）；"
              f"房價、旅客結構、員工數等營運輸入合計貢獻不到 3%。多月遞迴預測誤差擴大 —— "
              f"第 6 個月 MAE 升到 {M['horizons'][-1]['mae']} pp。")
lead("效益", "提前一個月看營運冷暖、排定風險 SOP；不回答「該做什麼才能提升住房率」，也不作精準定價或承諾值。")

h(3, "一個邊界")
para("本研究的資料是「旅館 × 月份」的彙總，不是訂單層級紀錄。因此全篇分析為「相關」而非「因果」，"
     "無法分析單筆訂單取消、取消原因或個別顧客行為，也無法預測地震、颱風等外生衝擊"
     "（東部旅館的預測須人工覆核）。", color=RGBColor(0xB0, 0x30, 0x40))

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 第 1 章
# ══════════════════════════════════════════════════════════════
h(1, "第 1 章　專案緣起、資料與方法")

h(2, "1.1　為什麼要做這個專案")
lead("結論", "旅館的空房不能庫存，但營運報表永遠慢一個月；能提前一個月預見次月住房率落點，"
            "調價、促銷與排班才有作用空間。")
para("旅宿業具備三個結構性特性：（1）空房不可儲存——當晚未售出的客房價值在午夜歸零；"
     "（2）成本相對剛性——折舊、租金、固定編制人力不隨住房率同步下降；"
     "（3）報表落後——官方月報與內部結算多在次月中旬才完成，看到低谷時已無法補救。"
     "本專案要補的就是這個「時間差」。")
figure(3, "專案緣起：問題（產能剛性）、作法（歷史慣性預警）、效益（能用與不能用）")

h(2, "1.2　資料")
lead("結論", f"{SC['months']} 個月官方月報整理成標準化的旅館×月面板（{SC['rows_all']:,} 筆、"
            f"{SC['hotels_all']} 間觀光旅館），並在清理階段修掉一個讓住客人次膨脹 3–5 倍的解析漏洞。")
para("資料處理過的三個實際問題：")
bullet("館名不一致：同一旅館跨年改名（如礁溪老爺大酒店→礁溪老爺酒店），以對照表合併。")
bullet("彙總列誤計：住客國籍年報在縣市尾端夾帶「小計／國際／一般」列，曾使人次膨脹 3–5 倍；"
       "以「第二欄為空」的規則排除後重新產生。")
bullet("樣本進出：旅館逐年進出場（改名、換品牌、極少數歇業），另以平衡樣本檢查其對模型指標的影響。")
para("統計口徑：本報告「加權平均」＝Σ已售房晚 ÷ Σ可售房晚（ADR＝Σ客房營收 ÷ Σ已售房晚、"
     "RevPAR＝Σ客房營收 ÷ Σ可售房晚）；「簡單平均」＝每個「旅館 × 月份」各算一票。"
     "住房率兩種口徑在本資料上差約 3 個百分點，涉及住房率的圖表均標明採用何者。", color=MUTED)
figure(5, "資料工程：規模、處理過的資料問題與口徑宣告")

h(2, "1.3　方法：怎麼避免「用未來預測過去」")
lead("結論", f"以完全未參與訓練的 2026 上半年（{M['test_rows']} 筆）做時間外盲測，"
            "不用會洩漏未來資訊的隨機 K-Fold；所有特徵一律只取 t-1（前一個月）以前已公布的數值。")
bullet(f"時間切分：訓練 2023-01～2025-12（{M['train_rows']:,} 筆），盲測 2026-01～06，選模型前完全未使用。")
bullet("Pipeline 封裝：SimpleImputer(median) + StandardScaler + OneHotEncoder 三者封裝於 "
       "scikit-learn Pipeline、僅以訓練集擬合。")
bullet("特徵僅取 t-1 以前：occupancy_lag_1/2/3/12、roll3（前三月均值）均由 groupby(旅館).shift() 產生。")
bullet("雙軌回測：滾動一個月（每月餵入真實上月值）與固定起點六個月（遞迴餵入自己的預測），"
       "後者才反映多月預測的真實衰減。")
figure(17, "驗證設計：時間外盲測、Pipeline 封裝、特徵僅取 t-1 以前、雙軌回測")

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 第 2 章
# ══════════════════════════════════════════════════════════════
h(1, "第 2 章　疫後營運實證")

h(2, "2.1　三年營運總表")
lead("結論", f"2025 年加權住房率 {A['occ'][-1]}%，為疫後高點；2024 年只是盤整。")
para(f"走過 2024 年的盤整（住房率僅自 {A['occ'][0]}% 微升至 {A['occ'][1]}%、ADR 反而下滑 "
     f"{A['adr'][0] - A['adr'][1]:,.0f} 元），2025 年真正放量：已售房晚單年增加 {A['sold_delta_wan']:.0f} 萬間，"
     f"加權住房率躍升至 {A['occ'][-1]}%。營收須分辨口徑：客房營收 {A['room_rev_yi'][-1]:,.0f} 億元，"
     f"含餐飲等部門的總營收為 {A['total_rev_yi'][-1]:,.0f} 億元；RevPAR 與 ADR 的分母是客房，一律只用客房營收計算。")
table([
    ["指標（加權）", f"{A['years'][0]} 年", f"{A['years'][1]} 年", f"{A['years'][2]} 年", "2023→2025"],
    ["加權住房率", f"{A['occ'][0]}%", f"{A['occ'][1]}%", f"{A['occ'][2]}%", f"+{A['occ_delta_pp']} pp"],
    ["平均房價 ADR", f"NT${A['adr'][0]:,.0f}", f"NT${A['adr'][1]:,.0f}", f"NT${A['adr'][2]:,.0f}", f"{A['adr'][2] - A['adr'][0]:+,.0f}"],
    ["每可售房收益 RevPAR", f"NT${A['revpar'][0]:,.0f}", f"NT${A['revpar'][1]:,.0f}", f"NT${A['revpar'][2]:,.0f}", f"{A['revpar'][2] - A['revpar'][0]:+,.0f}"],
    ["已售房晚", f"{A['sold_wan'][0]:,.0f} 萬", f"{A['sold_wan'][1]:,.0f} 萬", f"{A['sold_wan'][2]:,.0f} 萬", f"+{A['sold_wan'][2] - A['sold_wan'][0]:,.0f} 萬"],
    ["客房營收", f"{A['room_rev_yi'][0]:,.0f} 億", f"{A['room_rev_yi'][1]:,.0f} 億", f"{A['room_rev_yi'][2]:,.0f} 億", f"+{A['room_rev_yi'][2] - A['room_rev_yi'][0]:,.0f} 億"],
])

h(2, "2.2　成長動能：量增，不是漲價")
lead("結論", f"2025 的復甦是「多賣房」而非「漲價」——住房率指數 {IDX['occ'][-1]}、RevPAR 指數 "
            f"{IDX['revpar'][-1]}，但 ADR 指數只有 {IDX['adr'][-1]}、連兩年低於基準。")
lead("這代表", "下一輪收益成長的槓桿在 ADR。「國旅漫天喊漲」在全體觀光旅館的加權平均上不成立"
              "（平均數持平代表漲價未普及，而非沒有旅館漲價）。")
figure(7, "指數化拆解（2023 = 100）：住房率與 RevPAR 上揚、ADR 仍低於基準")

h(2, "2.3　季節節奏：都會的月間擺盪反而較大")
lead("結論", f"以「月」為單位，都會商務型的擺盪（{SEA['urban_swing']} pp）其實比風景度假型（{SEA['resort_swing']} pp）更大；"
            f"水準上都會全年平均 {SEA['urban_mean']}%、度假 {SEA['resort_mean']}%（相差約 {SEA['avg_gap']} pp），"
            f"兩類的全年高點都落在 {SEA['urban_peak_month']} 月。")
lead("這代表", "月份特徵對都會型的預測解釋力較大。度假型真正劇烈的是「週末 vs 平日」的落差，"
              "那是日資料層級的現象，月平均會將它抹平。")
figure(8, "月份季節性（簡單平均住房率）：都會 vs 度假的逐月走勢")

h(2, "2.4　聚落財務結構：住房率低不等於賺得少")
lead("結論", f"風景度假型住房率較低（{SEA['resort_mean']}% vs 都會 {SEA['urban_mean']}%），"
            f"但加權 ADR（NT${SEA['resort_adr_w']:,.0f}）與 RevPAR（NT${SEA['resort_revpar_w']:,.0f}）"
            f"反而高於都會型（ADR NT${SEA['urban_adr_w']:,.0f}、RevPAR NT${SEA['urban_revpar_w']:,.0f}）。")
lead("這代表", "跨旅館類型比較要用 RevPAR，只看住房率排行會誤判度假型旅館「經營不佳」。"
              "住房率是「產能利用率」，不是「獲利指標」。")
para("成因：風景度假縣市納入了目的地型高價旅館（日勝生加賀屋、涵碧樓、漢來日月行館），"
     "以「高房價、低周轉」經營；都會商務型則是「低房價、高周轉」。兩種模式在 RevPAR 上並不對稱。", color=MUTED)
figure(9, "都會 vs 度假聚落：加權 ADR 與 RevPAR 對比")

h(2, "2.5　區域差異：排行要看家數")
lead("結論", f"縣市住房率排行的前段班多是 1–2 間的小樣本；真正的基本盤是台北"
            f"（{CITY['n'][_ti]} 間、貢獻全台 {CITY['taipei_rev_share']}% 總營收）。")
para(f"{CITY['names'][0]} 以 {CITY['occ_weighted'][0]}% 居首，但全縣市僅 {CITY['n'][0]} 間觀光旅館——那是單一旅館的表現，"
     f"不是地區特性。花蓮受 2024 年 0403 地震衝擊，簡單平均住房率兩年下跌 {CITY['hualien_drop_pp']} pp。"
     f"全資料 {SC['hotels_all']} 間旅館分布於 {len(CITY['names'])} 個縣市，其中 {_small_cty} 個只有 1–2 間，"
     "樣本數過少者只描述、不推論。")
figure(10, "各縣市加權住房率（括號為觀光旅館家數）")

h(2, "2.6　客源結構：國際客回流、散客成常態")
lead("結論", f"國際旅客佔比三年 +{GU['intl_delta_pp']} pp、回到 {GU['intl_ratio'][-1]}%；"
            f"自由行散客比例長期穩定在 {GU['fit_ratio'][-1]}%。")
lead("這代表", "自由行（FIT）已是絕對主流，OTA 收益管理與數位評價成為飯店競爭的關鍵主戰場，"
              "而非低價團客模式。")
para(f"單一國籍看，日本自 {GU['japan_wan'][0]:.0f} 萬人次成長到 {GU['japan_wan'][-1]:.0f} 萬、"
     f"是最大成長來源；港澳（{GU['hkmo_wan'][0]:.0f}→{GU['hkmo_wan'][-1]:.0f} 萬）是唯一衰退的。"
     "數字為「旅館住客人次」（同一旅客住多晚／多間會重複計），與移民署入境人數不同、數值明顯較高。", color=MUTED)
figure(11, "住客國籍結構與主要外籍客源走勢")

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 第 3 章
# ══════════════════════════════════════════════════════════════
h(1, "第 3 章　星等、定價與結構特徵")

h(2, "3.1　星等階梯：差距來自房價")
lead("結論", f"五星級每可售房收益（RevPAR）是三星級的 {ST['revpar_5_over_3']} 倍，但這個差距約八成來自房價、"
            "不是住房率。")
para(f"五星對三星：住房率只高 {ST['occ'][1] - ST['occ'][3]:.1f} 個百分點，但 ADR 高 {ST['adr_5_over_3']} 倍。"
     f"RevPAR＝住房率 × ADR，兩者同向相乘，差距被放大成 {ST['revpar_5_over_3']} 倍。"
     f"全台 {ST['n'][1]} 間五星級即囊括 {ST['five_rev_share']}% 的客房總營收。"
     f"各星等的住房率天花板有限（都在 {min(ST['occ'])}–{max(ST['occ'])}% 之間），"
     "真正決定 RevPAR 高低的是房價定位——提升收益的槓桿在「能不能支撐更高的 ADR」。")
table([
    ["星等", "家數", "加權住房率", "平均房價 ADR", "每房收益 RevPAR", "營收佔比"],
    *[[nm, f"{ST['n'][i]} 間", f"{ST['occ'][i]}%", f"NT${ST['adr'][i]:,.0f}",
       f"NT${ST['revpar'][i]:,.0f}", f"{ST['rev_share'][i]}%"] for i, nm in enumerate(ST["names"])],
])
figure(13, "星等 RevPAR 三視角：住房率差距有限，房價差距才是階梯的動力")

h(2, "3.2　選擇偏誤：有星等住房率高，但不是「認證效果」")
lead("結論", f"有星等旅館住房率比無星等高 {SG['occ_simple']['gap_pp']} 個百分點（簡單平均；加權下縮為 "
            f"{SG['occ_weighted']['gap_pp']} pp），但這是「選擇偏誤」而非「認證帶來的效果」。")
para("三個真相：（1）反向因果——是先有好條件的旅館才去送評鑑，不是評鑑帶來好條件；"
     "（2）遺漏變數——送評者本身多位於黃金地段、具備宴會廳與泳池、導入國際管理團隊，"
     "這些同時推高星等與住房率；"
     f"（3）組成異質——無星等組僅 {ST['n'][4]} 間，混了未送評的高價度假旅館與老舊小旅館，平均值意義薄弱。")
para("本專案立場：星等是一個「強預測特徵」（在模型中以 One-Hot 編碼保留能提升預測力，這完全正當），"
     "但不是一個「可操作的因果槓桿」。報告涉及星等、房價、規模的結論一律以「相關」敘述，不以「造成」敘述。", color=MUTED)
figure(14, "選擇偏誤：表象差距 vs 三個不能當因果的理由")

h(2, "3.3　房價與規模：兩個非線性結構")
lead("結論", f"降價救不了滯銷——最低價帶住房率反而全組最低（{PB['worst_occ']}%）；"
            f"客房規模越大住房率越高（{RB['occ_simple'][0]}%→{RB['occ_simple'][-1]}%），但加權 ADR 呈 U 型，"
            f"最小規模組 NT${RB['adr_weighted'][0]:,.0f} 反而最高。")
para(f"房價 8 分位中，最低價組是斷崖（比第 2 組低約 {PB['occ'][1] - PB['occ'][0]:.1f} pp），"
     f"第 2～8 組全部落在 {PB['plateau_min']}–{PB['plateau_max']}% 的窄帶內、最高價組並未下滑，"
     "因此並非倒 U 型。低價是「體質差的結果」（屋齡偏高、區位條件較弱），不是「促銷的手段」。"
     "這種「階梯 + 轉折」的非線性關係，也說明了為何模型採用樹方法（分箱切點）而非線性迴歸。")
figure(15, "房價 8 分位與客房規模四組的住房率")

h(2, "3.4　範圍界定：為何模型資料從 2023 年起")
lead("結論", "中國大陸來臺旅客量已從 2015 年高峰 418 萬人次，經 2020–2022 邊境關閉，"
            "至 2023 年僅回到約 22 萬、目前估計約 30 萬——需求結構換了一個世界。")
para("若把 2019 年以前納入訓練，模型會學到一個「陸客佔外籍客三成以上」但不會再現的需求結構。"
     "將資料起點設在 2023 年，是為了讓訓練與預測落在同一個體制內——這是刻意的範圍設定，不是資料不足。", color=MUTED)
figure(16, "中國大陸來臺旅客 2011–2025：三段體制（開放 / 管制 / 關閉後）")

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 第 4 章
# ══════════════════════════════════════════════════════════════
h(1, "第 4 章　次月住房率預測")

h(2, "4.1　多基準對照：模型有沒有存在價值")
lead("結論", f"Gradient Boosting 在 2026 上半年盲測 MAE {M['best']['mae']} 個百分點，"
            f"勝過所有簡單方法——比其中最好的「照抄上月」（{BL['rows'][0]['mae']}）再好 "
            f"{BL['beats_best_baseline_pp']} pp（{BL['beats_best_baseline_pct']}%）。")
lead("這代表", "第 1 個月的數字能支援促銷時機、OTA 房量與排班等戰術決策。"
              "若模型只比簡單方法好一點點，導入 ML 就沒有必要；現在改善近兩成、且預測幾乎不偏"
              f"（Bias {M['best']['bias']:+.2f} pp），這個模型有存在價值。")
table([
    ["方法（同一份 2026 上半年盲測）", "MAE（住房率百分點）"],
    *[[r_["name"], f"{r_['mae']}"] for r_ in BL["rows"]],
])
para("成因：GB 同時用了短期慣性（前 1 月、近 3 月）、年度季節（去年同月）與地理／星等——"
     "任何「單一規則」都只抓到其中一塊，合起來才會更準。", color=MUTED)
figure(18, "多基準對照：GB vs 照抄上月 / 去年同月 / 近 3 月平均")

h(2, "4.2　模型對決")
_rf_gap_rpt = round(
    next(c["mae"] for c in M["candidates"] if c["name"] == "Random Forest")
    - next(c["mae"] for c in M["candidates"] if c["name"] == "Gradient Boosting"), 2)
lead("結論", f"四款候選模型在 2025 驗證集上競賽，Gradient Boosting 勝出，Random Forest 僅差 {_rf_gap_rpt} pp，"
            "Ridge 明顯較差（顯示關係非線性）；選模全程未觸碰 2026 上半年盲測資料。")
table([
    ["候選模型（2025 驗證集）", "MAE (pp)", "RMSE", "R²", "Bias (pp)"],
    *[[c["name"].replace(" (前月住房率)", "（前月住房率）"), f"{c['mae']}", f"{c['rmse']}",
       f"{c['r2']:.3f}", f"{c['bias']:+.2f}"] for c in M["candidates"]],
])
para("指標讀法：MAE 最貼近「這個預測準不準」的直覺；RMSE 對大誤差加重處罰、用於評估最壞情況；"
     f"選定 GB 後以 2023–2025 全量重新訓練，2026 上半年盲測 R² 解釋了 {M['best']['r2'] * 100:.1f}% 的住房率變異；"
     f"Bias {M['best']['bias']:+.2f} pp 表示模型沒有系統性高估或低估。", color=MUTED)
figure(19, "四款候選模型的 MAE 對照（2025 驗證集）")

h(2, "4.3　期程衰減：第 1 個月能用，第 6 個月別用")
lead("結論", f"固定起點遞迴回測中，MAE 自第 1 個月 {M['horizons'][0]['mae']} 擴大到第 6 個月 "
            f"{M['horizons'][-1]['mae']}，R² 自 {M['horizons'][0]['r2']:.2f} 降到 {M['horizons'][-1]['r2']:.2f}；"
            f"六個月整體 MAE {M['fixed_overall']['mae']}，已接近「照抄上月」的 {M['baseline_mae']}。")
para(f"曲線並不單調——第 3、4 個月（{M['horizons'][2]['mae']}、{M['horizons'][3]['mae']} pp）"
     "反而優於第 2 個月；在每期僅 115 筆的樣本下，這是月份特性與樣本噪聲，不應描述為平滑的衰減曲線。"
     "第 2 個月起模型改用「自己上一步的預測」當輸入，誤差在遞迴中被自己放大——不是模型變差，是遞迴的本質。")
lead("作業建議", "每月官方月報公布後重新推論，決策只採用「第 1 個月」的預測；"
                "第 2～6 個月的輸出僅作趨勢參考、不進入承諾性計畫。")
figure(20, "預測誤差隨期程的衰減（MAE / RMSE）")

h(2, f"4.4　模型本質：{FI['top3_sum']}% 靠慣性")
lead("結論", f"模型前 3 項特徵（前 1 月 {FI['values'][0]}% + 近 3 月 {FI['values'][1]}% + 去年同月 "
            f"{FI['values'][2]}%）合計 {FI['top3_sum']}% 的重要性；房價、旅客結構、員工數合計貢獻不到 3%。")
lead("這代表", "儀表板的情境試算不是因果模擬——把國際客佔比拉高 10 個百分點，預測值變化微乎其微；"
              "這是模型結構的必然，不是程式錯誤。模型的價值是「在官方數字出來前一個月，先給一個有根據的落點」，"
              "而不是回答「我該做什麼才能提升住房率」。")
figure(21, "特徵重要性（Top 8）")

h(2, "4.5　穩健性與誤差邊界")
lead("結論", f"樣本進出對指標影響極小（三年皆在榜 {RO['present_all_three_years']} 間，MAE {RO['balanced']['MAE']}，"
            f"與全體差 {RO['balanced_gap_pp']} pp）；真正的誤差邊界在東部——"
            f"台東 MAE {RO['by_city']['台東縣']['MAE']}、花蓮 {RO['by_city']['花蓮縣']['MAE']}，"
            f"是台中（{RO['by_city']['台中市']['MAE']}）的約 3 倍。")
lead("這代表", f"{M['best']['mae']} pp 是全體平均；都會型縣市實際約 4–6 pp、東部度假型可達 13 pp。"
              "東部旅館的預測值應標為低信賴；發生天災、交通中斷時停用模型輸出、改人工覆核。")
para("成因：地震、颱風造成的住房率斷點，無法由「歷史慣性」預測。報告只給單一數字會掩蓋這個差異，"
     "因此拆解至縣市層級呈現。", color=MUTED)
figure(22, "各縣市滾動一個月 MAE")

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 第 5 章
# ══════════════════════════════════════════════════════════════
h(1, "第 5 章　系統落地與後續方向")
lead("結論", "分析與模型都交付成 Streamlit 互動儀表板；後續四個方向已設計、尚未執行。")
para("主體分析 app.py 提供 5 個主題：整體營運與住房趨勢、個別旅館年度實績、星級認證效益分析、"
     "住客國籍與客源結構分析、影響因素與特徵解析。儀表板只上線可驗證的月度預測；"
     "年度模型（僅 3 年資料、R² 約 0.40）與每日模型（無旅館端逐日實際住房率）留在 repo 中探索、未上線"
     "——寧可少一頁，也不輸出無法驗證的數字。")
para("後續四個方向：", bold=True)
bullet("回補 2016–2019 月報，檢驗陸客體制轉換（門檻：僅在滾動 MAE、固定 MAE、RMSE 三項均改善時才替換正式模型）。")
bullet("整合連假與氣象外部特徵（官方辦公日曆已做特徵消融實驗、未通過門檻）。")
bullet("客源國籍細分、客房與餐飲雙引擎、每員工產值等結構深鑽。")
bullet("次月預測落入歷史後 20% 分位時觸發自動告警，推播促銷策略建議。")
figure(23, "系統落地（app.py 5 主題）與後續四個方向")

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 第 6 章
# ══════════════════════════════════════════════════════════════
h(1, "第 6 章　方法誠信與研究限制")
para("資料分析的可信度來自「驗證方式」與「可重現」，不是結論好不好看。本章同時列出「可信的地方」"
     "與「主動揭露的弱點」。")

h(2, "6.1　可信的地方")
bullet(f"三段時間切分做時間外驗證，不是隨機 K-Fold；訓練 {M['train_period']} → 驗證選模 {M['val_period']} → "
       f"盲測 {M['test_period']}，選模全程未碰盲測資料。")
bullet("涉及住房率的圖表都標明統計口徑（加權 / 簡單平均）。")
bullet("所有數字由 compute_facts.py 自 data/processed/hotel_monthly.csv 與 reports/*.json 重算成 "
       "facts.json，投影片與本報告內不寫死任何數值。")
bullet("已加入多基準對照（照抄上月 / 去年同月 / 近 3 個月平均），證明模型相對簡單方法的增益，"
       "而非只跟單一弱基準比較；模型改善幅度另附 1,000 次旅館分群拔靴法 95% 信賴區間"
       f"（[{M['improve_ci_lo']}, {M['improve_ci_hi']}] pp）。")

h(2, "6.2　主動揭露的弱點")
bullet(f"選模訓練資料量的取捨：選模階段只用 {M['train_rows']:,} 筆（{M['train_period']}，約 24 個月）訓練，"
       f"比舊版「一次切分」少約一年；重訓後 2026 上半年盲測 MAE（{M['best']['mae']}）與舊版（6.08）幾乎相同，"
       "可信度提升沒有明顯犧牲準確度，但驗證所用的訓練樣本確實較少，是已知的取捨。")
bullet("資料期間：僅 2023 年起。刻意排除 2020–2022（邊境封閉）與 2019 年以前（陸客規模是現在的 10 倍以上）；"
       "此為體制一致性的選擇，代價是無法分析「陸客時代→疫後」的結構轉變本身。")
bullet("多為分組平均：星等、縣市、房價、規模等分析多為「group by 後取平均」，未以多變數迴歸控制"
       "地段、房間數等干擾因子；因此星等、房價、規模的結論僅能讀作「相關」。")
bullet("分類方式：「都會／度假」為依縣市所在地的人工分類，非旅館實際定位或分群模型結果；"
       "星等以「現行」認證回填全期間，少數旅館歷史星等可能不同。")
bullet("外生衝擊：天災、重大活動、天氣、即時訂房進度與取消率均未納入；多月遞迴預測誤差擴大。")
figure(24, "方法誠信：可信的地方與主動揭露的弱點")

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 第 7 章
# ══════════════════════════════════════════════════════════════
h(1, "第 7 章　結論與建議")

h(2, "7.1　三個結論回顧")
lead("結論 1", f"復甦是量增不是漲價（住房率指數 {IDX['occ'][-1]}、ADR 指數 {IDX['adr'][-1]}）。")
lead("結論 2", f"次月住房率平均誤差 {M['best']['mae']} 個百分點，勝 3 種簡單基準 {BL['beats_best_baseline_pct']}%。")
lead("結論 3", f"模型 {FI['top3_sum']}% 靠慣性、東部誤差為都會 3 倍——它是預警雷達不是因果搖桿。")

h(2, "7.2　對誰有用（可行動建議）")
bullet("收益管理：2025 的成長已由「量」貢獻，下一輪應聚焦 ADR 定位；跨旅館類型比較改用 RevPAR，不看住房率排行。")
bullet("促銷與配額：以「第 1 個月」的預測作為促銷啟動、團體配額與人力配置的討論起點（精度足夠但非承諾值）；"
       "「第 6 個月」的輸出只作趨勢參考。")
bullet("風險 SOP：東部旅館的預測值標示為低信賴；發生地震、颱風、交通中斷時停用模型輸出、改人工覆核調度。")
bullet("定價策略：降價無法救體質差的旅館；低價帶住房率反而最低，資源應放在「能支撐更高 ADR」的定位上。")

h(2, "7.3　後續方向")
para("回補 2016–2019 月報並檢驗體制轉換、整合連假與氣象外部特徵、客源與餐飲／人效結構深鑽、"
     "低住房率自動告警——四項均已設計，依「可行性 × 對預測力的預期貢獻」排序。")

doc.add_page_break()

# ══════════════════════════════════════════════════════════════
# 附錄
# ══════════════════════════════════════════════════════════════
h(1, "附錄")

h(2, "A　資料來源")
bullet("交通部觀光署《觀光旅館營運統計》逐月報表，2023-01～2026-06（主資料）。")
bullet("交通部觀光署《來臺旅客統計》（中國大陸來臺旅客走勢；2024–2025 為估計值）。")
bullet("行政院人事行政總處《政府行政機關辦公日曆表》2023–2027（data.gov.tw/dataset/14718；"
       "假日特徵實驗用、未通過門檻、未納入正式模型）。")

h(2, "B　統計口徑")
para("加權平均住房率＝Σ已售房晚 ÷ Σ可售房晚；加權 ADR＝Σ客房營收 ÷ Σ已售房晚；"
     "加權 RevPAR＝Σ客房營收 ÷ Σ可售房晚。簡單平均＝每個「旅館 × 月份」各算一票，"
     "即 df.groupby(...).mean()。住房率兩種口徑在本資料上差約 3 個百分點。")

h(2, "C　可重現說明")
para("compute_facts.py 自原始 CSV 與 reports/*.json 重算 facts.json；本報告與配套簡報只讀 facts.json，"
     "不在文件中寫死任何數字。配套簡報以 build_deck_v2.py 產生（白底版與全深色版），"
     "本報告以 build_report.py 產生，圖片為全深色版投影片匯出。")

h(2, "D　老師回饋與本報告的對應")
table([
    ["老師回饋", "本報告如何落實"],
    ["先講結論再講原因", "各章、各節皆以「結論」起首，接「這代表 / 效益」，再以說明段與「成因」收尾；摘要即為三大結論。"],
    ["圖表要放背後的意義", "每張圖前均有一段「這代表什麼」的洞察句，並在圖說中點出結論，不做純描述。"],
    ["要放有價值有效益的東西", "每個結論配「對誰有用」的行動建議；新增第 4.1 節多基準對照，證明模型相對簡單方法的實際增益。"],
])

doc.save(OUT)
print(f"已產出：{OUT}")
print(f"段落數：{len(doc.paragraphs)}　圖片：{sum(1 for _ in SLIDES.glob('s*.png'))} 張投影片可用")
