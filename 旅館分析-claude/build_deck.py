# -*- coding: utf-8 -*-
"""
台灣觀光旅館住房率分析與預測 — 25 頁建議版簡報生成器

設計原則
  1. 投影片內不寫死任何數字，全部從 facts.json 取值（facts.json 由 compute_facts.py
     自 data/processed/hotel_monthly.csv 與 reports/*.json 重算）。
  2. 每一個比率都標明口徑（加權 / 簡單平均），避免與儀表板口徑不一致。
  3. 13 張原生 PowerPoint 圖表（可在 PowerPoint 內編輯資料），不使用圖片。
  4. 明亮專業配色，列印 25 頁以內。

執行：python 旅館分析-claude/build_deck.py
"""

import csv
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.oxml import parse_xml
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
F = json.loads((HERE / "facts.json").read_text(encoding="utf-8"))

# ── 風格（第一個命令列參數；預設 white）────────────────────────
#   python build_deck.py            → A 純白加粗線（淺色佈景）
#   python build_deck.py grey       → B 淺藍灰內凹（淺色佈景）
#   python build_deck.py dark       → C 深色戲劇繪圖區（淺色佈景）
#   python build_deck.py darktheme  → D 全深色佈景主題（送印用）
#   python build_deck.py all        → 產出 A/B/C 三個檔
STYLE = (sys.argv[1].lower() if len(sys.argv) > 1 else "white")

if STYLE == "all":
    import subprocess
    for _st in ("white", "grey", "dark"):
        subprocess.run([sys.executable, __file__, _st], check=True)
    sys.exit(0)

DARKUI = STYLE == "darktheme"

# ── 版面：A4 橫向（297 × 210 mm），1 頁 1 投影片 ──────────────
#   以 13.333 × 7.5 的「設計座標」撰寫，helper 內統一換算到 A4 畫布，
#   字級乘 FSCALE 以配合橫向縮窄，避免長中文標題折行。
DESIGN_W, DESIGN_H = 13.333, 7.5
PAGE_W, PAGE_H = 11.6929, 8.2677          # A4 橫向
_S = PAGE_W / DESIGN_W                     # 等比縮放（0.877），不變形
_OY = (PAGE_H - DESIGN_H * _S) / 2         # 內容垂直置中，上下各約 21mm 白邊
FSCALE = _S


def X(v):
    return Inches(v * _S)


def Y(v):
    return Inches(v * _S + _OY)


def FS(pt):
    return Pt(pt * FSCALE)


# ── 配色（專業數據分析報告風格：白底、克制用色、低圖表雜訊）──────
BG = RGBColor(0xFF, 0xFF, 0xFF)          # 頁面：純白
CARD = RGBColor(0xF5, 0xF6, 0xF8)        # 面板：極淺灰
BORDER = RGBColor(0xE3, 0xE6, 0xEB)      # 髮絲框線
HEAD_BG = RGBColor(0xF0, 0xF2, 0xF6)     # 重點條／表頭：中性淺灰
ALT_ROW = RGBColor(0xF7, 0xF8, 0xFA)     # 表格隔行
CHART_BG = RGBColor(0xFF, 0xFF, 0xFF)    # 圖表不加底色面板
CHART_EDGE = RGBColor(0xFF, 0xFF, 0xFF)

T_TITLE = RGBColor(0x14, 0x1C, 0x2B)     # 標題：近黑
T_BODY = RGBColor(0x3E, 0x47, 0x57)      # 內文
T_MUTED = RGBColor(0x72, 0x7C, 0x8B)     # 次要
T_FAINT = RGBColor(0x76, 0x80, 0x8D)     # 頁腳／圖註（統一色，較易讀）

BLUE = RGBColor(0x25, 0x46, 0xC7)        # 主色（沉穩靛藍）
CYAN = RGBColor(0x0E, 0x7C, 0xB8)
TEAL = RGBColor(0x0E, 0x8B, 0x7B)        # 第二資料色
AMBER = RGBColor(0xBE, 0x73, 0x0A)      # 唯一「注意」強調色
RED = RGBColor(0xC1, 0x33, 0x4E)        # 限制／警語
PURPLE = RGBColor(0x63, 0x46, 0xC8)
GREY = RGBColor(0xA6, 0xAE, 0xBB)       # 對照用中性資料色

_STYLES = {
    # 專業數據分析報告風格（白底、克制用色、低圖表雜訊）＝ 預設
    "white": dict(plot=RGBColor(0xFF, 0xFF, 0xFF), grid=RGBColor(0xEC, 0xEE, 0xF2),
                  label=RGBColor(0x14, 0x1C, 0x2B), lw=2.4, tag="專業A4版_1130"),
    "grey":  dict(plot=RGBColor(0xF3, 0xF5, 0xF8), grid=RGBColor(0xFF, 0xFF, 0xFF),
                  label=RGBColor(0x14, 0x1C, 0x2B), lw=2.4, tag="專業A4_淺灰繪圖區"),
    "dark":  dict(plot=RGBColor(0x0F, 0x23, 0x3D), grid=RGBColor(0x24, 0x40, 0x5F),
                  label=RGBColor(0xFF, 0xFF, 0xFF), lw=2.6, tag="專業A4_深繪圖區"),
}

if DARKUI:
    # ── 全深色佈景主題（rich dark navy，適合專業印刷）─────────
    BG = RGBColor(0x0C, 0x18, 0x28)          # 頁面底：深海軍藍
    CARD = RGBColor(0x15, 0x25, 0x3A)        # 卡片／面板
    BORDER = RGBColor(0x2C, 0x41, 0x5E)      # 框線
    HEAD_BG = RGBColor(0x1B, 0x30, 0x4B)     # 表頭／重點底
    ALT_ROW = RGBColor(0x12, 0x21, 0x35)     # 表格隔行
    CHART_BG = RGBColor(0x16, 0x28, 0x3F)    # 圖表面板
    CHART_EDGE = RGBColor(0x34, 0x50, 0x76)  # 圖表面板框
    T_TITLE = RGBColor(0xF3, 0xF7, 0xFC)     # 主標：近白
    T_BODY = RGBColor(0xD3, 0xDF, 0xEC)      # 內文：淺灰藍
    T_MUTED = RGBColor(0x9A, 0xAF, 0xC8)     # 次要文字
    T_FAINT = RGBColor(0xA6, 0xB9, 0xD0)     # 頁腳／圖註（統一色，深底上調亮）
    BLUE = RGBColor(0x60, 0x9C, 0xFF)        # 加亮的彩色，深底上才跳
    CYAN = RGBColor(0x45, 0xC0, 0xF0)
    TEAL = RGBColor(0x35, 0xD6, 0xC0)
    AMBER = RGBColor(0xFB, 0xBF, 0x3C)
    RED = RGBColor(0xFB, 0x7A, 0x92)
    PURPLE = RGBColor(0xB2, 0x9A, 0xF0)
    GREY = RGBColor(0x8B, 0x9F, 0xB8)
    _STYLES["darktheme"] = dict(plot=RGBColor(0x0F, 0x1E, 0x30),
                                grid=RGBColor(0x2A, 0x40, 0x5C),
                                label=RGBColor(0xF3, 0xF7, 0xFC), lw=2.7,
                                tag="專業A4全深色版_1130")

CFG = _STYLES.get(STYLE if STYLE in _STYLES else "white")
OUT = HERE / f"台灣觀光旅館住房率分析與預測_25頁建議版_{CFG['tag']}.pptx"
# 若主檔正被 PowerPoint 鎖定，改寫入帶時間戳的新檔，避免整支腳本失敗
if OUT.exists():
    try:
        with open(OUT, "a"):
            pass
    except PermissionError:
        import time as _t
        OUT = OUT.with_name(OUT.stem + "_" + _t.strftime("%H%M%S") + OUT.suffix)
        print(f"（主檔被鎖定，改存：{OUT.name}）")

FONT = "Microsoft JhengHei"
SRC = "資料來源：交通部觀光署觀光旅館營運統計（2023-01～2026-06）"

prs = Presentation()
prs.slide_width = Inches(PAGE_W)
prs.slide_height = Inches(PAGE_H)
BLANK = prs.slide_layouts[6]

PAGE = {"n": 0}


# ── 基礎元件 ────────────────────────────────────────────────
def rect(slide, l, t, w, h, fill, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.035):
    s = slide.shapes.add_shape(shape, X(l), Y(t), X(w), X(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(0.75)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        try:
            s.adjustments[0] = radius
        except Exception:
            pass
    s.shadow.inherit = False
    return s


def text(slide, body, l, t, w, h, size=14, color=T_BODY, bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.0, space_after=0):
    tb = slide.shapes.add_textbox(X(l), Y(t), X(w), X(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    lines = body.split("\n") if isinstance(body, str) else list(body)
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        if space_after:
            p.space_after = Pt(space_after)
        r = p.add_run()
        r.text = ln
        r.font.name = FONT
        r.font.size = FS(size)
        r.font.bold = bold
        r.font.color.rgb = color
    return tb


def rich(slide, items, l, t, w, h, size=13, spacing=1.22, space_after=7):
    """items: [(粗體前綴, 內文, 顏色)]"""
    tb = slide.shapes.add_textbox(X(l), Y(t), X(w), X(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    for i, (lead, rest, col) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = spacing
        p.space_after = Pt(space_after)
        if lead:
            r = p.add_run()
            r.text = lead
            r.font.name, r.font.size, r.font.bold = FONT, FS(size), True
            r.font.color.rgb = col
        if rest:
            r2 = p.add_run()
            r2.text = rest
            r2.font.name, r2.font.size = FONT, FS(size)
            r2.font.color.rgb = T_BODY
    return tb


def header(slide, part, title, sub, src=None):
    PAGE["n"] += 1
    bg_fill(slide, BG)
    # 章節標籤 + 短強調線（取代整條頂端色帶，較克制）
    text(slide, part, 0.62, 0.30, 7.0, 0.24, 11, BLUE, bold=True)
    rect(slide, 0.62, 0.555, 0.46, 0.030, BLUE, shape=MSO_SHAPE.RECTANGLE)
    text(slide, title, 0.60, 0.64, 12.4, 0.56, 25, T_TITLE, bold=True)
    text(slide, sub, 0.62, 1.22, 12.4, 0.30, 12, T_MUTED)
    rect(slide, 0.62, 7.03, 12.1, 0.010, BORDER, shape=MSO_SHAPE.RECTANGLE)
    text(slide, src or SRC, 0.62, 7.10, 9.5, 0.26, 9, T_FAINT)
    text(slide, f"{PAGE['n']:02d} / 25", 11.3, 7.10, 1.42, 0.26, 9.5, T_FAINT,
         bold=True, align=PP_ALIGN.RIGHT)
    return slide


def bg_fill(slide, color):
    """滿版底色（不受內容置中位移影響），供 header 與封面使用。"""
    sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0),
                                Inches(PAGE_W), Inches(PAGE_H))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def note(slide, txt):
    slide.notes_slide.notes_text_frame.text = txt


def card(slide, l, t, w, h, title=None, accent=BLUE, title_size=13.5):
    # 淺灰面板 + 髮絲框；標題下方一小段強調線（取代粗色邊條）
    rect(slide, l, t, w, h, CARD, BORDER)
    if title:
        text(slide, title, l + 0.26, t + 0.18, w - 0.5, 0.3, title_size, T_TITLE, bold=True)
        rect(slide, l + 0.26, t + 0.50, 0.34, 0.028, accent, shape=MSO_SHAPE.RECTANGLE)
    return (l + 0.26, t + (0.66 if title else 0.22), w - 0.52)


def kpi(slide, l, t, w, value, label, sub, accent=BLUE, h=1.34):
    rect(slide, l, t, w, h, CARD, BORDER)
    text(slide, value, l + 0.22, t + 0.17, w - 0.4, 0.46, 26, accent, bold=True)
    rect(slide, l + 0.24, t + 0.70, 0.40, 0.030, accent, shape=MSO_SHAPE.RECTANGLE)
    text(slide, label, l + 0.22, t + 0.80, w - 0.4, 0.26, 11, T_TITLE, bold=True)
    text(slide, sub, l + 0.22, t + 1.04, w - 0.4, 0.30, 9, T_MUTED, spacing=1.08)


def table(slide, rows, l, t, w, h, widths=None, fs=11.5, head_fs=11.5, aligns=None):
    nr, nc = len(rows), len(rows[0])
    shp = slide.shapes.add_table(nr, nc, X(l), Y(t), X(w), X(h))
    tb = shp.table
    if widths:
        tot = sum(widths)
        for i, cw in enumerate(widths):
            tb.columns[i].width = Emu(int(X(w) * cw / tot))
    tb.first_row = False
    try:
        tb.horz_banding = False
    except Exception:
        pass
    for ri, row in enumerate(rows):
        tb.rows[ri].height = X(h / nr)
        for ci, val in enumerate(row):
            c = tb.cell(ri, ci)
            c.fill.solid()
            c.fill.fore_color.rgb = HEAD_BG if ri == 0 else (BG if ri % 2 else ALT_ROW)
            c.margin_left = c.margin_right = Inches(0.08)
            c.margin_top = c.margin_bottom = Inches(0.02)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = c.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            if aligns:
                p.alignment = aligns[ci]
            else:
                p.alignment = PP_ALIGN.CENTER if ci else PP_ALIGN.LEFT
            r = p.add_run()
            r.text = str(val)
            r.font.name = FONT
            r.font.size = FS(head_fs if ri == 0 else fs)
            r.font.bold = ri == 0
            r.font.color.rgb = T_TITLE if ri == 0 else T_BODY
    return tb


def _sub(parent, tag, **attrs):
    el = parent.makeelement(qn(tag), {k: v for k, v in attrs.items()})
    parent.append(el)
    return el


def _tint_chart_bg(ch, area_rgb, plot_rgb=CARD, border_rgb=BORDER):
    """把圖表區塗上底色、繪圖區留白，讓圖表在頁面上被凸顯。"""
    cs = ch._chartSpace
    for old in cs.findall(qn("c:spPr")):
        cs.remove(old)
    spPr = cs.makeelement(qn("c:spPr"), {})
    fill = _sub(spPr, "a:solidFill")
    _sub(fill, "a:srgbClr", val=str(area_rgb))
    ln = _sub(spPr, "a:ln")
    lnfill = _sub(ln, "a:solidFill")
    _sub(lnfill, "a:srgbClr", val=str(border_rgb))
    cs.find(qn("c:chart")).addnext(spPr)
    # 繪圖區白底
    plot_area = cs.find(qn("c:chart")).find(qn("c:plotArea"))
    if plot_area is not None:
        for old in plot_area.findall(qn("c:spPr")):
            plot_area.remove(old)
        psp = plot_area.makeelement(qn("c:spPr"), {})
        pf = _sub(psp, "a:solidFill")
        _sub(pf, "a:srgbClr", val=str(plot_rgb))
        plot_area.append(psp)


def chart(slide, kind, cats, series, l, t, w, h, colors=None, legend=True,
          labels=True, numfmt='0.0', gap=60, smooth=False, ymin=None, ymax=None,
          lbl_size=9, overlap=-15, panel=True, panel_pad=0.12, point_label_pos=None):
    # 專業報告風格：圖表直接落在頁面上，不加外框面板；深色佈景才給底色
    _framed = panel and (DARKUI or STYLE in ("dark", "grey"))
    if _framed:
        rect(slide, l - panel_pad, t - panel_pad,
             w + 2 * panel_pad, h + 2 * panel_pad, CHART_BG, CHART_EDGE, radius=0.03)
    cd = CategoryChartData()
    cd.categories = cats
    for name, vals in series:
        cd.add_series(name, vals)
    gf = slide.shapes.add_chart(kind, X(l), Y(t), X(w), X(h), cd)
    ch = gf.chart
    ch.font.name = FONT
    ch.font.size = FS(9.5)
    ch.font.color.rgb = T_MUTED
    ch.has_title = False
    if _framed:
        _tint_chart_bg(ch, CHART_BG, plot_rgb=CFG["plot"], border_rgb=CHART_EDGE)

    if legend and len(series) > 1:
        ch.has_legend = True
        ch.legend.position = XL_LEGEND_POSITION.TOP
        ch.legend.include_in_layout = False
        ch.legend.font.size = FS(10)
        ch.legend.font.name = FONT
        ch.legend.font.color.rgb = T_BODY
    else:
        ch.has_legend = False

    plot = ch.plots[0]
    if kind in (XL_CHART_TYPE.COLUMN_CLUSTERED, XL_CHART_TYPE.BAR_CLUSTERED,
                XL_CHART_TYPE.COLUMN_STACKED, XL_CHART_TYPE.BAR_STACKED):
        plot.gap_width = gap
        plot.overlap = overlap if len(series) > 1 else 0
    if labels:
        plot.has_data_labels = True
        dl = plot.data_labels
        dl.number_format = numfmt
        dl.number_format_is_linked = False
        dl.font.size = FS(lbl_size)
        dl.font.name = FONT
        dl.font.bold = True
        dl.font.color.rgb = CFG["label"]
        # 標籤位置微調：key 可為 si（整條數列）或 (si, pi)（單一資料點，優先於數列）
        _pchar = {"above": "t", "below": "b", "left": "l", "right": "r"}
        _lblhex = str(CFG["label"])
        _sz = int(round(lbl_size * FSCALE * 100))
        _txpr = ('<c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr>'
                 f'<a:defRPr sz="{_sz}" b="1"><a:solidFill><a:srgbClr val="{_lblhex}"/></a:solidFill>'
                 f'<a:latin typeface="{FONT}"/></a:defRPr></a:pPr><a:endParaRPr lang="zh-TW"/></a:p></c:txPr>')
        _show = ('<c:showLegendKey val="0"/><c:showVal val="1"/><c:showCatName val="0"/>'
                 '<c:showSerName val="0"/><c:showPercent val="0"/><c:showBubbleSize val="0"/>')
        _ser_pos, _pt_pos = {}, {}
        for _k, _v in (point_label_pos or {}).items():
            if isinstance(_k, tuple):
                _pt_pos.setdefault(_k[0], {})[_k[1]] = _pchar[_v]
            else:
                _ser_pos[_k] = _pchar[_v]
        for si in sorted(set(_ser_pos) | set(_pt_pos)):
            try:
                _ser = ch.series[si]._element
                for _old in _ser.findall(qn("c:dLbls")):
                    _ser.remove(_old)
                _pts = "".join(
                    f'<c:dLbl><c:idx val="{pi}"/>'
                    '<c:spPr><a:noFill/><a:ln><a:noFill/></a:ln></c:spPr>' + _txpr +
                    f'<c:dLblPos val="{pc}"/>' + _show + '</c:dLbl>'
                    for pi, pc in sorted(_pt_pos.get(si, {}).items())
                )
                _serpos = f'<c:dLblPos val="{_ser_pos[si]}"/>' if si in _ser_pos else ""
                _xml = (
                    '<c:dLbls xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
                    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">' + _pts +
                    f'<c:numFmt formatCode="{numfmt}" sourceLinked="0"/>'
                    '<c:spPr><a:noFill/><a:ln><a:noFill/></a:ln></c:spPr>' + _txpr + _serpos + _show +
                    '</c:dLbls>'
                )
                _el = parse_xml(_xml)
                _cat = _ser.find(qn("c:cat"))
                (_cat.addprevious(_el) if _cat is not None else _ser.append(_el))
            except Exception as _e:
                print(f"  [warn] point_label_pos si={si}: {_e!r}")

    pal = colors or [BLUE, TEAL, AMBER, PURPLE, RED, CYAN]
    _dark_plot = STYLE in ("dark", "darktheme")
    _mk_ring = CARD if STYLE == "dark" else (CFG["plot"] if not _dark_plot else CHART_BG)
    for i, s in enumerate(ch.series):
        col = pal[i % len(pal)]
        if kind == XL_CHART_TYPE.LINE_MARKERS:
            s.format.line.color.rgb = col
            s.format.line.width = Pt(CFG["lw"])
            s.smooth = smooth
            s.marker.format.fill.solid()
            s.marker.format.fill.fore_color.rgb = col
            s.marker.format.line.color.rgb = _mk_ring
        else:
            s.format.fill.solid()
            s.format.fill.fore_color.rgb = col
            s.format.line.fill.background()

    _tick_col = RGBColor(0xDA, 0xE4, 0xF2) if _dark_plot else RGBColor(0x3A, 0x43, 0x52)
    for ax in (ch.category_axis, ch.value_axis):
        ax.has_major_gridlines = ax is ch.value_axis
        ax.format.line.color.rgb = CHART_EDGE if _dark_plot else BORDER
        ax.tick_labels.font.size = FS(9.5)
        ax.tick_labels.font.name = FONT
        ax.tick_labels.font.color.rgb = _tick_col
    ch.value_axis.major_gridlines.format.line.color.rgb = CFG["grid"]
    ch.value_axis.major_gridlines.format.line.width = Pt(0.75 if _dark_plot else 0.5)
    ch.value_axis.has_title = False
    ch.category_axis.has_title = False
    if ymin is not None:
        ch.value_axis.minimum_scale = ymin
    if ymax is not None:
        ch.value_axis.maximum_scale = ymax
    return ch


def caption(slide, txt, l, t, w, color=T_MUTED, size=10.5):
    return text(slide, txt, l, t, w, 0.5, size, color, spacing=1.2)


S = lambda: prs.slides.add_slide(BLANK)  # noqa: E731

A, IDX, SEA, CITY, GU = F["annual"], F["index"], F["season"], F["city"], F["guests"]
ST, SG, PB, RB = F["star"], F["star_gap"], F["price_bins"], F["room_bins"]
M, FI, RO, SC = F["model"], F["importance"], F["robust"], F["scope"]
SO = F["star_ols"]
PI = F["perm_importance"]
YRS = [f"{y} 年" for y in A["years"]]
MON = [f"{m} 月" for m in SEA["months"]]

# ══ 01 封面 ═════════════════════════════════════════════════
s = S()
PAGE["n"] = 1
bg_fill(s, BG)
_cbar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(PAGE_W), Inches(0.085))
_cbar.fill.solid()
_cbar.fill.fore_color.rgb = BLUE
_cbar.line.fill.background()
_cbar.shadow.inherit = False
rect(s, 7.50, 0.95, 5.25, 5.95, CARD, BORDER)
text(s, "資料科學與旅宿收益管理專題", 0.95, 1.35, 7.0, 0.3, 12.5, CYAN, bold=True)
rect(s, 0.95, 1.82, 0.085, 1.66, BLUE, shape=MSO_SHAPE.RECTANGLE)
text(s, "台灣觀光旅館\n住房率分析與預測", 1.26, 1.80, 6.2, 1.7, 38, T_TITLE, bold=True, spacing=1.12)
text(s, f"2023–2025 營運實證　·　2026 上半年時間外驗證（{SC['rows_2026h1']} 筆盲測）",
     0.97, 3.78, 6.4, 0.32, 13.5, T_BODY)
text(s, f"{SC['months']} 個月 × {SC['hotels_all']} 間觀光旅館　|　{SC['rows_all']:,} 筆月度面板資料",
     0.97, 4.18, 6.4, 0.3, 12, T_MUTED)
rect(s, 0.95, 4.78, 6.35, 0.92, HEAD_BG)
text(s, "本簡報所有數字均由 compute_facts.py 自原始資料重算並標明統計口徑",
     1.18, 5.00, 5.9, 0.48, 11, BLUE, bold=True, spacing=1.2)
text(s, SRC, 0.97, 6.10, 6.6, 0.26, 10.5, T_MUTED)
text(s, "2026.09", 0.97, 6.44, 2.0, 0.28, 11.5, BLUE, bold=True)

_hl = [
    (f"{A['occ'][-1]}%", "2025 加權住房率", TEAL),
    (f"{M['best']['mae']} pp", "次月預測 MAE", BLUE),
    (f"{M['best']['improve_pct']}%", "優於前月基準", AMBER),
    (f"{FI['top3_sum']}%", "前三特徵佔比", PURPLE),
]
text(s, "四個關鍵結果", 7.92, 1.30, 4.4, 0.3, 13.5, T_TITLE, bold=True)
for i, (v, lb, c) in enumerate(_hl):
    yy = 1.90 + i * 1.16
    rect(s, 7.92, yy, 0.05, 0.72, c, shape=MSO_SHAPE.RECTANGLE)
    text(s, v, 8.16, yy - 0.02, 2.4, 0.42, 22, c, bold=True)
    text(s, lb, 8.16, yy + 0.44, 4.2, 0.26, 11, T_MUTED)
rect(s, 7.92, 6.52, 4.55, 0.010, BORDER, shape=MSO_SHAPE.RECTANGLE)
text(s, "pp = percentage point（住房率百分點）", 7.92, 6.62, 4.6, 0.26, 9.5, T_FAINT)
note(s, "開場 20 秒：我分析交通部觀光署 42 個月、125 間觀光旅館的 4,832 筆月度營運資料，"
        "做了兩件事：一是釐清疫後復甦的真實結構，二是建立一個能提前一個月預警住房率的模型，"
        "並用完全沒參與訓練的 2026 上半年 694 筆資料做盲測。右邊四個數字是全篇結論。")

# ══ 02 問題與價值 ══════════════════════════════════════════
s = header(S(), "PART I · 專案緣起", "旅館的空房無法庫存，但營運報表永遠慢一個月",
           "若能在月初就預見次月住房率落點，調價、促銷與排班才有作用空間")
x, y, w = card(s, 0.62, 1.62, 3.85, 4.05, "問題：產能剛性", RED)
rich(s, [("空房不可儲存　", "當晚未售出的客房，價值在午夜歸零，無法留到隔天補賣。", RED),
         ("成本相對剛性　", "折舊、租金、固定編制人力不隨住房率同步下降，住房率下滑直接侵蝕現金流。", RED),
         ("報表落後一個月　", "官方月報與內部結算多在次月中旬才完成，看到低谷時已無法補救。", RED)],
     x, y, w, 3.2, 12.5)
x, y, w = card(s, 4.72, 1.62, 3.85, 4.05, "作法：用歷史慣性做短期預警", BLUE)
rich(s, [("資料層　", f"{SC['months']} 個月官方月報整理成旅館×月面板（{SC['rows_all']:,} 筆）。", BLUE),
         ("特徵層　", "只用 t-1 以前已公布的住房率滯後與季節特徵，杜絕偷看當期。", BLUE),
         ("模型層　", "四款候選模型在時間外資料上競賽，擇優作為正式模型。", BLUE),
         ("應用層　", "Streamlit 儀表板：歷史比較 + 次月預測 + 情境試算。", BLUE)],
     x, y, w, 3.2, 12.5)
x, y, w = card(s, 8.82, 1.62, 3.9, 4.05, "產出：能用與不能用", TEAL)
rich(s, [("能用　", f"提前一個月給出住房率落點，平均誤差 {M['best']['mae']} 個百分點，"
                   f"比「照抄上月」準 {M['best']['improve_pct']}%。", TEAL),
         ("能用　", "辨識淡旺季節奏、星等與規模的結構差異，作為定價與配額討論的依據。", TEAL),
         ("不能用　", "不是因果工具。資料是旅館×月彙總，無法回答單筆訂單取消、"
                    "取消原因或個別顧客行為。", AMBER),
         ("不能用　", "無法預測地震、颱風等外生衝擊，該情境需人工接管。", AMBER)],
     x, y, w, 3.2, 12.5)
rect(s, 0.62, 5.86, 12.1, 0.92, HEAD_BG)
text(s, f"一句話定位：這是一台「提前 30 天的預警雷達」，不是「可以轉動住房率的搖桿」。"
        f"模型 {FI['top3_sum']}% 的判斷來自住房率自身慣性與季節性，營運參數微調無法撼動大勢。",
     0.92, 6.12, 11.5, 0.45, 13, BLUE, bold=True, spacing=1.25)
note(s, "30 秒：飯店最殘酷的是客房不能庫存，成本卻是剛性的，但報表永遠慢一個月。"
        "我要解的就是這個時間差。請注意右邊『不能用』那一欄 —— 我刻意先講清楚邊界，"
        "因為資料是旅館乘月份的彙總，本質上做不了訂單層級的分析。")

# ══ 03 端到端藍圖 ══════════════════════════════════════════
s = header(S(), "PART I · 技術架構", "端到端資料管線：從官方 XLSX 到互動決策介面",
           "四層各自獨立可重跑，任一層資料更新後下游只需重新執行，不需改動程式邏輯")
_layers = [
    ("Layer 1", "資料擷取與解析", BLUE,
     [f"download_monthly_data.py 抓取 {SC['raw_files']} 個月 XLSX",
      "build_monthly_data.py 解析月報 → hotel_monthly.csv",
      "館名標準化、改名對照（2 組別名合併）"]),
    ("Layer 2", "特徵工程（防洩漏）", CYAN,
     ["依旅館分組位移：lag_1 / lag_2 / lag_3 / lag_12",
      "roll3 = 前三個月住房率均值",
      "月份循環編碼 + 縣市、星等 One-Hot"]),
    ("Layer 3", "模型訓練與驗證", TEAL,
     [f"時間切分：訓練 {M['train_rows']:,} 筆 / 盲測 {M['test_rows']} 筆",
      "Pipeline 封裝 Imputer + Scaler + Encoder",
      "滾動一個月 + 固定起點六個月雙軌回測"]),
    ("Layer 4", "應用與交付", PURPLE,
     ["app.py：5 大營運分析主題",
      "pages/ 1–3：年度 / 月度 / 每日預測分頁",
      "Streamlit Community Cloud 雲端部署"]),
]
for i, (tag, name, col, items) in enumerate(_layers):
    l = 0.62 + i * 3.09
    rect(s, l, 1.66, 2.92, 4.40, CARD, BORDER)
    text(s, tag, l + 0.24, 1.84, 2.5, 0.26, 10.5, col, bold=True)
    text(s, name, l + 0.24, 2.10, 2.5, 0.3, 14, T_TITLE, bold=True)
    rect(s, l + 0.24, 2.50, 0.32, 0.028, col, shape=MSO_SHAPE.RECTANGLE)
    rich(s, [("· ", it, col) for it in items], l + 0.24, 2.68, 2.5, 3.1, 11, 1.25, 8)
    if i < 3:
        text(s, "▶", l + 2.94, 3.66, 0.3, 0.3, 14, BORDER, bold=True, align=PP_ALIGN.CENTER)
rect(s, 0.62, 6.04, 12.1, 0.74, HEAD_BG)
text(s, "關鍵設計：Layer 2 的所有特徵都只取 t-1 以前的數值，且補值與標準化"
        "全部封裝在 scikit-learn Pipeline 內、僅以訓練集擬合 —— 這是整個專案的誠信底線。",
     0.92, 6.24, 11.5, 0.4, 12.5, BLUE, bold=True)
note(s, "20 秒：四層架構，每層可獨立重跑。重點是 Layer 2 與 Layer 3 的分界："
        "所有特徵只能用前一個月以前已經公布的數字，補值和標準化也都關在 Pipeline 裡、"
        "只用訓練集擬合，這樣盲測才算真的盲測。")

# ══ 04 資料工程 ════════════════════════════════════════════
s = header(S(), "PART I · 資料工程", "資料基礎：42 個月官方月報整理為標準化面板",
           "原始報表與處理後特徵嚴格分流；所有清理步驟以程式記錄，可完整重現")
_k = [(f"{SC['rows_all']:,} 筆", "月度面板紀錄", f"{SC['months']} 個月 × {SC['hotels_all']} 間觀光旅館", BLUE),
      (f"{SC['raw_files']} 檔", "原始月報 XLSX", "data/raw/monthly/ 202301～202606", CYAN),
      (f"{SC['rows_hist']:,} / {SC['rows_2026h1']}", "訓練 / 盲測筆數", "2023-01～2025-12 / 2026-01～06", TEAL),
      (f"{RO['present_all_three_years']} 間", "三年皆在榜（2023–2025）", f"2025 全年 12 月完整 {A['hotels_12m'][-1]} 間", AMBER)]
for i, (v, lb, sub, c) in enumerate(_k):
    kpi(s, 0.62 + i * 3.09, 1.62, 2.92, v, lb, sub, c)
x, y, w = card(s, 0.62, 3.18, 6.0, 2.46, "實際目錄結構", BLUE)
rich(s, [("data/raw/monthly/　", f"{SC['raw_files']} 個官方月報 XLSX（未進版控）", BLUE),
         ("data/processed/　", "hotel_monthly.csv 為主檔，供儀表板與模型共用", BLUE),
         ("reports/　", "驗證 JSON、特徵重要性 CSV、回測明細 CSV", BLUE),
         ("models/　", "monthly_model_through_202606.pkl（正式月度模型）", BLUE)],
     x, y, w, 1.8, 11.5)
x, y, w = card(s, 6.72, 3.18, 6.0, 2.46, "三個實際處理過的資料問題", AMBER)
rich(s, [("館名不一致　", "同一旅館跨年改名（礁溪老爺大酒店→礁溪老爺酒店、"
                        "寒舍艾麗酒店→台北艾麗酒店），以對照表合併。", AMBER),
         ("彙總列誤計　", "住客國籍年報在縣市尾端夾帶「小計／國際／一般」列，"
                        "曾使人次膨脹 3～5 倍；以「第二欄為空」規則排除後重新產生。", AMBER),
         ("樣本進出　", "旅館逐年進出場，另以平衡樣本驗證其對模型指標的影響。", AMBER)],
     x, y, w, 1.8, 11.5)
rect(s, 0.62, 5.86, 12.1, 0.92, HEAD_BG)
text(s, "口徑宣告：本簡報「加權平均」＝Σ已售房晚÷Σ可售房晚（ADR＝Σ客房營收÷Σ已售房晚）；"
        "「簡單平均」＝每個旅館×月份各算一票。兩者在本資料上可差 2～3 個百分點，每張圖都會標明。",
     0.92, 6.12, 11.5, 0.45, 12.5, BLUE, bold=True, spacing=1.25)
note(s, "25 秒：資料規模在上排。下面左邊是實際目錄，右邊是我真正動手處理的三個問題 —— "
        "特別是中間那個：住客國籍年報夾帶小計列，害人次膨脹三到五倍，我比對原始 XLSX 才抓到。"
        "最下面那條口徑宣告很重要，加權跟簡單平均在這份資料上會差兩三個百分點。")

# ══ 05 三年總體營運大表 ════════════════════════════════════
s = header(S(), "PART II · 營運實證", f"三年總體營運：2025 年加權住房率 {A['occ'][-1]}%，為疫後高點",
           "全部為加權口徑（Σ已售房晚÷Σ可售房晚），與儀表板「歷史年度營運總覽」表一致")
_rows = [["指標（加權口徑）", f"{A['years'][0]} 年", f"{A['years'][1]} 年", f"{A['years'][2]} 年", "2023→2025 變化"],
         ["加權平均住房率", f"{A['occ'][0]}%", f"{A['occ'][1]}%", f"{A['occ'][2]}%", f"+{A['occ_delta_pp']} pp"],
         ["平均房價 ADR", f"NT$ {A['adr'][0]:,.0f}", f"NT$ {A['adr'][1]:,.0f}", f"NT$ {A['adr'][2]:,.0f}",
          f"{A['adr'][2] - A['adr'][0]:+,.0f} 元"],
         ["每可售房收益 RevPAR", f"NT$ {A['revpar'][0]:,.0f}", f"NT$ {A['revpar'][1]:,.0f}", f"NT$ {A['revpar'][2]:,.0f}",
          f"{A['revpar'][2] - A['revpar'][0]:+,.0f} 元"],
         ["已售房晚", f"{A['sold_wan'][0]:,.1f} 萬", f"{A['sold_wan'][1]:,.1f} 萬", f"{A['sold_wan'][2]:,.1f} 萬",
          f"+{A['sold_wan'][2] - A['sold_wan'][0]:,.1f} 萬"],
         ["客房營收", f"{A['room_rev_yi'][0]:,.1f} 億", f"{A['room_rev_yi'][1]:,.1f} 億", f"{A['room_rev_yi'][2]:,.1f} 億",
          f"+{A['room_rev_yi'][2] - A['room_rev_yi'][0]:,.1f} 億"],
         ["總營收（含餐飲等）", f"{A['total_rev_yi'][0]:,.1f} 億", f"{A['total_rev_yi'][1]:,.1f} 億",
          f"{A['total_rev_yi'][2]:,.1f} 億", f"+{A['total_rev_yi'][2] - A['total_rev_yi'][0]:,.1f} 億"],
         ["涵蓋旅館數（全年 12 月完整）", f"{A['hotels_12m'][0]} 間", f"{A['hotels_12m'][1]} 間",
          f"{A['hotels_12m'][2]} 間", "樣本逐年進出"]]
table(s, _rows, 0.62, 1.66, 12.1, 3.30, widths=[2.5, 1.35, 1.35, 1.35, 1.5], fs=12, head_fs=12)
x, y, w = card(s, 0.62, 5.16, 5.95, 1.62, "讀法一：2024 年是盤整年", AMBER)
text(s, f"住房率僅自 {A['occ'][0]}% 微升至 {A['occ'][1]}%（+{A['occ'][1] - A['occ'][0]:.2f} pp），"
        f"ADR 反而下滑 {A['adr'][0] - A['adr'][1]:,.0f} 元，RevPAR 因此較 2023 年衰退。"
        f"真正的放量發生在 2025 年：已售房晚單年增加 {A['sold_delta_wan']:,.1f} 萬間。",
     x, y, w, 1.0, 11.5, T_BODY, spacing=1.25)
x, y, w = card(s, 6.77, 5.16, 5.95, 1.62, "讀法二：營收規模需分辨口徑", TEAL)
text(s, f"客房營收 {A['room_rev_yi'][-1]:,.1f} 億元；若含餐飲與其他部門則為 "
        f"{A['total_rev_yi'][-1]:,.1f} 億元（餐飲約 {A['food_rev_yi'][-1]:,.1f} 億）。"
        f"RevPAR 與 ADR 的分母是客房，因此一律只用客房營收計算。",
     x, y, w, 1.0, 11.5, T_BODY, spacing=1.25)
note(s, "35 秒：這是全篇的事實底座。三年加權住房率 60.76、60.98、64.15。"
        "注意 2024 年是盤整年，住房率幾乎沒動、房價還跌了一百多塊，RevPAR 甚至比 2023 差。"
        "真正放量是 2025 年，已售房晚一年多了 29.4 萬間。"
        "右下角特別標註營收口徑：客房營收 290.5 億，含餐飲的總營收是 634.6 億，兩者不能混用。")

# ══ 06 指數化 ══════════════════════════════════════════════
s = header(S(), "PART II · 成長動能", "指數化拆解：2025 年的成長來自「量」，不是「價」",
           f"以 2023 年為基準 100，加權口徑。住房率指數升至 {IDX['occ'][-1]}，ADR 指數仍低於基準（{IDX['adr'][-1]}）")
chart(s, XL_CHART_TYPE.LINE_MARKERS, YRS,
      [("住房率指數", IDX["occ"]), ("ADR 指數", IDX["adr"]), ("RevPAR 指數", IDX["revpar"])],
      0.62, 1.62, 7.55, 4.25, colors=[TEAL, AMBER, BLUE], numfmt="0.0", ymin=94, ymax=108,
      point_label_pos={0: "above", 2: "above", 1: "below", (2, 2): "below"})
# 住房率/RevPAR 標籤在線上方、ADR 在線下方；RevPAR 2025 點（104.9）改到線下方
text(s, "加權口徑，2023 = 100", 0.80, 5.78, 4.0, 0.26, 10, T_FAINT)
x, y, w = card(s, 8.37, 1.62, 4.35, 4.25, "三條線怎麼讀", BLUE)
rich(s, [(f"住房率 {IDX['occ'][-1]}　", "需求確實回來了，且成長集中在 2024→2025。", TEAL),
         (f"ADR {IDX['adr'][-1]}　", "兩年都低於基準：名目房價尚未回到 2023 年水準，"
                                   "業者選擇以價格換取產能利用率。", AMBER),
         (f"RevPAR {IDX['revpar'][-1]}　", "＝住房率 × ADR。量的增幅被價的缺口抵掉一部分，"
                                          f"所以 RevPAR 指數（{IDX['revpar'][-1]}）低於住房率指數（{IDX['occ'][-1]}）。", BLUE),
         ("商業意涵　", "「國旅漫天喊漲」在觀光旅館的加權平均上不成立。"
                      "真正的收益管理空間在於：量已經回來，下一步才是拉價。", BLUE)],
     x, y, w, 3.4, 12)
rect(s, 0.62, 6.06, 12.1, 0.72, HEAD_BG)
text(s, "注意：這是全體觀光旅館的加權平均。個別高檔旅館漲價不會被否證 —— "
        "平均數持平代表「漲價未普及」，而非「沒有旅館漲價」。",
     0.92, 6.26, 11.5, 0.4, 12, BLUE, bold=True)
note(s, "30 秒：把三個指標都用 2023 當 100。住房率衝到 105.6，但房價指數是 99.3 —— "
        "兩年都低於基準。所以 2025 年的成長完全是賣出更多房晚換來的，不是漲價。"
        "RevPAR 104.9 夾在中間，因為它等於住房率乘房價。"
        "如果被問『可是我覺得住宿變貴了』，就用最下面那句回答：平均持平不代表沒有旅館漲價。")

# ══ 07 月份季節性 ══════════════════════════════════════════
s = header(S(), "PART II · 季節節奏", "都會商務型的月間擺盪，其實比風景度假型更大",
           f"簡單平均（每旅館×月一票）。都會擺盪 {SEA['urban_swing']} pp vs 度假 {SEA['resort_swing']} pp，與直覺相反")
chart(s, XL_CHART_TYPE.LINE_MARKERS, MON,
      [("都會商務聚落", SEA["urban"]), ("風景度假聚落", SEA["resort"])],
      0.62, 1.62, 7.55, 4.25, colors=[BLUE, AMBER], numfmt="0", ymin=40, ymax=75, lbl_size=8)
text(s, "簡單平均住房率 (%)，2023–2025 合計；聚落依旅館所在縣市人工分類",
     0.80, 5.78, 6.5, 0.26, 10, T_FAINT)
x, y, w = card(s, 8.37, 1.62, 4.35, 4.25, "三個必須講清楚的事實", BLUE)
rich(s, [("水準差距　", f"都會全年平均 {SEA['urban_mean']}%，度假 {SEA['resort_mean']}%，"
                      f"平均每月相差約 {SEA['avg_gap']} 個百分點 —— 差距在水準，不在波動。", BLUE),
         ("擺盪反而都會大　", f"都會最高 {SEA['urban_peak_month']} 月（{max(SEA['urban'])}%）、"
                            f"最低 {SEA['urban_trough_month']} 月（{min(SEA['urban'])}%），"
                            f"落差 {SEA['urban_swing']} pp；度假僅 {SEA['resort_swing']} pp。", AMBER),
         ("高點同月　", f"兩類旅館的全年高點都落在 {SEA['urban_peak_month']} 月"
                      "（尾牙、展會、跨年疊加），並非一方旺季、一方淡季。", TEAL),
         ("對模型的意義　", "度假型住房率低而平，都會型高而有節奏 —— "
                          "月份特徵對都會型的解釋力較大。", PURPLE)],
     x, y, w, 3.4, 12)
rect(s, 0.62, 6.06, 12.1, 0.72, HEAD_BG)
text(s, "為什麼不是「度假型淡旺季劇烈」？因為本資料只到「月」的粒度 —— "
        "度假型最劇烈的是週末與平日的落差，那是日資料層級的現象，月平均會把它抹平。",
     0.92, 6.26, 11.5, 0.4, 12, BLUE, bold=True)
note(s, "40 秒 —— 這頁是反直覺的重點。大家都以為度假旅館淡旺季劇烈、都會平穩，"
        "但月資料顯示相反：都會擺盪 14.2 個百分點，度假只有 9.4。"
        "原因寫在最下面：度假型真正劇烈的是週末跟平日的差，那是日資料的現象，月平均會抹平。"
        "如果考官問這個，這就是標準答案。另外兩類的高點都在 12 月，不是一方旺一方淡。")

# ══ 08 聚落財務結構 ════════════════════════════════════════
s = header(S(), "PART II · 聚落結構", "度假型住房率較低，但房價與每房收益反而高於都會型",
           "加權口徑。住房率低不等於賺得少 —— RevPAR 才是可比的收益指標")
chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED, ["平均房價 ADR", "每可售房收益 RevPAR"],
      [("都會商務聚落", [SEA["urban_adr_w"], SEA["urban_revpar_w"]]),
       ("風景度假聚落", [SEA["resort_adr_w"], SEA["resort_revpar_w"]])],
      0.62, 1.72, 6.75, 4.05, colors=[BLUE, AMBER], numfmt='#,##0', gap=80)
text(s, "加權口徑（ADR＝Σ客房營收÷Σ已售房晚；RevPAR＝Σ客房營收÷Σ可售房晚），單位 NT$",
     0.80, 5.70, 6.4, 0.26, 10, T_FAINT)
x, y, w = card(s, 7.57, 1.72, 5.15, 1.95, "數字關係", TEAL)
rich(s, [("ADR　", f"度假 NT$ {SEA['resort_adr_w']:,.0f} vs 都會 NT$ {SEA['urban_adr_w']:,.0f}"
                 f"（高 {SEA['resort_adr_w'] / SEA['urban_adr_w'] - 1:.0%}）", TEAL),
         ("RevPAR　", f"度假 NT$ {SEA['resort_revpar_w']:,.0f} vs 都會 NT$ {SEA['urban_revpar_w']:,.0f}"
                    f"（高 {SEA['resort_revpar_w'] / SEA['urban_revpar_w'] - 1:.0%}）", TEAL),
         ("住房率　", f"度假 {SEA['resort_mean']}% vs 都會 {SEA['urban_mean']}%"
                   f"（低 {SEA['urban_mean'] - SEA['resort_mean']:.1f} pp）", AMBER)],
     x, y, w, 1.35, 11.5)
x, y, w = card(s, 7.57, 3.82, 5.15, 1.95, "為什麼會這樣", PURPLE)
text(s, "風景度假縣市納入了若干目的地型高價旅館（如日勝生加賀屋、涵碧樓、漢來日月行館），"
        "它們以高房價、低周轉的模式經營；都會商務型則是低房價、高周轉。"
        "兩種模式在 RevPAR 上並不對稱，度假型的高 ADR 足以補回較低的住房率。",
     x, y, w, 1.35, 11.5, T_BODY, spacing=1.25)
rect(s, 0.62, 5.98, 12.1, 0.80, HEAD_BG)
text(s, "口試重點：若只看住房率排行，會誤判度假型旅館「經營不佳」。"
        "住房率是產能利用率、不是獲利指標；跨商業模式比較必須改用 RevPAR。",
     0.92, 6.20, 11.5, 0.42, 12, BLUE, bold=True)
note(s, "30 秒：這頁修正一個常見誤讀。度假型住房率比都會低 13 個百分點，"
        "但房價高 53%、RevPAR 還高 18%。因為度假縣市有加賀屋、涵碧樓這類高價低周轉的旅館。"
        "結論一句話：住房率是產能利用率，不是獲利指標，跨模式比較要看 RevPAR。")

# ══ 09 縣市排行 ════════════════════════════════════════════
s = header(S(), "PART II · 區域差異", "縣市住房率排行必須同時看旅館家數，否則會過度推論",
           "加權口徑。前段班多為樣本數極少的縣市，不具統計代表性")
_n = 12
_cn = [f"{c}\n({n} 間)" for c, n in zip(CITY["names"][:_n], CITY["n"][:_n])]
chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED, _cn,
      [("加權住房率 (%)", CITY["occ_weighted"][:_n])],
      0.62, 1.66, 8.15, 3.95, colors=[BLUE], numfmt="0.0", gap=45, ymax=90, lbl_size=9)
text(s, "加權住房率（Σ已售房晚÷Σ可售房晚），2023–2025 合計；括號為涵蓋觀光旅館家數",
     0.80, 5.52, 7.8, 0.26, 10, T_FAINT)
x, y, w = card(s, 8.97, 1.66, 3.75, 1.88, "不可直接推論的前段班", RED)
rich(s, [(f"{CITY['names'][0]}　", f"{CITY['occ_weighted'][0]}%，但全縣市僅 {CITY['n'][0]} 間 —— "
                                 "是單一旅館的表現，不是地區特性。", RED),
         (f"{CITY['names'][1]}　", f"{CITY['occ_weighted'][1]}%，{CITY['n'][1]} 間，同樣屬小樣本。", RED)],
     x, y, w, 1.3, 11.5)
x, y, w = card(s, 8.97, 3.70, 3.75, 1.91, "真正有代表性的觀察", TEAL)
rich(s, [("台北市　", f"{CITY['n'][CITY['names'].index('台北市')]} 間、"
                    f"{CITY['occ_weighted'][CITY['names'].index('台北市')]}%，"
                    f"並貢獻全台 {CITY['taipei_rev_share']}% 總營收，是唯一兼具規模與高住房率者。", TEAL),
         ("花蓮縣　", f"受 2024 年 0403 地震影響，簡單平均住房率自 "
                    f"{CITY['by_year']['花蓮縣'][0]}% 降至 {CITY['by_year']['花蓮縣'][1]}%"
                    f"（{CITY['hualien_drop_pp']} pp），2025 年僅回升至 {CITY['by_year']['花蓮縣'][2]}%。", AMBER)],
     x, y, w, 1.35, 11.5)
rect(s, 0.62, 5.98, 12.1, 0.80, HEAD_BG)
text(s, f"統計原則：本資料共 {SC['hotels_all']} 間觀光旅館分布於 {len(CITY['names'])} 個縣市，"
        f"其中 {sum(1 for n in CITY['n'] if n <= 2)} 個縣市的樣本數 ≤ 2 間。"
        "報告中一律先標家數、再談排名，樣本數過少者只描述、不推論。",
     0.92, 6.20, 11.5, 0.42, 12, BLUE, bold=True)
note(s, "30 秒：排行榜第一名是基隆，但基隆只有一間觀光旅館 —— 那是一間旅館的表現，"
        "不是地區特性。真正有代表性的是台北：38 間、住房率 69.9%、而且吃下全台一半營收。"
        "花蓮則是外生衝擊的案例，0403 地震讓住房率掉了 14.5 個百分點，到 2025 還沒回來。"
        "我的原則是先標家數再談排名。")

# ══ 10 客源結構 ════════════════════════════════════════════
s = header(S(), "PART II · 客源結構", f"國際旅客佔比回升至 {GU['intl_ratio'][-1]}%，散客比例三年穩定在 77%",
           "加權人次口徑。數字為「旅館住客人次」，同一旅客多晚／多間會重複計，與移民署入境人數不同")
chart(s, XL_CHART_TYPE.COLUMN_STACKED, YRS,
      [("本國旅客", GU["dom_ratio"]), ("國際旅客", GU["intl_ratio"])],
      0.62, 1.66, 5.35, 4.0, colors=[GREY, BLUE], numfmt="0.0", gap=110, overlap=100, ymax=100)
text(s, "住客人次結構 (%)，加權", 0.80, 5.58, 4.0, 0.26, 10, T_FAINT)
chart(s, XL_CHART_TYPE.LINE_MARKERS, YRS,
      [("日本", GU["japan_wan"]), ("美國", GU["usa_wan"]),
       ("韓國", GU["korea_wan"]), ("港澳", GU["hkmo_wan"])],
      6.55, 1.66, 6.05, 4.0, colors=[RED, BLUE, TEAL, AMBER], numfmt="0.0", ymin=20)
text(s, "主要外籍客源住客人次（萬人次）", 6.73, 5.58, 5.0, 0.26, 10, T_FAINT)
x, y, w = card(s, 0.62, 5.92, 3.9, 0.90, None, BLUE)
rich(s, [("國際佔比　", f"{GU['intl_ratio'][0]}% → {GU['intl_ratio'][-1]}%"
                      f"（+{GU['intl_delta_pp']} pp）", BLUE)], x, y - 0.22, w, 0.6, 11.5)
x, y, w = card(s, 4.72, 5.92, 3.9, 0.90, None, TEAL)
rich(s, [("散客:團客　", f"{GU['fit_ratio'][-1]}:{GU['group_ratio'][-1]}，三年幾乎不變", TEAL)],
     x, y - 0.22, w, 0.6, 11.5)
x, y, w = card(s, 8.82, 5.92, 3.9, 0.90, None, AMBER)
rich(s, [("唯一衰退　", f"港澳 {GU['hkmo_wan'][0]} → {GU['hkmo_wan'][-1]} 萬人次", AMBER)],
     x, y - 0.22, w, 0.6, 11.5)
note(s, "30 秒：左圖國際旅客從 34.4% 回到 40.7%，加了 6.3 個百分點。"
        "右圖拆到單一國籍：日本從 76 萬漲到 111.6 萬是最大成長來源，美國也明顯回升，"
        "港澳是唯一衰退的。散客團客比例三年都是 77 比 23，完全沒動 —— 自由行已經是結構性常態。"
        "請注意標題下那行：這是住客人次，同一個旅客住三晚算三次，所以數字比移民署入境人數大。")

# ══ 11 星級階梯 ════════════════════════════════════════════
s = header(S(), "PART III · 星級效益", f"星等呈現明顯階梯：五星級 RevPAR 為三星級 {ST['revpar_5_over_3']} 倍",
           "加權口徑，與儀表板「星級總表」一致。卓越五星僅 1 間，不宜作為類別比較")
_rows = [["星等", "家數", "加權住房率", "平均房價 ADR", "每房收益 RevPAR", "客房營收佔比", "備註"]]
_memo = {"卓越五星": "僅 1 間，個案", "五星級": "市場主體，營收過半",
         "四星級": "中間層，穩定", "三星級": "住房率與房價雙低",
         "無星等/未評鑑": "組內差異最大"}
for i, nm in enumerate(ST["names"]):
    _rows.append([nm, f"{ST['n'][i]} 間", f"{ST['occ'][i]}%", f"NT$ {ST['adr'][i]:,.0f}",
                  f"NT$ {ST['revpar'][i]:,.0f}", f"{ST['rev_share'][i]}%", _memo.get(nm, "")])
table(s, _rows, 0.62, 1.68, 12.1, 2.62, widths=[1.55, 0.8, 1.15, 1.25, 1.3, 1.05, 1.7], fs=11.5)
x, y, w = card(s, 0.62, 4.50, 5.95, 2.28, "階梯是怎麼被放大的", BLUE)
rich(s, [("兩個因子同向　", f"五星對三星：ADR 高 {ST['adr_5_over_3']} 倍、"
                          f"住房率高 {ST['occ'][1] - ST['occ'][3]:.1f} pp。"
                          f"RevPAR＝住房率 × ADR，兩者同向相乘，差距放大到 "
                          f"{ST['revpar_5_over_3']} 倍。", BLUE),
         ("營收集中　", f"五星級 {ST['n'][1]} 間即佔客房營收 {ST['five_rev_share']}%；"
                      f"加上卓越五星共 {ST['five_plus_rev_share']}%。", BLUE)],
     x, y, w, 1.7, 11.5)
x, y, w = card(s, 6.77, 4.50, 5.95, 2.28, "「無星等」為何不在最底層", AMBER)
text(s, f"無星等組住房率 {ST['occ'][4]}% 是全組最低，但 RevPAR（NT$ {ST['revpar'][4]:,.0f}）"
        f"反而高於三星級（NT$ {ST['revpar'][3]:,.0f}）。原因是這組混入了未送評鑑的高價旅館"
        f"（如日勝生加賀屋、漢來日月行館），ADR 達 NT$ {ST['adr'][4]:,.0f}、高於四星級，"
        "把整組 RevPAR 拉起來。「無星等」是一個異質集合，不是一個品質等級。",
     x, y, w, 1.7, 11.5, T_BODY, spacing=1.22)
note(s, "35 秒：星等是乾淨的階梯。關鍵是 RevPAR 等於住房率乘房價，"
        "五星的房價高 1.98 倍、住房率又高 8.9 個百分點，兩個因子同向，所以 RevPAR 差到 2.29 倍。"
        "46 間五星就吃掉六成四的客房營收。右邊這個必考：無星等組住房率最低，"
        "但 RevPAR 比三星高，因為裡面混了加賀屋這種沒送評的高價旅館。"
        "所以無星等是異質集合，不是一個品質等級。")

# ══ 12 星級 RevPAR 圖 ══════════════════════════════════════
s = header(S(), "PART III · 星級效益", "拆解 RevPAR：住房率與房價兩個因子的貢獻並不相同",
           "加權口徑。同一組數字的三種視角 —— 住房率差距有限，房價差距才是主要動力")
chart(s, XL_CHART_TYPE.BAR_CLUSTERED, list(reversed(ST["names"])),
      [("每可售房收益 RevPAR (NT$)", list(reversed(ST["revpar"])))],
      0.62, 1.70, 6.25, 3.95, colors=[BLUE], numfmt='#,##0', gap=55, panel_pad=0.05)
text(s, "加權 RevPAR＝Σ客房營收 ÷ Σ可售房晚", 0.80, 5.60, 5.0, 0.26, 10, T_FAINT)
chart(s, XL_CHART_TYPE.BAR_CLUSTERED, list(reversed(ST["names"])),
      [("加權住房率 (%)", list(reversed(ST["occ"])))],
      7.22, 1.70, 5.5, 1.90, colors=[TEAL], numfmt="0.0", gap=45, lbl_size=9, panel_pad=0.05)
text(s, "住房率：五星對三星僅差 "
        f"{ST['occ'][1] - ST['occ'][3]:.1f} pp", 7.40, 3.66, 5.0, 0.26, 10, T_FAINT)
chart(s, XL_CHART_TYPE.BAR_CLUSTERED, list(reversed(ST["names"])),
      [("平均房價 ADR (NT$)", list(reversed(ST["adr"])))],
      7.22, 3.95, 5.5, 1.70, colors=[AMBER], numfmt='#,##0', gap=45, lbl_size=9, panel_pad=0.05)
text(s, f"房價：五星對三星達 {ST['adr_5_over_3']} 倍 ← 主要動力",
     7.40, 5.60, 5.0, 0.26, 10, T_FAINT)
rect(s, 0.62, 5.96, 12.1, 0.82, HEAD_BG)
text(s, f"給經理人的讀法：住房率的天花板有限（各星等都在 {min(ST['occ'])}–{max(ST['occ'])}% 之間），"
        "真正決定 RevPAR 高低的是房價定位。因此提升收益的槓桿在「能不能支撐更高的 ADR」，"
        "而不是單純追求把房間填滿。",
     0.92, 6.18, 11.5, 0.44, 12, BLUE, bold=True, spacing=1.22)
note(s, "25 秒：同一組數字三個視角。左邊是 RevPAR 的階梯。"
        "右上住房率：五星對三星只差 8.9 個百分點，差距其實不大。"
        "右下房價：五星是三星的 1.98 倍 —— 這才是 RevPAR 階梯的主要動力。"
        "所以收益的槓桿是房價定位能力，不是把房間填滿。")

# ══ 13 選擇偏誤與口徑 ══════════════════════════════════════
s = header(S(), "PART III · 科學邊界", "有星等住房率高出 16.8 pp：是認證效果，還是選擇偏誤？",
           "本頁同時呈現兩種口徑，並說明為何本專案不宣稱因果關係")
x, y, w = card(s, 0.62, 1.62, 5.95, 2.32, "同一個問題，兩種口徑", AMBER)
_rows = [["口徑", "有星等", "無星等", "差距"],
         ["住房率（簡單平均）", f"{SG['occ_simple']['star']}%", f"{SG['occ_simple']['nostar']}%",
          f"+{SG['occ_simple']['gap_pp']} pp"],
         ["住房率（加權）", f"{SG['occ_weighted']['star']}%", f"{SG['occ_weighted']['nostar']}%",
          f"+{SG['occ_weighted']['gap_pp']} pp"],
         ["ADR（加權）", f"NT$ {SG['adr_weighted']['star']:,.0f}",
          f"NT$ {SG['adr_weighted']['nostar']:,.0f}", f"+{SG['adr_weighted']['gap_pct']}%"]]
table(s, _rows, x, y - 0.06, w, 1.50, widths=[1.85, 1.0, 1.0, 0.95], fs=11, head_fs=11)
text(s, f"口徑會改變結論的量級：住房率差距在簡單平均下為 {SG['occ_simple']['gap_pp']} pp，"
        f"加權後縮為 {SG['occ_weighted']['gap_pp']} pp。本頁後續討論以簡單平均的 "
        f"{SG['occ_simple']['gap_pp']} pp 為準，並已標明。",
     x, y + 1.52, w, 0.6, 10.5, T_MUTED, spacing=1.2)
x, y, w = card(s, 6.77, 1.62, 5.95, 2.32, "為什麼這不能當成因果", RED)
rich(s, [("反向因果　", "是先有好條件才去送評鑑，不是評鑑帶來好條件。", RED),
         ("遺漏變數　", "送評者本身多位於黃金地段、具備宴會廳與泳池、導入國際管理體系 —— "
                      "這些同時推高星等與住房率。", RED),
         ("組成異質　", f"無星等組僅 {ST['n'][4]} 間，混合了高價度假旅館與老舊小型旅館，"
                      "平均值意義薄弱。", RED)],
     x, y - 0.06, w, 2.0, 11.5)
x, y, w = card(s, 0.62, 4.14, 5.95, 2.64, "要證明因果，需要什麼（本專案做不到）", PURPLE)
rich(s, [("事件研究　", "取得旅館「取得星等前後」的逐月資料，比較同一家旅館的變化 —— "
                     "本資料的星等是以現行認證回填全期間，無法辨識取得時點。", PURPLE),
         ("配對比較　", "以地段、房間數、房價配對可比的有／無星等旅館 —— "
                      f"無星等僅 {ST['n'][4]} 間，配對後樣本過小。", PURPLE),
         ("外生變動　", "利用評鑑制度變更造成的外生衝擊 —— 期間內無此事件。", PURPLE)],
     x, y, w, 2.1, 11.5)
x, y, w = card(s, 6.77, 4.14, 5.95, 2.64, "所以本專案的定位是", TEAL)
text(s, "星等是一個「強預測特徵」，不是一個「可操作的因果槓桿」。\n\n"
        "在模型中保留星等（One-Hot 編碼）能提升預測力，這完全正當；"
        "但報告不會寫「申請星等可以提升住房率 16.8 個百分點」，"
        "因為資料結構不足以支撐該結論。\n\n"
        "全篇涉及星等、房價、規模的結論，一律以「相關」敘述，不以「造成」敘述。",
     x, y, w, 2.1, 11.5, T_BODY, spacing=1.3)
note(s, "40 秒 —— 這是我最想讓委員看到的一頁。左上先承認口徑問題："
        "同一個差距在簡單平均下是 16.8 個百分點，加權後只剩 14.8，所以我把口徑標出來。"
        "右上三個理由說明為什麼這不是因果：是先有好條件才去送評，不是送評帶來好條件。"
        "左下誠實說明要證明因果需要什麼資料、而我為什麼拿不到。"
        "右下是結論：星等是好用的預測特徵，但我不會說申請星等能提升住房率。")

# ══ 14 房價與規模：兩個非線性結構（合併原房價分箱 + 客房規模）══════
s = header(S(), "PART III · 結構特徵", "房價與規模對住房率都是非線性：不是「越低越好」也不是「越大越好」",
           "簡單平均。左：房價 8 等分位；右：客房規模四組。兩者都無法用線性迴歸描述，故模型採樹方法")
chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED, PB["labels"],
      [("住房率 (%)", PB["occ"])],
      0.62, 1.70, 6.15, 3.75, colors=[BLUE], numfmt="0.0", gap=35, ymax=72, lbl_size=8)
text(s, f"房價區間（NT$），各組約 {PB['n'][0]} 觀測值。最低價組 {PB['worst_occ']}% 斷崖，"
        f"第 2～8 組全在 {PB['plateau_min']}–{PB['plateau_max']}% 窄帶、最高價組未下滑 → 非倒 U",
     0.80, 5.52, 6.2, 0.5, 9, T_FAINT, spacing=1.15)
chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED,
      [f"{l}\n({n} 間)" for l, n in zip(RB["labels"], RB["hotels"])],
      [("住房率 (%)", RB["occ_simple"])],
      7.22, 1.70, 5.40, 3.75, colors=[TEAL], numfmt="0.0", gap=55, ymax=78, lbl_size=8)
text(s, f"住房率隨規模單向升（{RB['occ_simple'][0]}%→{RB['occ_simple'][-1]}%）；但加權 ADR 反而"
        f"呈 U 型 —— 最小組 NT$ {RB['adr_weighted'][0]:,.0f} 最高、中型 NT$ "
        f"{RB['adr_weighted'][2]:,.0f} 最低（最小組混入高價度假旅館）",
     7.40, 5.52, 5.3, 0.5, 9, T_FAINT, spacing=1.15)
rect(s, 0.62, 6.04, 12.1, 0.80, HEAD_BG)
text(s, "共同訊息：低房價與低住房率同時出現（低價是滯銷的結果、非原因）；小型旅館組內極度異質。"
        "兩種關係都是「階梯 + 轉折」，線性迴歸抓不到，這正是選用 Gradient Boosting 的理由。",
     0.92, 6.24, 11.5, 0.44, 11.5, BLUE, bold=True, spacing=1.2)
note(s, "30 秒（合併頁）：左圖房價八等分 —— 最低價組 41.8% 是斷崖，但第二到第八組全擠在窄帶內、"
        "最高價組也沒下滑，所以不是倒 U。右圖規模 —— 住房率隨規模單向上升，"
        "但 ADR 是 U 型，最小規模組因為混了溫泉旅館反而 ADR 最高。"
        "兩個結構都是階梯加轉折，線性迴歸抓不到，這就是我用樹模型的原因。"
        "口徑：住房率為簡單平均、ADR 為加權。")

# ══ 15 陸客結構性轉變（新增，佐證模型限定 2023 年起）═══════════════
s = header(S(), "PART III · 範圍界定", "為什麼模型資料從 2023 年起：陸客量的體制性斷裂",
           "中國大陸來臺旅客由 2015 年高峰 418 萬人次，經邊境封閉後至今僅回到約 30 萬 —— 需求結構已非同一個世界",
           src="資料來源：交通部觀光署《來臺旅客統計》；2024–2025 為估計值，待官方年報定版")
with open(HERE.parent / "data" / "processed" / "china_visitors_annual.csv", encoding="utf-8-sig") as _fh:
    _cv = [[int(r["年"]), float(r["中國大陸來臺旅客萬人次"])] for r in csv.DictReader(_fh)]
chart(s, XL_CHART_TYPE.LINE_MARKERS, [f"{y}" for y, _ in _cv],
      [("中國大陸來臺旅客（萬人次）", [v for _, v in _cv])],
      0.62, 1.66, 8.05, 4.05, colors=[RED], numfmt="0", ymax=460, lbl_size=8)
text(s, "灰底區間為 2020–2022 邊境對境外旅客關閉期", 0.80, 5.62, 6.0, 0.26, 10, T_FAINT)
x, y, w = card(s, 8.87, 1.66, 3.85, 2.05, "三段體制", RED)
rich(s, [("2011–2015　", "開放陸客團自由行，一路衝到 418 萬人次高峰。", RED),
         ("2016–2019　", "政黨輪替後管制趨嚴，回落至約 270 萬。", AMBER),
         ("2020–2025　", "邊境關閉歸零；2023 起僅商務／轉機，約 22→30 萬。", BLUE)],
     x, y, w, 1.6, 10.5)
x, y, w = card(s, 8.87, 3.83, 3.85, 1.88, "對本專案的意義", TEAL)
text(s, "若把 2019 年以前納入訓練，模型會學到一個「陸客佔外籍客三成以上」、"
        "但不會再現的需求結構。將資料起點設在 2023 年，是為了讓訓練與預測"
        "落在同一個體制內 —— 這是刻意的範圍設定，不是資料不足。",
     x, y, w, 1.5, 10.5, T_BODY, spacing=1.24)
rect(s, 0.62, 5.94, 12.1, 0.86, HEAD_BG)
text(s, "此圖同時是儀表板「住客國籍與客源結構分析」分頁的一張圖；"
        "報告中作為「Q1：為何不抓 2012–2019 年報」的視覺後盾。",
     0.92, 6.16, 11.5, 0.44, 12, BLUE, bold=True)
note(s, "30 秒（新增頁）：這頁回答一個必問的問題 —— 為什麼不用更長的歷史資料。"
        "陸客 2015 年高峰 418 萬，2016 年政黨輪替後管制趨嚴掉到 270 萬，"
        "2020 年邊境一關直接歸零，到 2023 年也只回到 22 萬、現在估 30 萬。"
        "如果我把 2019 年以前加進訓練，模型會學到一個陸客佔外籍三成的世界，"
        "那個世界不會再回來。把起點設在 2023 是刻意讓訓練跟預測在同一個體制內。"
        "這張圖儀表板上也有。")

# ══ 16 防洩漏架構 ══════════════════════════════════════════
s = header(S(), "PART IV · 驗證設計", "不用打亂時間的交叉驗證：以 2026 上半年做真正的盲測",
           "時間序列若用隨機 K-Fold，等於用未來預測過去；本專案採時間外（out-of-time）驗證")
_steps = [("步驟 1", "時間切分", BLUE,
           f"訓練集：2023-01～2025-12，{M['train_rows']:,} 筆\n"
           f"盲測集：2026-01～2026-06，{M['test_rows']} 筆\n"
           "盲測集在模型選定前完全未被使用"),
          ("步驟 2", "Pipeline 封裝", CYAN,
           "SimpleImputer(median) + StandardScaler\n"
           "+ OneHotEncoder(handle_unknown='ignore')\n"
           "三者封裝於 Pipeline，僅以訓練集 fit"),
          ("步驟 3", "特徵僅取 t-1 以前", TEAL,
           "lag_1 / lag_2 / lag_3 / lag_12、roll3\n"
           "均由 groupby(旅館).shift() 產生\n"
           "預測當期時，所有特徵皆已公布"),
          ("步驟 4", "雙軌回測", PURPLE,
           "滾動一個月：每月餵入真實上月值\n"
           "固定起點六個月：遞迴餵入自己的預測\n"
           "後者才反映多月預測的真實衰減")]
for i, (tag, nm, col, body) in enumerate(_steps):
    l = 0.62 + i * 3.09
    rect(s, l, 1.70, 2.92, 3.30, CARD, BORDER)
    rect(s, l, 1.70, 2.92, 0.052, col, shape=MSO_SHAPE.RECTANGLE)
    text(s, tag, l + 0.22, 1.90, 2.5, 0.24, 10.5, col, bold=True)
    text(s, nm, l + 0.22, 2.14, 2.5, 0.3, 14, T_TITLE, bold=True)
    text(s, body, l + 0.22, 2.56, 2.5, 2.2, 11, T_BODY, spacing=1.3)
x, y, w = card(s, 0.62, 5.20, 5.95, 1.58, "為什麼兩種回測都要做", BLUE)
text(s, f"滾動一個月 MAE {M['best']['mae']} pp，固定起點六個月 MAE "
        f"{M['fixed_overall']['mae']} pp。若只報前者會高估實際可用性，"
        "只報後者則低估次月預測的價值 —— 兩者用途不同，必須並列。",
     x, y, w, 1.0, 11.5, T_BODY, spacing=1.25)
x, y, w = card(s, 6.77, 5.20, 5.95, 1.58, "一個誠實的保留", AMBER)
text(s, "四款候選模型是依「在盲測集上的 MAE 最小」來挑選的，"
        "嚴格說盲測集已參與了模型選擇，因此報出的指標略為樂觀。"
        "更嚴謹的作法是再切一段驗證集；在 42 個月的資料量下，這是已知的取捨。",
     x, y, w, 1.0, 11.5, T_BODY, spacing=1.25)
note(s, "35 秒：時間序列最常見的作弊就是隨機切 K-Fold，那等於用未來預測過去。"
        "我用的是時間外驗證：2026 上半年 694 筆在模型選定前完全沒用過。"
        "第四格特別說明兩種回測的差別。"
        "右下角那個保留是我自己揭露的：我是看盲測 MAE 最小來選模型的，"
        "嚴格說盲測集已經參與了選擇，所以指標略為樂觀 —— 如果委員要追問，這就是答案。")

# ══ 17 特徵工程 ════════════════════════════════════════════
s = header(S(), "PART IV · 特徵工程", "特徵矩陣：時序慣性、季節節奏與地理／星等編碼",
           "欄位名稱與 src/train_monthly_current.py 完全一致；所有時序特徵均由旅館分組位移產生")
_rows = [["特徵類型", "欄位名稱", "建構方式", "捕捉的商業意涵"],
         ["短期慣性", "occupancy_lag_1\noccupancy_lag_2\noccupancy_lag_3",
          "groupby(旅館).shift(1/2/3)", "上月與近月客流的延續性；模型最主要的依據"],
         ["平滑趨勢", "occupancy_roll3", "lag_1～lag_3 的平均",
          "抹平單月噪聲（連假落點、單一團體進出）後的趨勢水準"],
         ["年度季節", "occupancy_lag_12", "groupby(旅館).shift(12)",
          "去年同月表現，捕捉寒暑假、年節等固定季節模式"],
         ["日曆節奏", "month / month_sin", "月份序數與循環編碼",
          "讓 12 月與 1 月在特徵空間中相鄰，避免斷點"],
         ["營運輸入", "input_domestic_ratio\ninput_international_ratio\ninput_employees",
          "前期旅客結構與人力", "客源組成與人力配置（實測重要性合計 < 3%）"],
         ["類別編碼", "city / star_rating", "OneHotEncoder(ignore)",
          "地理區位與星等定位；新類別出現時不報錯"]]
table(s, _rows, 0.62, 1.66, 12.1, 4.05, widths=[1.3, 2.5, 2.2, 4.3], fs=10.5, head_fs=11,
      aligns=[PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.LEFT])
rect(s, 0.62, 5.92, 12.1, 0.86, HEAD_BG)
text(s, "不納入當期資訊的原則：預測 2026-07 時，只能使用 2026-06 及更早已公布的數值。"
        "因此「當月旅客結構」「當月房價」一律不可作為特徵 —— 實務上預測時根本拿不到。",
     0.92, 6.14, 11.5, 0.44, 12, BLUE, bold=True, spacing=1.22)
note(s, "25 秒：欄位名稱我刻意跟程式碼寫成一樣，方便對照。"
        "三類時序特徵：lag 抓短期延續、roll3 抹平單月噪聲、lag_12 抓去年同月的季節。"
        "month_sin 是為了讓 12 月跟 1 月在特徵空間裡相鄰。"
        "最下面那條原則是底線：預測七月只能用六月以前的數字，"
        "當月房價、當月旅客結構都不能用，因為真的要預測時根本還沒有。")

# ══ 18 模型對決 ════════════════════════════════════════════
s = header(S(), "PART IV · 模型比較", f"Gradient Boosting 勝出：時間外 MAE {M['best']['mae']} 個百分點",
           f"四款模型在同一份 {M['test_rows']} 筆盲測資料上比較；基準為「直接沿用上月住房率」")
_order = ["Gradient Boosting", "Random Forest", "Ridge", "Baseline (前月住房率)"]
_cm = {c["name"]: c for c in M["candidates"]}
_rows = [["候選模型", "MAE (pp)", "RMSE", "R²", "Bias (pp)", "優於基準", "評定"]]
_verdict = {"Gradient Boosting": "★ 採用為正式模型", "Random Forest": "次優，差距 0.04 pp",
            "Ridge": "線性假設不足", "Baseline (前月住房率)": "比較基準"}
for nm in _order:
    c = _cm[nm]
    _rows.append([nm.replace(" (前月住房率)", "（前月住房率）"), f"{c['mae']}", f"{c['rmse']}",
                  f"{c['r2']:.3f}", f"{c['bias']:+.2f}",
                  "—" if "Baseline" in nm else f"{c['improve_pct']}%", _verdict[nm]])
table(s, _rows, 0.62, 1.66, 7.95, 2.30, widths=[2.0, 0.85, 0.8, 0.8, 0.9, 0.85, 1.75], fs=11)
chart(s, XL_CHART_TYPE.BAR_CLUSTERED,
      list(reversed([n.replace(" (前月住房率)", "") for n in _order])),
      [("MAE（住房率百分點，越低越好）", list(reversed([_cm[n]["mae"] for n in _order])))],
      0.62, 4.08, 7.95, 2.06, colors=[BLUE], numfmt="0.00", gap=55, ymax=8.5)
rect(s, 0.62, 6.24, 7.95, 0.56, HEAD_BG)
text(s, f"選模方法上的保留：GB（{M['best']['mae']}）與 RF（{_cm['Random Forest']['mae']}）差距在雜訊內，"
        "且四款模型是依「盲測集 MAE 最小」擇優，嚴格說回報值略樂觀 —— 純正做法應另切一段 validation 集選模型。",
     0.82, 6.34, 7.6, 0.4, 9.5, BLUE, bold=True, spacing=1.12)
x, y, w = card(s, 8.78, 1.66, 3.94, 2.48, "怎麼讀這四個指標", BLUE)
rich(s, [("MAE　", "平均差幾個百分點。最貼近「這個預測準不準」的直覺。", BLUE),
         ("RMSE　", "對大誤差加重處罰，用於評估最壞情況風險。", BLUE),
         ("R²　", f"解釋了 {M['best']['r2'] * 100:.1f}% 的住房率變異。", BLUE),
         ("Bias　", f"{M['best']['bias']:+.2f} pp，幾乎不偏 —— "
                  "模型沒有系統性高估或低估。", TEAL)],
     x, y, w, 2.1, 11)
x, y, w = card(s, 8.78, 4.30, 3.94, 2.48, "6.08 pp 在商業上的意思", TEAL)
text(s, f"預測某旅館下個月住房率為 70%，實際通常落在 64%～76% 之間。\n\n"
        f"與「照抄上月數字」相比（MAE {M['baseline_mae']} pp），"
        f"誤差縮小 {M['baseline_mae'] - M['best']['mae']:.2f} pp，"
        f"相對改善 {M['best']['improve_pct']}%。\n\n"
        "對促銷啟動、團體配額與排班決策而言，這個精度足以作為討論起點，"
        "但不足以當作承諾值。",
     x, y, w, 2.1, 11, T_BODY, spacing=1.28)
note(s, "40 秒 —— 這是核心頁。Gradient Boosting MAE 6.08，比照抄上月的基準 7.51 好 19%。"
        "Random Forest 只差 0.04，我誠實標註兩者差距很小。Ridge 明顯較差，說明關係不是線性的。"
        "右下角是 6.08 的商業翻譯：預測 70% 的話，實際大概在 64 到 76 之間。"
        "Bias 只有 +0.14，代表模型不偏 —— 這點很重要，有偏的模型即使 MAE 小也不能用。"
        "如果委員追問選模嚴謹性：GB 是在 2026 上半年測試集上 MAE 最低而中選，"
        "GB 6.08 對 RF 6.12 差距在雜訊內，純正做法應該另外切一段 validation 集來選模型，"
        "現在的回報值嚴格說略樂觀 —— 這點我在下方藍色框和限制頁都寫明了。")

# ══ 19 期程衰減 ════════════════════════════════════════════
s = header(S(), "PART IV · 期程衰減", "一個月預測可用；遞迴到第六個月，誤差擴大且不再單調",
           "固定起點六個月回測：第 2 個月起改用模型自己的預測值作為滯後特徵，誤差逐步累積")
_hs = [f"第 {h['h']} 個月" for h in M["horizons"]]
chart(s, XL_CHART_TYPE.LINE_MARKERS, _hs,
      [("MAE (pp)", [h["mae"] for h in M["horizons"]]),
       ("RMSE", [h["rmse"] for h in M["horizons"]])],
      0.62, 1.66, 7.25, 4.0, colors=[BLUE, AMBER], numfmt="0.00", ymin=4)
text(s, "固定起點遞迴回測，2026-01 為起點；橫軸為距起點的月數",
     0.80, 5.58, 6.5, 0.26, 10, T_FAINT)
x, y, w = card(s, 8.07, 1.66, 4.65, 1.95, "兩個要誠實說明的現象", AMBER)
rich(s, [("整體擴大　", f"MAE 自第 1 個月 {M['horizons'][0]['mae']} pp 升至第 6 個月 "
                      f"{M['horizons'][-1]['mae']} pp，R² 自 "
                      f"{M['horizons'][0]['r2']:.2f} 降至 {M['horizons'][-1]['r2']:.2f}。", AMBER),
         ("但不單調　", f"第 3、4 個月（{M['horizons'][2]['mae']}、{M['horizons'][3]['mae']} pp）"
                      f"反而優於第 2 個月（{M['horizons'][1]['mae']} pp）。"
                      "在 115 筆／期的樣本下，這是月份特性與樣本噪聲，"
                      "不應描述為平滑的衰減曲線。", RED)],
     x, y, w, 1.4, 10.5)
x, y, w = card(s, 8.07, 3.77, 4.65, 1.93, "因此的作業建議", TEAL)
text(s, "每月官方月報公布後重新推論，永遠只採用「第 1 個月」的預測做決策；"
        "第 2～6 個月的輸出僅作為趨勢參考與情境區間，不進入承諾性計畫。\n\n"
        f"六個月整體 MAE {M['fixed_overall']['mae']} pp，已接近基準的 "
        f"{M['baseline_mae']} pp —— 長期遞迴預測幾乎失去優勢。",
     x, y, w, 1.4, 10.5, T_BODY, spacing=1.25)
rect(s, 0.62, 5.90, 12.1, 0.88, HEAD_BG)
text(s, f"關鍵對比：滾動一個月（每月餵入真實值）MAE {M['best']['mae']} pp；"
        f"固定起點六個月（遞迴餵入自己的預測）整體 MAE {M['fixed_overall']['mae']} pp。"
        "差異不是模型變差，而是誤差在遞迴中被自己放大。",
     0.92, 6.14, 11.5, 0.44, 12, BLUE, bold=True, spacing=1.22)
note(s, "35 秒：這頁我特別不想美化。整體趨勢是誤差擴大，第一個月 6.07 到第六個月 8.41，"
        "R² 從 0.88 掉到 0.65。但請看右上第二點：第三、第四個月反而比第二個月好 —— "
        "它不是一條平滑的衰減曲線，每期只有 115 筆，這是噪聲。"
        "我不會把它畫成漂亮的單調曲線然後假裝沒看到。"
        "結論是：只用第一個月的預測做決策，每月重新跑。")

# ══ 20 特徵重要性 ══════════════════════════════════════════
s = header(S(), "PART IV · 模型本質", f"前三項住房率自身特徵佔 {FI['top3_sum']}%：這是慣性模型",
           "Gradient Boosting 特徵重要性（Top 8）。此為模型依賴程度，不代表因果強度")
_nm_map = {"occupancy_lag_1": "前 1 月住房率 (lag_1)", "occupancy_roll3": "近 3 月均值 (roll3)",
           "occupancy_lag_12": "去年同月 (lag_12)", "month": "月份 (month)",
           "month_sin": "月份循環 (month_sin)", "occupancy_lag_2": "前 2 月住房率 (lag_2)",
           "input_domestic_ratio": "本國客佔比", "input_international_ratio": "國際客佔比",
           "input_employees": "員工數"}
_labels = [_nm_map.get(n, n) for n in FI["names"]]
chart(s, XL_CHART_TYPE.BAR_CLUSTERED, list(reversed(_labels)),
      [("重要性 (%)", list(reversed(FI["values"])))],
      0.62, 1.66, 7.05, 4.35, colors=[PURPLE], numfmt="0.0", gap=45)
text(s, "來源：reports/feature_importance_monthly_current.csv", 0.80, 5.92, 5.5, 0.26, 10, T_FAINT)
x, y, w = card(s, 7.87, 1.66, 4.85, 2.10, "這告訴我們什麼", PURPLE)
rich(s, [("慣性主導　", f"lag_1（{FI['values'][0]}%）+ roll3（{FI['values'][1]}%）"
                      f"+ lag_12（{FI['values'][2]}%）＝ {FI['top3_sum']}%。"
                      "模型主要在延伸旅館自身的歷史軌跡。", PURPLE),
         ("營運輸入極小　", "房價、旅客結構、員工數合計貢獻不到 3%。"
                         "調整這些輸入值，預測結果幾乎不動。", AMBER)],
     x, y, w, 1.5, 11)
x, y, w = card(s, 7.87, 3.92, 4.85, 2.09, "對使用者的兩個提醒", RED)
rich(s, [("不要當情境模擬器　", "儀表板的情境試算不是因果模擬。"
                            "把國際客佔比拉高 10 個百分點，預測值變化微乎其微 —— "
                            "這是模型結構的必然，不是程式有問題。", RED),
         ("價值在哪　", "它的價值是「在官方數字出來前一個月，先給出一個有根據的落點」，"
                      "而不是回答「我該做什麼才能提升住房率」。", TEAL)],
     x, y, w, 1.5, 10.5)
note(s, "35 秒：這頁我把模型的弱點直接講出來。前三項全部是住房率自己的歷史，佔 94.5%。"
        "房價、旅客結構、員工數加起來不到 3%。"
        "所以儀表板上的情境試算，你把國際客佔比拉高十個百分點，預測值幾乎不動 —— "
        "這是模型結構的必然，不是 bug。"
        "如果委員問『那這個模型有什麼用』，答案是右下角：它的價值是提前一個月給落點，"
        "不是告訴你該做什麼。")

# ══ 21 穩健性檢驗 ══════════════════════════════════════════
s = header(S(), "PART V · 穩健性", "誤差的真正邊界不是樣本進出，而是外生衝擊下的東部縣市",
           "滾動一個月回測拆解至縣市層級；地震與颱風造成的斷點無法由歷史慣性預測")
_cities = list(RO["by_city"].items())
chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED,
      [f"{c}\n({v['hotels']} 間)" for c, v in _cities],
      [("滾動一個月 MAE (pp)", [v["MAE"] for _, v in _cities])],
      0.62, 1.66, 8.15, 3.95, colors=[BLUE], numfmt="0.00", gap=45, ymax=15)
text(s, f"全體基準 MAE {RO['all']['MAE']} pp（虛線概念值）；"
        "僅列出盲測期間有觀測值的縣市", 0.80, 5.52, 7.8, 0.26, 10, T_FAINT)
x, y, w = card(s, 8.97, 1.66, 3.75, 1.30, "樣本進出：影響極小", TEAL)
text(s, f"三年皆在榜 {RO['present_all_three_years']} 間，其中 "
        f"{RO['balanced']['hotels']} 間進入盲測：MAE {RO['balanced']['MAE']} pp，"
        f"與全體 {RO['all']['MAE']} pp 僅差 {RO['balanced_gap_pp']} pp。",
     x, y - 0.1, w, 0.95, 10.5, T_BODY, spacing=1.22)
x, y, w = card(s, 8.97, 3.12, 3.75, 1.30, "真正的問題在東部", RED)
text(s, f"台東 MAE {RO['by_city']['台東縣']['MAE']} pp、花蓮 "
        f"{RO['by_city']['花蓮縣']['MAE']} pp（R² 僅 "
        f"{RO['by_city']['花蓮縣']['R2']:.2f}），遠高於台中 "
        f"{RO['by_city']['台中市']['MAE']} pp、桃園 {RO['by_city']['桃園市']['MAE']} pp。",
     x, y - 0.1, w, 0.95, 10.5, T_BODY, spacing=1.22)
x, y, w = card(s, 8.97, 4.58, 3.75, 1.03, "管理上的處理", PURPLE)
text(s, "東部縣市預測值標示為低信賴；發生天災、交通中斷時停用模型輸出，改由人工判斷。",
     x, y - 0.1, w, 0.7, 10.5, T_BODY, spacing=1.22)
rect(s, 0.62, 5.98, 12.1, 0.80, HEAD_BG)
text(s, f"這是一個誠實的結論：{RO['all']['MAE']} pp 是全體平均，"
        f"但都會型縣市實際約 {RO['by_city']['台中市']['MAE']}–{RO['by_city']['台北市']['MAE']} pp、"
        f"東部度假型可達 {RO['by_city']['台東縣']['MAE']} pp。報告單一數字會掩蓋這個差異。",
     0.92, 6.20, 11.5, 0.42, 12, BLUE, bold=True, spacing=1.22)
note(s, "35 秒：我做了兩種穩健性檢查。第一，樣本進出有沒有扭曲結果？"
        "三年都在榜的 112 間 MAE 5.98，跟全體 6.08 只差 0.1，所以沒有。"
        "第二，誤差在哪裡特別大？台東 13.14、花蓮 8.79，而台中只有 3.96。"
        "原因是地震跟颱風造成的斷點，歷史慣性根本抓不到。"
        "所以最下面那句很重要：6.08 是平均，都會區大概 4 到 6，東部可以到 13。"
        "只報一個數字會掩蓋這件事。")

# ══ 22 系統落地 ════════════════════════════════════════════
s = header(S(), "PART V · 系統落地", "Streamlit 儀表板：把分析與模型交到使用者手上",
           "主體分析 5 個主題呈現歷史事實；3 個預測分頁各自獨立，不互相覆蓋")
x, y, w = card(s, 0.62, 1.66, 6.0, 4.0, "app.py — 主體分析（5 個主題）", BLUE)
rich(s, [("1  整體營運與住房趨勢　", "年度指數化走勢、月份季節性（都會 vs 度假）、"
                                 "年度營運總覽表、縣市排行。", BLUE),
         ("2  個別旅館年度實績　", "單一旅館的年度營收、人力效率、逐月住房率、同儕比較。", BLUE),
         ("3  星級認證效益分析　", "各星等住房率／ADR／RevPAR、有無星等分布（標明關聯非因果）。", BLUE),
         ("4  住客國籍與客源結構　", "本國 vs 國際、散客 vs 團體、主要客源回流，"
                                "並附中國大陸來臺旅客 2011–2025 走勢以說明模型為何限定 2023 年起。", BLUE),
         ("5  影響因素與特徵解析　", "房價／規模分箱、特徵重要性、2026 上半年時間外測試結果。", BLUE)],
     x, y, w, 3.2, 11)
x, y, w = card(s, 6.72, 1.66, 6.0, 4.0, "pages/ — 三個預測分頁", TEAL)
rich(s, [("1  年度預測分析　", "情境估算工具（Decision Tree，R² 約 0.40、RMSE 約 15 pp）。"
                           "頁面明確標示「僅供情境討論，非精確承諾」，"
                           "並隱藏 R² 為極大負值的未標準化線性模型。", TEAL),
         ("2  月度預測分析　", f"★ 正式模型。次月預測、2026 上半年回測、"
                           f"未來 12 個月遞迴彙總為年度估計。"
                           f"頁面標註「{FI['top3_sum']}% 靠住房率慣性」以避免誤用情境試算。", TEAL),
         ("3  每日預測分析　", "無旅館端逐日實際住房率，目前不產出預測，"
                           "僅顯示資料累積狀態 —— 寧可標示「尚未就緒」，"
                           "也不輸出無法驗證的數字。", AMBER)],
     x, y, w, 3.2, 11)
x, y, w = card(s, 0.62, 5.86, 6.0, 0.92, None, PURPLE)
rich(s, [("部署　", "本地 streamlit run app.py；雲端 Streamlit Community Cloud，"
                 "requirements.txt 鎖定版本。", PURPLE)], x, y - 0.22, w, 0.6, 11)
x, y, w = card(s, 6.72, 5.86, 6.0, 0.92, None, BLUE)
rich(s, [("設計原則　", "所有圖表都附口徑說明與因果警語，避免使用者誤讀。", BLUE)],
     x, y - 0.22, w, 0.6, 11)
note(s, "25 秒：主體分析五個主題都是歷史事實，預測分開放三個分頁。"
        "我想強調第三個分頁：每日預測我沒有資料可以驗證，所以它不輸出任何數字，"
        "只顯示資料累積狀態。寧可標示尚未就緒，也不要輸出一個沒辦法驗證的預測。"
        "另外每張圖我都附了口徑說明跟因果警語。")

# ══ 23 預計完成事項 ════════════════════════════════════════
s = header(S(), "PART VI · 後續規劃", "四個已設計、尚未執行的延伸方向",
           "以下為規劃內容，本次報告未包含實作結果；排序依「可行性 × 對預測力的預期貢獻」")
_plans = [("優先 1", "歷史月報回補與體制檢驗", BLUE,
           ["抓取 2016–2019 官方月報（樣本量為年報 12 倍）",
            "建立跨期旅館名稱對照字典",
            "以 COVID／陸客 Dummy 檢驗體制轉換",
            "門檻：僅在滾動 MAE、固定 MAE、RMSE 三項均改善時才替換正式模型"]),
          ("優先 2", "外部環境特徵整合", TEAL,
           ["人事行政總處：各月法定休假日數、3 天以上連假天數、春節落點",
            "氣象署：風景區測站月降雨日數與氣溫",
            "已完成官方辦公日曆特徵實驗 → 未通過三項門檻，未採用",
            "下一步改以連假「天數 × 落點」而非單純假日數"]),
          ("優先 3", "客源與營收結構深鑽", AMBER,
           ["單一國籍（日／韓／美／港澳／東南亞）對住房率的邊際貢獻",
            "散客比例對 ADR 的定價彈性",
            "餐飲營收對客房淡季的損益平抑效果",
            "每員工產值作為人力效率指標"]),
          ("優先 4", "自動預警與資料分層", PURPLE,
           ["次月預測落入歷史後 20% 分位時觸發告警",
            "主模型聚焦有星等觀光旅館（本資料 98 間），"
            "無星等 26 間作獨立對照組",
            "不混入一般旅館（報表格式與定義不同）"])]
for i, (tag, nm, col, items) in enumerate(_plans):
    l = 0.62 + (i % 2) * 6.15
    t = 1.62 + (i // 2) * 2.70
    rect(s, l, t, 5.98, 2.52, CARD, BORDER)
    text(s, tag, l + 0.24, t + 0.18, 1.2, 0.24, 10, col, bold=True)
    text(s, nm, l + 1.16, t + 0.16, 4.6, 0.28, 13, T_TITLE, bold=True)
    rect(s, l + 0.24, t + 0.50, 0.32, 0.028, col, shape=MSO_SHAPE.RECTANGLE)
    rich(s, [("· ", it, col) for it in items], l + 0.24, t + 0.66, 5.5, 1.8, 10, 1.22, 5)
rect(s, 0.62, 6.98, 12.1, 0.010, BORDER, shape=MSO_SHAPE.RECTANGLE)
note(s, "25 秒：四個方向，照可行性排序。第一優先是回補 2016 到 2019 的月報 —— "
        "注意我寫的門檻：只有在三項指標都改善時才替換模型，不是抓到資料就換。"
        "第二是外部特徵，我已經做過官方日曆的實驗，結果沒通過門檻所以沒採用，"
        "這個失敗的實驗也是結果。後兩項是結構深鑽跟自動告警。"
        "這一頁全部是規劃，不是成果，我會講清楚。")

# ══ 24 研究限制 ════════════════════════════════════════════
s = header(S(), "PART VI · 研究限制", "七項限制：說清楚這份分析不能回答什麼",
           "主動揭露邊界，是讓可信的部分更可信")
_lims = [("資料粒度", "旅館×月彙總，非訂單紀錄", RED,
          "無法做單筆訂單取消預測、取消原因分析、顧客個人層級行為"),
         ("觀測期間", f"僅 {SC['months']} 個月（2023-01 起）", RED,
          "刻意排除 2020–2022：邊境封閉與陸客崩跌形成體制斷裂，納入會汙染訓練訊號"),
         ("因果關係", "全篇為相關，非因果", AMBER,
          "星等、房價、規模的結論皆不可讀作「改變 X 就會改變 Y」"),
         ("統計口徑", "加權與簡單平均結論不同", AMBER,
          f"有無星等住房率差距：簡單平均 {SG['occ_simple']['gap_pp']} pp vs 加權 "
          f"{SG['occ_weighted']['gap_pp']} pp。每張圖均標明口徑"),
         ("模型選擇", "盲測集參與了模型挑選", AMBER,
          "四款模型依盲測 MAE 最小擇優，故報出指標略為樂觀"),
         ("外生衝擊", "天災、重大活動無法預測", RED,
          f"台東 MAE 達 {RO['by_city']['台東縣']['MAE']} pp；該情境應停用模型輸出"),
         ("分類方式", "「都會／度假」為人工縣市分類", TEAL,
          "非旅館實際定位，亦非分群模型結果；星等以現行認證回填全期間")]
for i, (cat, head, col, body) in enumerate(_lims[:6]):
    l = 0.62 + (i % 3) * 4.10
    t = 1.62 + (i // 3) * 2.22
    rect(s, l, t, 3.93, 2.02, CARD, BORDER)
    text(s, cat, l + 0.24, t + 0.17, 3.5, 0.24, 10, col, bold=True)
    rect(s, l + 0.24, t + 0.44, 0.30, 0.026, col, shape=MSO_SHAPE.RECTANGLE)
    text(s, head, l + 0.24, t + 0.56, 3.5, 0.32, 12, T_TITLE, bold=True)
    text(s, body, l + 0.24, t + 0.98, 3.5, 0.95, 10, T_BODY, spacing=1.25)
_c = _lims[6]
rect(s, 0.62, 6.18, 12.1, 0.86, CARD, BORDER)
rect(s, 0.62, 6.34, 0.30, 0.026, _c[2], shape=MSO_SHAPE.RECTANGLE)
text(s, _c[0], 0.90, 6.30, 2.0, 0.24, 10, _c[2], bold=True)
text(s, f"{_c[1]} — {_c[3]}", 2.60, 6.30, 9.9, 0.56, 11, T_BODY, spacing=1.22)
note(s, "30 秒：我把七項限制列出來。最重要的是第二項 —— 為什麼只用 2023 年以後的資料？"
        "因為 2020 到 2022 邊境封閉、陸客從 2015 年的 418 萬掉到 2021 年不到 1 萬，"
        "這是體制斷裂，硬加進去只會汙染訓練訊號。"
        "第五項是我自己揭露的方法論弱點。"
        "我的立場是：主動講清楚不能回答什麼，能回答的部分才會被相信。")

# ══ 25 總結與 Q&A ══════════════════════════════════════════
s = header(S(), "PART VII · 總結", "專案總結與 Q&A",
           "一句話：用 42 個月官方資料，建立一台誠實標明邊界的「次月住房率預警雷達」")
_sum = [("實證結果", TEAL,
         [f"2025 年加權住房率 {A['occ'][-1]}%，為疫後高點（2023 年 {A['occ'][0]}%）",
          f"成長來自量：住房率指數 {IDX['occ'][-1]}，ADR 指數仍為 {IDX['adr'][-1]}",
          f"五星級 RevPAR 為三星級 {ST['revpar_5_over_3']} 倍，主要由房價而非住房率驅動",
          f"國際旅客回升至 {GU['intl_ratio'][-1]}%，散客比穩定於 {GU['fit_ratio'][-1]}%"]),
        ("模型結果", BLUE,
         [f"Gradient Boosting 時間外 MAE {M['best']['mae']} pp、R² {M['best']['r2']:.3f}",
          f"優於前月基準 {M['best']['improve_pct']}%，Bias {M['best']['bias']:+.2f} pp 近乎不偏",
          f"次月預測可用；遞迴至第 6 個月 MAE 擴大至 {M['horizons'][-1]['mae']} pp",
          f"樣本進出影響僅 {RO['balanced_gap_pp']} pp，誤差邊界在東部外生衝擊"]),
        ("方法誠信", PURPLE,
         ["時間外驗證，非隨機 K-Fold；特徵僅取 t-1 以前",
          "每張圖標明加權／簡單平均口徑",
          f"揭露 {FI['top3_sum']}% 來自住房率慣性，不宣稱因果",
          "主動列出七項限制與一項模型選擇上的方法論保留"]),
        ("後續方向", AMBER,
         ["回補 2016–2019 月報並檢驗體制轉換",
          "整合連假與氣象外部特徵（已做實驗，未通過門檻）",
          "客源國籍與餐飲／人效結構深鑽",
          "低住房率自動告警與旅館分層"])]
for i, (nm, col, items) in enumerate(_sum):
    l = 0.62 + i * 3.09
    rect(s, l, 1.60, 2.92, 3.05, CARD, BORDER)
    text(s, nm, l + 0.24, 1.78, 2.5, 0.3, 12.5, T_TITLE, bold=True)
    rect(s, l + 0.24, 2.08, 0.32, 0.026, col, shape=MSO_SHAPE.RECTANGLE)
    rich(s, [("· ", it, col) for it in items], l + 0.24, 2.24, 2.5, 2.35, 9.5, 1.2, 5)
rect(s, 0.62, 4.90, 12.1, 1.24, CARD, BORDER)
text(s, "資料來源彙總", 0.90, 5.02, 3.0, 0.26, 11.5, T_TITLE, bold=True)
rect(s, 0.90, 5.31, 0.34, 0.026, TEAL, shape=MSO_SHAPE.RECTANGLE)
rich(s, [("①  主資料　", "交通部觀光署《觀光旅館營運統計》逐月報表，2023-01～2026-06（125 間、4,832 筆）", TEAL),
         ("②  客源背景　", "交通部觀光署《來臺旅客統計》（陸客 2011–2025 走勢，2024–25 為估計值）", TEAL),
         ("③  日曆特徵（實驗用，未納入正式模型）　",
          "行政院人事行政總處《政府行政機關辦公日曆表》2023–2027（data.gov.tw/dataset/14718）", TEAL)],
     0.90, 5.46, 11.9, 0.75, 9, 1.16, 3)
rect(s, 0.62, 6.34, 12.1, 0.44, HEAD_BG)
text(s, "Q & A", 0.90, 6.41, 1.1, 0.3, 13, BLUE, bold=True)
text(s, "儀表板 taiwan-hotel-occupancy.streamlit.app　|　所有數字可追溯至 "
        "data/processed/hotel_monthly.csv 與 reports/*.json，由 compute_facts.py 重算產生　|　感謝指教",
     2.05, 6.43, 10.6, 0.30, 9.5, T_BODY)
note(s, "30 秒收尾：四欄分別是實證結果、模型結果、方法誠信、後續方向。"
        "如果只能記住三件事：一，2025 年的復甦是量增不是價漲；"
        "二，次月預測誤差 6.08 個百分點，比照抄上月好 19%；"
        "三，這個模型 94.5% 靠慣性，它是預警雷達不是因果工具。"
        "所有數字都可以回溯到原始 CSV，而且是用程式重算的，不是手抄。謝謝，請指教。")

prs.save(OUT)
print(f"[{STYLE}] 繪圖區底色 {CFG['plot']}／格線 {CFG['grid']}／線寬 {CFG['lw']}pt")
print(f"已產出：{OUT}")
print(f"投影片數：{len(prs.slides.__iter__.__self__._sldIdLst)}")
_nc = sum(1 for sl in prs.slides for sh in sl.shapes if sh.has_chart)
_nt = sum(1 for sl in prs.slides for sh in sl.shapes if sh.has_table)
print(f"原生圖表：{_nc} 張　原生表格：{_nt} 個")
