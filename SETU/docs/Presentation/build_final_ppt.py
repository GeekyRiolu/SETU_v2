#!/usr/bin/env python3
"""Build the Project Phase-II final presentation.

Starts from the interim deck (SETU_updated.pptx), keeps its look, and brings it
in line with the department's Phase-II final template:

  * every section the final template asks for (literature summary, problem
    input/output, component design, results and performance analysis,
    snapshots, applications, future scope, publications) is added;
  * text is updated to the final report (all 22 languages, SeqKD finding);
  * every diagram is replaced by the one in the final report (assets/).

    python3 build_final_ppt.py [BASE.pptx] [OUT.pptx]

Defaults: ~/Downloads/SETU_updated.pptx -> ~/Downloads/SETU_Phase-II_Final_Presentation.pptx
Needs python-pptx and Pillow.
"""
import copy
import os
import sys
import tempfile

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, PP_PLACEHOLDER
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
BASE = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads/SETU_updated.pptx")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser(
    "~/Downloads/SETU_Phase-II_Final_Presentation.pptx")

TNR = "Times New Roman"
BLUE = RGBColor(0x4E, 0x67, 0xC8)      # the deck's title colour
INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x59, 0x59, 0x59)
CARD = RGBColor(0xEE, 0xF1, 0xFA)       # light tint of the title blue
HEAD = RGBColor(0x44, 0x72, 0xC4)       # table header blue used by the deck
ROW1 = RGBColor(0xCF, 0xD5, 0xEA)
ROW2 = RGBColor(0xE9, 0xEB, 0xF5)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREEN = RGBColor(0x2E, 0x7D, 0x32)
AMBER = RGBColor(0xB2, 0x6A, 0x00)
TERM = RGBColor(0x1E, 0x1E, 0x2E)
TERM_TXT = RGBColor(0xE6, 0xE6, 0xE6)
TERM_CMD = RGBColor(0x7F, 0xD1, 0xB9)

# content area: clear of the title above and the teal corner triangle below
L, R = Inches(0.5), Inches(9.5)
TOP, BOTTOM = Inches(1.05), Inches(6.25)


def A(name):
    return os.path.join(ASSETS, name)


# ------------------------------------------------------------------ text ---
def _fonts(rPr, face):
    for tag in ("a:latin", "a:ea", "a:cs", "a:sym"):
        el = rPr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rPr, qn(tag))
        el.set("typeface", face)


def add_run(p, text, size=18, bold=False, italic=False, color=INK, face=TNR):
    r = p.add_run()
    r.text = text
    f = r.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    if color is not None:
        f.color.rgb = color
    rPr = r._r.get_or_add_rPr()
    _fonts(rPr, face)
    return r


def fresh(tf, anchor=MSO_ANCHOR.TOP, margins=None, wrap=True):
    """Remove every paragraph so the caller starts from a clean frame."""
    body = tf._txBody
    for p in body.findall(qn("a:p")):
        body.remove(p)
    tf.word_wrap = wrap
    tf.vertical_anchor = anchor
    bp = body.find(qn("a:bodyPr"))
    for child in list(bp):
        if child.tag in (qn("a:spAutoFit"), qn("a:normAutofit")):
            bp.remove(child)
    if bp.find(qn("a:noAutofit")) is None:
        etree.SubElement(bp, qn("a:noAutofit"))
    if margins is not None:
        tf.margin_left = tf.margin_right = margins[0]
        tf.margin_top = tf.margin_bottom = margins[1]
    return tf


def para(tf, runs, size=18, bullet=None, level=0, before=6, line=1.0,
         align=PP_ALIGN.LEFT, color=INK, face=TNR):
    """runs: str, or list of str / (text, {bold, italic, color, size, face})."""
    p = tf.add_paragraph()
    p.alignment = align
    pPr = p._p.get_or_add_pPr()
    ln = etree.SubElement(pPr, qn("a:lnSpc"))
    etree.SubElement(ln, qn("a:spcPct")).set("val", str(int(line * 100000)))
    sb = etree.SubElement(pPr, qn("a:spcBef"))
    etree.SubElement(sb, qn("a:spcPts")).set("val", str(int(before * 100)))
    sa = etree.SubElement(pPr, qn("a:spcAft"))
    etree.SubElement(sa, qn("a:spcPts")).set("val", "0")
    if bullet:
        ind = 0.30 if level == 0 else 0.28
        pPr.set("marL", str(int(Inches(0.30 + 0.32 * level))))
        pPr.set("indent", str(-int(Inches(ind))))
        etree.SubElement(pPr, qn("a:buClr")).append(_srgb(color if bullet != "num" else BLUE))
        etree.SubElement(pPr, qn("a:buSzPct")).set("val", "100000")
        etree.SubElement(pPr, qn("a:buFont")).set("typeface", TNR)
        if bullet == "num":
            etree.SubElement(pPr, qn("a:buAutoNum")).set("type", "arabicPeriod")
        else:
            etree.SubElement(pPr, qn("a:buChar")).set("char", bullet)
    else:
        pPr.set("marL", "0")
        pPr.set("indent", "0")
        etree.SubElement(pPr, qn("a:buNone"))
    if isinstance(runs, str):
        runs = [runs]
    for item in runs:
        text, o = (item, {}) if isinstance(item, str) else item
        add_run(p, text, size=o.get("size", size), bold=o.get("bold", False),
                italic=o.get("italic", False), color=o.get("color", color),
                face=o.get("face", face))
    return p


def _srgb(rgb):
    el = etree.Element(qn("a:srgbClr"))
    el.set("val", str(rgb))
    return el


def textbox(slide, x, y, w, h, name=None, anchor=MSO_ANCHOR.TOP, margins=(Inches(0.05), Inches(0.03))):
    tb = slide.shapes.add_textbox(x, y, w, h)
    if name:
        tb.name = name
    fresh(tb.text_frame, anchor=anchor, margins=margins)
    return tb.text_frame


def bullets(slide, items, x=L, y=TOP, w=None, h=None, size=18, before=8, line=1.0,
            mark="●", name="Body"):
    w = w or (R - x)
    h = h or (BOTTOM - y)
    tf = textbox(slide, x, y, w, h, name=name)
    for it in items:
        level = 0
        if isinstance(it, tuple) and it and it[0] == "sub":
            level, it = 1, it[1]
        if isinstance(it, tuple):           # (label, text)
            runs = [(it[0] + " ", {"bold": True}), it[1]]
        else:
            runs = it
        para(tf, runs, size=size if level == 0 else size - 2, level=level,
             bullet=(mark if level == 0 else "◦") if mark else None,
             before=before if level == 0 else 3, line=line)
    return tf


# ---------------------------------------------------------------- shapes ---
def card(slide, x, y, w, h, head=None, body=None, fill=CARD, head_color=BLUE,
         body_color=INK, head_size=15, body_size=13, name="Card", align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    shp.name = name
    shp.adjustments[0] = 0.07
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.line.fill.background()
    shp.shadow.inherit = False
    tf = fresh(shp.text_frame, anchor=anchor, margins=(Inches(0.12), Inches(0.07)))
    if head:
        para(tf, [(head, {"bold": True})], size=head_size, color=head_color, before=0, align=align)
    if body:
        for i, b in enumerate(body if isinstance(body, list) else [body]):
            para(tf, b, size=body_size, color=body_color, before=3 if (head or i) else 0,
                 line=1.0, align=align)
    return shp


def stat(slide, x, y, w, h, number, label, num_size=30, label_size=12, fill=CARD,
         num_color=BLUE, name="Stat"):
    shp = card(slide, x, y, w, h, fill=fill, name=name, anchor=MSO_ANCHOR.MIDDLE)
    tf = shp.text_frame
    para(tf, [(number, {"bold": True})], size=num_size, color=num_color, before=0,
         align=PP_ALIGN.CENTER)
    para(tf, label, size=label_size, color=MUTED, before=2, align=PP_ALIGN.CENTER)
    return shp


def picture(slide, path, x, y, w, h, name=None, align="center"):
    iw, ih = Image.open(path).size
    s = min(w / iw, h / ih)
    pw, ph = int(iw * s), int(ih * s)
    px = x + (w - pw) // 2 if align == "center" else x
    pic = slide.shapes.add_picture(path, px, y + (h - ph) // 2 if align == "center" else y, pw, ph)
    if name:
        pic.name = name
    pic._element.nvPicPr.cNvPr.set("descr", name or os.path.basename(path))
    return pic


def caption(slide, text, y, x=L, w=None, size=12):
    tf = textbox(slide, x, y, w or (R - x), Inches(0.32), name="Caption")
    para(tf, [(text, {"italic": True})], size=size, color=MUTED, before=0, align=PP_ALIGN.CENTER)
    return tf


def arrow(slide, x, y, w, h):
    a = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x, y, w, h)
    a.fill.solid()
    a.fill.fore_color.rgb = BLUE
    a.line.fill.background()
    a.shadow.inherit = False
    a.name = "Arrow"
    return a


def table(slide, rows, x, y, w, col_w, row_h=Inches(0.36), size=13, head_size=13,
          name="Table", fills=(ROW1, ROW2), bold_first_col=False, colors=None):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), x, y, w, row_h * len(rows))
    shape.name = name
    tbl = shape.table
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = cw
    for r, row in enumerate(rows):
        tbl.rows[r].height = row_h
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = HEAD if r == 0 else fills[(r - 1) % 2]
            tf = fresh(cell.text_frame, anchor=MSO_ANCHOR.MIDDLE)
            col = WHITE if r == 0 else (colors.get((r, c), INK) if colors else INK)
            para(tf, [(val, {"bold": r == 0 or (bold_first_col and c == 0) or
                             (colors is not None and (r, c) in colors)})],
                 size=head_size if r == 0 else size, color=col, before=0)
    return shape


def terminal(slide, x, y, w, h, title, lines, size=14):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    shp.name = "Terminal"
    shp.adjustments[0] = 0.04
    shp.fill.solid()
    shp.fill.fore_color.rgb = TERM
    shp.line.fill.background()
    shp.shadow.inherit = False
    tf = fresh(shp.text_frame, margins=(Inches(0.16), Inches(0.1)))
    para(tf, [(title, {"bold": True})], size=size + 1, color=WHITE, before=0, face=TNR)
    for kind, text in lines:
        para(tf, text, size=size, color=TERM_CMD if kind == "$" else TERM_TXT,
             before=6 if kind == "$" else 1)
    return shp


# ----------------------------------------------------------------- slides ---
def set_title(slide, text):
    t = slide.shapes.title
    t.left, t.top, t.width, t.height = Emu(457200), Emu(193425), Emu(8229600), Emu(703500)
    tf = fresh(t.text_frame, anchor=MSO_ANCHOR.MIDDLE)
    para(tf, text, size=36, color=BLUE, before=0)
    return t


def drop(shape):
    el = shape._element
    el.getparent().remove(el)


def drop_body(slide):
    for ph in list(slide.placeholders):
        if ph.placeholder_format.type not in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE):
            drop(ph)


def drop_pictures(slide):
    for shp in list(slide.shapes):
        if shp.shape_type == 13:  # picture
            drop(shp)


def body_of(slide):
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == 1:
            return ph
    raise LookupError("no body placeholder")


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


INDIC_FONT = "Nirmala UI"   # ships with Windows; covers every Indic script used here
_RPR_AFTER_CS = ("a:sym", "a:hlinkClick", "a:hlinkMouseOver", "a:rtl", "a:extLst")


def one_font(slide):
    """Times New Roman for every run; Indic runs keep an Indic complex-script font."""
    for r in slide._element.iter(qn("a:r")):
        rPr = r.find(qn("a:rPr"))
        if rPr is None:
            rPr = etree.Element(qn("a:rPr"))
            r.insert(0, rPr)
        _fonts(rPr, TNR)


def tag_indic(slide):
    """Point every run holding Indic script at an Indic-capable complex-script font."""
    for r in slide._element.iter(qn("a:r")):
        t = r.find(qn("a:t"))
        if t is None or not t.text or not any("ऀ" <= ch <= "෿" for ch in t.text):
            continue
        rPr = r.find(qn("a:rPr"))
        if rPr is None:
            rPr = etree.Element(qn("a:rPr"))
            r.insert(0, rPr)
        cs = rPr.find(qn("a:cs"))
        if cs is None:
            cs = etree.Element(qn("a:cs"))
            nxt = next((rPr.find(qn(tag)) for tag in _RPR_AFTER_CS
                        if rPr.find(qn(tag)) is not None), None)
            if nxt is not None:
                nxt.addprevious(cs)
            else:
                rPr.append(cs)
        cs.set("typeface", INDIC_FONT)


def steps(slide, header, items, y=TOP, size=17, name="Algorithm"):
    """header: list of (label, text); items: list of (number, text, level)."""
    tf = textbox(slide, L, y, R - L, BOTTOM - y, name=name)
    for i, (label, text) in enumerate(header):
        para(tf, [(label, {"bold": True}), text], size=size + (1 if i == 0 else 0),
             before=0 if i == 0 else 4)
    for num, text, level in items:
        p = para(tf, [(f"{num}  ", {"bold": True, "color": BLUE}), text] if num else text,
                 size=size if level == 0 else size - 1, before=8 if level == 0 else 3)
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(int(Inches(0.38 + 0.4 * level))))
        pPr.set("indent", str(-int(Inches(0.38))) if num else "0")
    return tf


def code_card(slide, title, lines, y=TOP, h=None, size=15, name="Pseudocode"):
    shp = card(slide, L, y, R - L, h or (BOTTOM - y), title, None, head_size=17, name=name)
    for ln in lines:
        indent = len(ln) - len(ln.lstrip(" "))
        p = para(shp.text_frame, ln.strip(), size=size, before=4)
        p._p.get_or_add_pPr().set("marL", str(int(Inches(0.3 * indent / 4))))
    return shp


def main():
    prs = Presentation(BASE)
    S = list(prs.slides)              # S[0] is interim slide 1
    layout = S[3].slide_layout          # the content layout with the teal corner

    def new(title, note=None):
        s = prs.slides.add_slide(layout)
        drop_body(s)
        set_title(s, title)
        if note:
            notes(s, note)
        return s

    def restyle(slide, title):
        set_title(slide, title)
        return slide

    # ---- 1. title slide is kept as presented (the header already names the department)

    # ---- 3. agenda continued
    s3 = restyle(S[2], "Agenda (contd.)")
    tf = fresh(body_of(s3).text_frame)
    for item, lvl in [("Algorithm Design", 0), ("Implementation", 0), ("Testing", 0),
                      ("Unit Testing", 1), ("Integration Testing", 1),
                      ("Results and Performance Analysis", 0), ("Snapshots", 0),
                      ("Applications", 0), ("Conclusion and Future Scope", 0),
                      ("Publications / Conferences / Project Competitions", 0),
                      ("References", 0)]:
        p = para(tf, item, size=20, bullet="○" if lvl == 0 else "●", level=lvl,
                 before=6 if lvl == 0 else 2, line=1.05)
        p._p.pPr.set("marL", str(int(Inches(1.0 + 0.4 * lvl))))

    # ---- 4. introduction
    s4 = restyle(S[3], "Introduction")
    drop(body_of(s4))
    bullets(s4, [
        "India recognises 22 scheduled languages, yet digital services remain English-first.",
        "Strong Indic translation exists (IndicTrans2 covers all 22), but it runs in the cloud: "
        "no connectivity means no translation, and every sentence leaves the device.",
        "Running on the device needs a model about ten times smaller; even IndicTrans2's "
        "distilled 200M variant needs close to 1 GB of memory.",
        ["SETU (सेतु, ", ("bridge", {"italic": True}), ") distils IndicTrans2 into compact "
         "52.6M-parameter students, one per direction, quantised to INT4 ONNX (103.9 MB)."],
        "We tested preference distillation (DPO) against sequence-level knowledge distillation "
        "(SeqKD): SeqKD won decisively, 17.09 vs 11.10 BLEU.",
        "All 22 scheduled languages are covered in both directions; 44 models serve 506 "
        "directions through an English pivot, fully offline.",
    ], size=19, before=11, line=1.05)

    # ---- 5. objectives
    s5 = restyle(S[4], "Objectives")
    drop(body_of(s5))
    tf = textbox(s5, L, TOP, R - L, BOTTOM - TOP, name="Objectives")
    for label, text in [
        ("Quality:", "To retain at least 80% of the teacher's BLEU in every student "
                     "(student/teacher ratio ≥ 0.80)."),
        ("Latency:", "To translate a sentence in under 500 ms on ARM-class CPU hardware, with no GPU."),
        ("Size:", "To keep each deployable quantised model within 200 MB."),
        ("Offline operation:", "To run inference with every network socket disabled, so no "
                               "user text leaves the device."),
        ("Empirical finding:", "To test preference distillation (DPO) against sequence-level "
                               "KD at matched student size, and report the outcome either way."),
        ("Coverage and extensibility:", "To support the scheduled languages in both directions, "
                                        "reach every Indic-to-Indic pair, and add a language "
                                        "by configuration alone."),
    ]:
        para(tf, [(label + " ", {"bold": True}), text], size=18, bullet="num", before=10, line=1.05)

    # ---- literature survey summary (new; the template asks for one summary slide)
    lit = new("Literature Survey: Summary",
              "One-slide summary of the 20 papers in the table. Each card groups related papers; "
              "the bottom band is the gap SETU fills.")
    cw, ch, gx, gy = Inches(4.42), Inches(1.36), Inches(0.16), Inches(0.13)
    cards = [
        ("Compact models [1], [2], [4], [20]",
         "Mobile NMT, SMaLL-100, shallow-to-deep training and DistilBERT keep most quality at a "
         "fraction of the size, but accuracy drops on complex sentences."),
        ("Indic multilingual MT [11], [12], [15], [16]",
         "IndicTrans2 covers all 22 languages; smaller Indic systems cover only a few. Broad "
         "coverage today needs large, server-side models."),
        ("Knowledge distillation [5], [9], [10]",
         "kNN-KD, All-in-One KD and continual KD transfer knowledge efficiently and add "
         "languages incrementally, at the cost of training complexity."),
        ("Preference learning [8], [14]",
         "DPO replaces RLHF with a simple classification loss and has been applied to NMT, but "
         "its gains depend on the quality of the preference data."),
        ("Speech and cascaded systems [6], [7], [13]",
         "Cascaded ASR → MT pipelines compound recognition errors, while end-to-end speech "
         "translation still lacks data for low-resource languages."),
        ("Data and offline systems [3], [17], [18], [19]",
         "Web-mined corpora are noisy; existing offline translators are conceptual or "
         "statistical, and low-latency LLM translation is too heavy for edge devices."),
    ]
    for i, (h, b) in enumerate(cards):
        card(lit, L + (i % 2) * (cw + gx), TOP + (i // 2) * (ch + gy), cw, ch, h, b,
             head_size=15, body_size=13.5, name=f"Lit card {i + 1}")
    card(lit, L, TOP + 3 * (ch + gy) + Inches(0.02), R - L, Inches(0.72), None,
         [[("Research gap: ", {"bold": True, "color": WHITE}),
           ("no surveyed system delivers high-quality multilingual Indic translation fully "
            "offline, within an edge device's 200 MB and 500 ms budget.", {"color": WHITE})]],
         fill=BLUE, body_size=14, name="Gap", anchor=MSO_ANCHOR.MIDDLE)

    # ---- problem statement with input and output
    s12 = restyle(S[11], "Problem Statement")
    drop(body_of(s12))
    card(s12, L, TOP, R - L, Inches(2.05), None,
         [[("There is a need for a lightweight, offline-capable multilingual translation "
            "framework that delivers high-quality translation across the scheduled languages of "
            "India on edge devices (at least 80% of a strong teacher's BLEU, within 200 MB and "
            "under 500 ms of CPU time per sentence, with zero network calls), and that supports "
            "adding new languages without catastrophic forgetting and without a quadratic "
            "growth in the number of trained models.", {"italic": True})]],
         body_size=16, name="Statement", anchor=MSO_ANCHOR.MIDDLE)
    half = (R - L - Inches(0.2)) // 2
    card(s12, L, TOP + Inches(2.25), half, Inches(2.85), "Input",
         ["Samanantar parallel corpus: web-mined Indic–English sentence pairs.",
          "IndicTrans2 dist-200M teacher's 1-best translations: about 497,000 distilled "
          "pairs per direction.",
          "At run time: a sentence with its source and target language."],
         head_size=18, body_size=15.5, name="Input")
    card(s12, L + half + Inches(0.2), TOP + Inches(2.25), half, Inches(2.85), "Output",
         ["44 INT4 ONNX student models, 103.9 MB each, for all 22 scheduled languages "
          "in both directions.",
          "506 usable directions through the English pivot.",
          "The translation, with its latency and route, produced fully offline."],
         head_size=18, body_size=15.5, name="Output")

    # ---- proposed system: four stages
    s13 = restyle(S[12], "Proposed System")
    drop(body_of(s13))
    stages = [
        ("1. Distil", "IndicTrans2 dist-200M decodes the cleaned corpus; its 1-best output "
                      "replaces the noisy human reference (SeqKD)."),
        ("2. Train", "52.6M Marian student, 16k SentencePiece vocabulary; masked padding, "
                     "LR warmup, label smoothing, gradient clipping."),
        ("3. Quantise", "Export to ONNX, validate, then INT8 → INT4: 411 MB down to 103.9 MB "
                        "(4× smaller)."),
        ("4. Serve", "One engine behind the REST API, offline PWA, web app and CLI; English "
                     "pivot for Indic-to-Indic pairs."),
    ]
    sw, gap = Inches(1.95), Inches(0.4)
    for i, (h, b) in enumerate(stages):
        x = L + i * (sw + gap)
        card(s13, x, TOP, sw, Inches(2.75), h, b, head_size=17, body_size=14.5, name=f"Stage {i + 1}")
        if i < 3:
            arrow(s13, x + sw + Inches(0.07), TOP + Inches(1.2), Inches(0.26), Inches(0.32))
    bullets(s13, [
        "The pipeline runs once per translation direction: 44 students cover all 22 "
        "scheduled languages both ways.",
        "The English pivot turns 44 models into 506 usable directions, at about 50–65 ms "
        "for the extra hop.",
        "Nothing leaves the device at inference time; the teacher is used only offline.",
    ], y=TOP + Inches(3.0), size=17, before=9)

    # ---- conceptual modelling overview
    s15 = restyle(S[14], "Conceptual/Analysis Modelling")
    drop(body_of(s15))
    bullets(s15, [
        ("Object-oriented models:", "use case, sequence, activity, state chart and class "
                                    "diagrams describe actors, interactions and structure."),
        ("Structured models:", "data flow and entity-relationship diagrams describe how data "
                               "moves and how it is related."),
        "Every model shows two separate lifecycles:",
        ("sub", [("Offline training: ", {"bold": True}),
                 "run by the ML engineer, once per direction, on a GPU."]),
        ("sub", [("Online inference: ", {"bold": True}),
                 "run by the end user, repeatedly, on the device."]),
        "Training components are absent from the deployed artifact entirely.",
    ], size=19, before=12, line=1.05)

    # ---- one slide per report diagram
    def side_by_side(title, img, points, note, img_w=Inches(3.4), size=15, cap=None):
        s = new(title, note)
        picture(s, A(img), L, TOP, img_w, BOTTOM - TOP - (Inches(0.35) if cap else 0),
                name=title)
        bullets(s, points, x=L + img_w + Inches(0.3), y=TOP + Inches(0.1), size=size, before=9)
        if cap:
            caption(s, cap, BOTTOM - Inches(0.32), x=L, w=img_w)
        return s

    def full(title, img, cap, note, h=None):
        s = new(title, note)
        hh = h or (BOTTOM - TOP - Inches(0.45))
        picture(s, A(img), L, TOP, R - L, hh, name=title)
        caption(s, cap, TOP + hh + Inches(0.08))
        return s

    use_case = side_by_side(
        "Use Case Diagram", "fig_use_case.png",
        [("Actors:", "End User, ML Engineer and Edge Device."),
         ("End User:", "Translate Text; Pivot Translate via English for Indic-to-Indic pairs."),
         ("ML Engineer:", "Distil Teacher Targets, Train Student (SeqKD), Quantise and Export "
                          "ONNX, Evaluate BLEU/chrF."),
         ("Edge Device:", "hosts the INT4 model and runs every translation offline.")],
        "Three actors. The end user only ever touches translation; everything else is the ML "
        "engineer's offline work.", img_w=Inches(2.9), size=17)
    sequence = full("Sequence Diagram", "fig_sequence.png",
                    "Direct translation and the two-hop English pivot",
                    "Top half: a direct pair. Bottom half: no direct model, so the router "
                    "chains source to English to target.")
    activity = new("Activity Diagram", "Left: the offline training pipeline. Right: on-device "
                                       "inference. The dashed line in the report separates them.")
    act = Image.open(A("fig_activity.png"))
    top_part, bottom_part = act.crop((0, 0, act.width, 1212)), act.crop((0, 1245, act.width, act.height))
    tmp_dir = tempfile.mkdtemp(prefix="setu_ppt_")
    tp, bp = os.path.join(tmp_dir, "activity_train.png"), os.path.join(tmp_dir, "activity_infer.png")
    top_part.save(tp)
    bottom_part.save(bp)
    colw = (R - L - Inches(0.3)) // 2
    hh = BOTTOM - TOP - Inches(0.4)
    scale = hh / top_part.height
    picture(activity, tp, L, TOP, colw, hh, name="Activity: offline training")
    pic_b = picture(activity, bp, L + colw + Inches(0.3), TOP, colw, int(bottom_part.height * scale),
                    name="Activity: on-device inference")
    pic_b.top = TOP
    caption(activity, "Offline training pipeline", BOTTOM - Inches(0.32), x=L, w=colw)
    caption(activity, "On-device inference", TOP + int(bottom_part.height * scale) + Inches(0.1),
            x=L + colw + Inches(0.3), w=colw)
    state = side_by_side(
        "State Chart Diagram", "fig_state_chart.png",
        ["A model passes through a fixed sequence of states: raw corpus → cleaned → "
         "teacher-distilled → SeqKD-trained → evaluated → quantised → deployed.",
         ("Collapse:", "detected at evaluation; a loss of 3–4 with degenerate output."),
         ("Recovery:", "retraining at a lower learning rate on the same distilled corpus. "
                       "Both transitions happened in practice."),
         "Training states run offline on a GPU; only the quantised artifact reaches the "
         "device."],
        "Model lifecycle, including the collapse and recovery transitions we hit in training.",
        img_w=Inches(3.6), size=16)
    dfd = full("Data Flow Diagram", "fig_data_flow.png",
               "Level-1 data flow: corpus to deployed translation",
               "Two corpora per direction: the processed one keeps human references for "
               "evaluation; the distilled one is used for training.")
    er = side_by_side(
        "ER Diagram", "fig_er.png",
        ["SETU has no relational database; the ER model describes its persistent artifacts "
         "on disk.",
         ("Language", "defines LanguagePair; a pair contains SentencePairs and trains "
                      "ModelVersions."),
         ("ModelVersion", "is scored by an EvalReport (BLEU, chrF, teacher BLEU, ratio) and "
                          "produces TranslationResults."),
         "Script-qualified FLORES codes (hin_Deva, eng_Latn) identify every language."],
        "Entities and relationships of the artifacts SETU stores.", img_w=Inches(4.2), size=16)

    # ---- SRS: final numbers
    s18 = restyle(S[17], "Software Requirements Specification")
    for shp in s18.shapes:
        if shp.has_table:
            for row in shp.table.rows:
                for cell in row.cells:
                    for p in cell.text_frame.paragraphs:
                        if not p.runs:
                            continue
                        t = "".join(r.text for r in p.runs)
                        new_t = (t.replace("(11 of 22 in Phase 1, both directions)",
                                           "(all 22 scheduled languages, both directions)")
                                  .replace("(about 104 MB achieved, INT4)", "(103.9 MB achieved, INT4)")
                                  .replace("<= 200 MB", "≤ 200 MB"))
                        if new_t != t:
                            p.runs[0].text = new_t
                            for r in p.runs[1:]:
                                r.text = ""

    # ---- planning: report Gantt + PERT
    s19 = restyle(S[18], "Project Planning/Scheduling")
    drop_pictures(s19)
    picture(s19, A("fig_gantt.png"), Inches(0.3), TOP, Inches(9.4), BOTTOM - TOP - Inches(0.45),
            name="Gantt chart")
    caption(s19, "Gantt chart: both phases complete, all 22 scheduled languages delivered",
            BOTTOM - Inches(0.36))
    pert = full("Project Planning: PERT Network", "fig_pert.png",
                "PERT network for Phase 1; the critical path (red) takes 40.34 weeks",
                "Critical path in red. Activities H and I had float, so they could slip without "
                "delaying the project.", h=Inches(4.6))

    # ---- system design: report architecture + its four layers
    s20 = restyle(S[19], "System Design")
    drop_pictures(s20)
    picture(s20, A("fig_architecture.png"), L, TOP, Inches(5.6), BOTTOM - TOP - Inches(0.4),
            name="System architecture")
    caption(s20, "SeqKD distillation and offline deployment pipeline", BOTTOM - Inches(0.34),
            x=L, w=Inches(5.6))
    lx, lw = L + Inches(5.8), R - L - Inches(5.8)
    for i, (h, b) in enumerate([
        ("Data layer", "Cleans corpora; keeps a processed corpus for evaluation and a distilled "
                       "one for training."),
        ("Model layer", "Teacher behind an abstract interface; Marian student trained from "
                        "scratch."),
        ("Deployment layer", "ONNX export, validation, INT8 → INT4 quantisation, per-stage "
                             "benchmark."),
        ("Serving layer", "Per-direction engine cache, English-pivot router, four interfaces."),
    ]):
        card(s20, lx, TOP + i * Inches(1.27), lw, Inches(1.15), h, b, head_size=14,
             body_size=11.5, name=h)

    # ---- module decomposition as numbered cards
    s21 = restyle(S[20], "Module Decomposition")
    drop(body_of(s21))
    mods = [
        ("1. Corpus Loader", "Ingests Samanantar; normalises scripts, filters, de-duplicates."),
        ("2. Teacher Distiller", "IndicTrans2 dist-200M generates the 1-best SeqKD targets."),
        ("3. SeqKD Trainer", "Trains the 52.6M Marian student: masked padding, warmup, clipping."),
        ("4. Quantiser", "ONNX export, then INT8 → INT4: 411 MB down to 103.9 MB."),
        ("5. Inference Engine and Router", "ONNX Runtime + SentencePiece; direct model or "
                                           "source → English → target."),
        ("6. REST API", "FastAPI: /translate, /languages, /models, /health."),
        ("7. Client Interfaces", "Next.js web app, offline PWA and CLI on one shared engine."),
        ("8. Evaluator and Expansion", "BLEU, chrF, student/teacher ratio; All-in-One KD and "
                                       "EWC to add languages."),
    ]
    mw, mh = Inches(4.42), Inches(1.16)
    for i, (h, b) in enumerate(mods):
        card(s21, L + (i % 2) * (mw + Inches(0.16)), TOP + (i // 2) * (mh + Inches(0.12)), mw, mh,
             h, b, head_size=15.5, body_size=14, name=h)

    # ---- module description slides: same text, sized to fit
    for idx in (21, 22, 23):
        s = restyle(S[idx], "Module Description")
        ph = body_of(s)
        ph.left, ph.top, ph.width, ph.height = L, TOP, R - L, BOTTOM - TOP
        for p in ph.text_frame.paragraphs:
            pPr = p._p.get_or_add_pPr()
            lvl = int(pPr.get("lvl", "0"))
            pPr.set("marL", str(int(Inches(0.35 if lvl == 0 else 0.8))))
            pPr.set("indent", str(-int(Inches(0.3 if lvl == 0 else 0.25))))
            if lvl == 0 and len(p.runs) == 1 and ":" in p.runs[0].text:
                # bold only the "Module n - Name:" label, as on the other slides
                head, tail = p.runs[0].text.split(":", 1)
                p.runs[0].text = head + ":"
                p.runs[0].font.bold = True
                r2 = copy.deepcopy(p.runs[0]._r)
                p.runs[0]._r.addnext(r2)
                r2.find(qn("a:t")).text = tail
                r2.find(qn("a:rPr")).set("b", "0")
            for tag in ("a:lnSpc", "a:spcBef"):
                el = pPr.find(qn(tag))
                if el is not None:
                    for c in list(el):
                        el.remove(c)
                    if tag == "a:lnSpc":
                        etree.SubElement(el, qn("a:spcPct")).set("val", "105000")
                    else:
                        etree.SubElement(el, qn("a:spcPts")).set("val", "1000" if lvl == 0 else "400")
            bs = pPr.find(qn("a:buSzPts"))
            if bs is not None:
                bs.set("val", "1600")
            for r in p.runs:
                r.font.size = Pt(17 if lvl == 0 else 15)

    # ---- component design (new): report class diagram + component roles
    comp_fig = full("Component Design: Class Diagram", "fig_class.png",
                    "Training classes (left) run offline; inference classes (right) ship to the device",
                    "Each class is a component. Only IndicTrans2Teacher imports transformers or "
                    "torch, which keeps the deployed artifact free of training code.")
    comp = new("Component Design", "Roles of the components in the class diagram.")
    half = (R - L - Inches(0.2)) // 2
    card(comp, L, TOP, half, Inches(4.45), "Training components (offline)", [
        [("IndicTrans2Teacher: ", {"bold": True}), "the teacher behind an abstract "
         "TeacherModel; the only importer of transformers and torch."],
        [("SeqKDDistiller: ", {"bold": True}), "decodes the corpus and writes (source, "
         "1-best) training pairs."],
        [("SFTTrainer: ", {"bold": True}), "trains the student with label smoothing and "
         "gradient-norm clipping."],
        [("DPOTrainer: ", {"bold": True}), "preference training against a frozen reference "
         "(the reported baseline)."],
        [("StudentTokenizer, ModelConfig: ", {"bold": True}), "16k SentencePiece vocabulary "
         "with reserved language tags; per-pair settings."],
    ], head_size=16, body_size=14, name="Training components")
    card(comp, L + half + Inches(0.2), TOP, half, Inches(4.45), "Inference components (on device)", [
        [("InferenceEngine: ", {"bold": True}), "translate(text, src, tgt); reports stub mode "
         "explicitly instead of failing silently."],
        [("ONNXTranslator: ", {"bold": True}), "holds the ONNX Runtime session and tokenizer; "
         "greedy decoding."],
        [("Router: ", {"bold": True}), "caches one engine per pair; picks the direct model or "
         "the English pivot."],
        [("TranslationResult: ", {"bold": True}), "translated text, latency, source, target "
         "and pivot flag."],
    ], head_size=16, body_size=14, name="Inference components")
    caption(comp, "A unit test fails the build if any other module imports transformers or torch",
            TOP + Inches(4.6), size=13)

    # ---- interface design: report figure in place of the old screenshot
    s25 = restyle(S[24], "Interface Design")
    drop_pictures(s25)
    picture(s25, A("fig_interfaces.png"), L, TOP + Inches(0.1), R - L, Inches(4.55),
            name="Interface design")
    caption(s25, "Four client surfaces over one shared inference engine", TOP + Inches(4.75))
    s26 = S[25]
    restyle(s26, "Interface Design")
    def fit_table(slide, size, x=L, y=TOP, w=R - L, row_h=Inches(0.3)):
        """Fit a table inside the content area; y=None keeps its current top."""
        for shp in slide.shapes:
            if not shp.has_table:
                continue
            tbl = shp.table
            old = sum(c.width for c in tbl.columns)
            for c in tbl.columns:
                c.width = int(c.width * w / old)
            for row in tbl.rows:
                row.height = row_h
                for cell in row.cells:
                    for p in cell.text_frame.paragraphs:
                        for r in p.runs:
                            r.font.size = Pt(size)
            shp.left = x
            if y is not None:
                shp.top = y

    fit_table(s26, 12)
    fit_table(S[13], 15)
    fit_table(S[32], 14, y=None)   # unit testing
    fit_table(S[33], 14, y=None)   # integration testing

    for idx, title in [(13, "Requirement Engineering"), (26, "Data Structure Design"),
                       (27, "Algorithm Design"), (28, "Algorithm Design"), (29, "Implementation"),
                       (30, "Pseudocode"), (31, "Pseudocode"), (32, "Unit Testing"),
                       (33, "Integration Testing"), (10, "Drawbacks of Existing System")]:
        restyle(S[idx], title)

    # implementation: label above the code screenshot, both clear of the corner
    impl = S[29]
    ph = body_of(impl)
    ph.left, ph.top, ph.width, ph.height = L, TOP - Inches(0.05), R - L, Inches(0.4)
    tf = fresh(ph.text_frame, anchor=MSO_ANCHOR.TOP, margins=(Inches(0.05), 0))
    para(tf, [("Inference: ", {"bold": True}), "English-pivot routing ",
              "(src/setu/inference/router.py)"], size=17, before=0)
    for shp in list(impl.shapes):
        if shp.shape_type == 13:
            img = shp.image.blob
            drop(shp)
            tmp_png = os.path.join(tempfile.mkdtemp(prefix="setu_ppt_"), "router." + shp.image.ext)
            with open(tmp_png, "wb") as fh:
                fh.write(img)
            picture(impl, tmp_png, L, TOP + Inches(0.4), R - L, BOTTOM - TOP - Inches(0.4),
                    name="router.py")

    # algorithms: same content, laid out without the restarted numbering
    for s in (S[27], S[28]):
        drop(body_of(s))
    steps(S[27], [("Algorithm 1: SeqKD_Train", ""),
                  ("Input: ", "language pair (src → tgt), N sentences"),
                  ("Output: ", "quantised INT4 ONNX student")], [
        ("1.", "Load N parallel sentences from Samanantar; normalise scripts, filter, dedup.", 0),
        ("2.", "For each source x: y* ← Teacher.generate(x), the IndicTrans2 greedy 1-best; "
               "store (x, y*) as the distilled corpus.", 0),
        ("3.", "Load the SentencePiece tokenizer (16k vocab, FLORES tags); initialise the 52M "
               "Marian student θ.", 0),
        ("4.", "For each epoch and each batch (x, y*):", 0),
        ("a.", "ŷ ← student(θ, encode(x))", 1),
        ("b.", "L ← cross_entropy(ŷ, encode(y*)), PAD masked (−100)   // modification", 1),
        ("c.", "θ ← θ − η · clip(∇θ L)   // warmup, clipping, η = 3e-4", 1),
        ("5.", "Export θ → ONNX; quantise INT8 → INT4. Return models/<pair>/int4 (about 104 MB).", 0),
    ], size=17)
    steps(S[28], [("Algorithm 2: Translate", ""),
                  ("Input: ", "text, src, tgt"),
                  ("Output: ", "translation")], [
        ("1.", "if src = tgt: reject.", 0),
        ("2.", "pair ← flores(src) + \"-\" + flores(tgt)", 0),
        ("3.", "if model(pair) exists: return Engine(pair).run(text)   // direct", 0),
        ("4.", "else if model(src → en) and model(en → tgt):   // English pivot", 0),
        ("", "mid ← Engine(src → en).run(text); return Engine(en → tgt).run(mid)", 1),
        ("5.", "else: return text unchanged (passthrough stub, flagged).", 0),
        ("", [("Example: ", {"bold": True}), "Translate(\"भारत एक विशाल देश है।\", hi, bn) has "
              "no direct hi → bn model, so it pivots: hi → en gives \"India is a vast "
              "country.\", then en → bn gives \"ভারত একটি বিশাল দেশ।\""], 0),
    ], size=17)

    for s in (S[30], S[31]):
        drop(body_of(s))
    code_card(S[30], "Pseudocode: build a translation model (SeqKD)", [
        "load parallel sentences for the language pair",
        "clean, filter and de-duplicate the sentences",
        "for each source sentence:",
        "    ask the teacher (IndicTrans2) for its best translation",
        "    save (source, teacher translation) as a training example",
        "create the student model and its tokenizer",
        "repeat for several passes over the data:",
        "    show the student a source sentence",
        "    compare its output with the teacher's translation",
        "    ignore padding; nudge the student to reduce the difference",
        "    keep the learning rate small and clip large updates",
        "compress the trained student to INT4 and save it",
    ], size=17.5)
    code_card(S[31], "Pseudocode: translate text", [
        "if source and target languages are the same: stop",
        "form the pair name from source and target",
        "if a model exists for the pair:",
        "    run that model and return the translation",
        "else if models exist for source → English and English → target:",
        "    translate source → English",
        "    translate English → target, and return the result",
        "else:",
        "    return the text unchanged (no model for this pair yet)",
        "show the translation with its latency and on-device badge",
    ], size=17.5)

    # ---- results and performance analysis (new)
    r1 = new("Results: SeqKD vs Preference Distillation",
             "The deciding experiment. Same 52.6M student, same 100k Hindi to English sentences, "
             "evaluated on held-out human references. SeqKD beats DPO-distill by 5.99 BLEU.")
    picture(r1, A("fig_head_to_head.png"), L, TOP, R - L, Inches(3.7), name="Head-to-head")
    caption(r1, "100,000 sentences, Hindi → English, matched student size, human references "
                "(teacher BLEU 28.16)", TOP + Inches(3.75))
    sw = (R - L - Inches(0.4)) // 3
    for i, (n, lab) in enumerate([("17.09", "BLEU, SeqKD (S1)"), ("11.10", "BLEU, DPO-distill (S2)"),
                                  ("+54%", "SeqKD over preference distillation")]):
        stat(r1, L + i * (sw + Inches(0.2)), TOP + Inches(4.2), sw, Inches(0.95), n, lab,
             num_size=28)

    r2 = new("Results: Why SeqKD Won",
             "Reference-trained students plateau; distilled students keep improving. That pattern "
             "is what you expect if reference noise is the limit.")
    picture(r2, A("fig_scaling.png"), L, TOP, R - L, Inches(3.2), name="Data scaling")
    caption(r2, "SeqKD data scaling, Hindi → English: the ratio crosses 0.80 at 500,000 sentences",
            TOP + Inches(3.22))
    bullets(r2, [
        "Reference-trained students plateau near a 0.66 ratio; distilled students keep "
        "improving: 0.607 → 0.764 → 0.806.",
        "Reference noise, not the training objective, caps a 52M student. The teacher's "
        "1-best output is a clean, consistent target.",
        "DPO itself worked (margin accuracy 1.0, chrF up), but chrF preference is not the "
        "signal a compact student needs most.",
    ], y=TOP + Inches(3.6), size=15, before=6)

    r3 = new("Results: Scorecard, 22 Directions",
             "Student/teacher BLEU ratio for every evaluated direction. Green bars pass 0.80; "
             "amber are near misses, all above 0.75.")
    picture(r3, A("fig_scorecard.png"), L, TOP, Inches(5.0), BOTTOM - TOP, name="Scorecard")
    sx, sw2 = L + Inches(5.25), R - L - Inches(5.25)
    for i, (n, lab) in enumerate([("14 / 22", "directions meet the ≥ 0.80 target"),
                                  ("0.838", "mean student/teacher ratio"),
                                  ("0.855", "median ratio"),
                                  ("0.955", "best: Marathi → English")]):
        stat(r3, sx, TOP + i * Inches(1.14), sw2, Inches(1.02), n, lab, num_size=26)
    tf = textbox(r3, sx, TOP + Inches(4.6), sw2, Inches(0.6), name="Scorecard note")
    para(tf, "Weakest: English → Tamil, 0.755. No collapsed models remain.", size=12,
         color=MUTED, before=0)

    r4 = new("Results: Per-Language Rollup",
             "Both directions track closely, so the method is not biased towards English.")
    picture(r4, A("fig_rollup.png"), L, TOP, R - L, Inches(3.75), name="Per-language rollup")
    bullets(r4, [
        ("Direction symmetry:", "English → Indic averages 0.850, Indic → English 0.825."),
        ("Near misses are under-converged, not unstable:", "their losses sit at 2.00–2.32 "
         "against 1.46–1.95 for passing directions."),
        ("BLEU understates agglutinative languages:", "English → Malayalam passes at 0.863 "
         "with only 5.2 BLEU."),
    ], y=TOP + Inches(3.9), size=15, before=5)

    r5 = new("Performance: Quantisation",
             "Hindi to English student. INT4 is the only precision under both the size and the "
             "latency budget, and it loses no quality.")
    picture(r5, A("fig_quantisation.png"), L, TOP, R - L, Inches(3.15), name="Quantisation")
    caption(r5, "Size, p90 latency and BLEU at FP32, INT8 and INT4 (Hindi → English)",
            TOP + Inches(3.2))
    for i, (n, lab) in enumerate([("4×", "smaller: 410.9 MB → 103.9 MB, 48% under budget"),
                                  ("191 ms", "p90 latency at INT4 (1,196 ms at FP32)"),
                                  ("19.3", "BLEU at INT4 (18.3 at INT8)")]):
        stat(r5, L + i * (sw + Inches(0.2)), TOP + Inches(3.7), sw, Inches(1.2), n, lab,
             num_size=28)

    r6 = side_by_side(
        "Performance: Latency", "fig_latency.png",
        [("Median:", "62–214 ms per sentence in every deployed direction."),
         ("Mean:", "105–202 ms, far inside the 500 ms budget."),
         ("p90:", "141–541 ms; only English → Tamil crosses 500 ms, on a shared VM host "
                  "under load."),
         ("Pivot:", "the extra hop through English costs about 50–65 ms."),
         ("Caveat:", "measured on x86 CPU; ARM Cortex-A55 latency is projected, not yet "
                     "measured.")],
        "Median and p90 latency per direction, INT4 ONNX on CPU.", img_w=Inches(4.7), size=15)

    r7 = new("Results: Definition of Done",
             "Three of four targets pass in every direction; quality passes in 14 of 22. "
             "On Hindi to English all four are met.")
    dw, dh = (R - L - Inches(0.2)) // 2, Inches(2.05)
    for i, (h, verdict, col, body) in enumerate([
        ("Quality (ratio ≥ 0.80)", "PARTIAL", AMBER, "14 of 22 directions; mean 0.838, median "
                                                     "0.855, best 0.955."),
        ("Latency (< 500 ms)", "MET", GREEN, "Mean 105–202 ms per sentence; p90 141–541 ms."),
        ("Size (≤ 200 MB)", "MET", GREEN, "103.9 MB in every direction, 48% under budget."),
        ("Offline (zero network calls)", "MET", GREEN, "Verified for every direction with all "
                                                      "sockets disabled."),
    ]):
        c = card(r7, L + (i % 2) * (dw + Inches(0.2)), TOP + (i // 2) * (dh + Inches(0.2)), dw, dh,
                 h, None, head_size=17, name=h)
        para(c.text_frame, [(verdict, {"bold": True})], size=26, color=col, before=8)
        para(c.text_frame, body, size=16, before=6)
    tf = textbox(r7, L, TOP + 2 * dh + Inches(0.55), R - L, Inches(0.5), name="DoD note")
    para(tf, [("Hindi → English, the primary pair, meets all four targets.", {"bold": True})],
         size=16, color=BLUE, before=0, align=PP_ALIGN.CENTER)

    r8 = new("Results: Sample Translations",
             "Real outputs of the INT4 students. The English to Kannada row was captured live "
             "from the CLI.")
    rows = [["Direction", "Input", "SETU output"],
            ["hi → en", "भारत एक विशाल देश है।", "India is a vast country."],
            ["hi → en", "मुझे किताबें पढ़ना पसंद है।", "I love reading books."],
            ["en → hi", "Water is essential for life", "जीवन के लिए पानी आवश्यक है।"],
            ["bn → en", "ভারত একটি বড় দেশ।", "India is a big country."],
            ["mr → en", "मला पुस्तके वाचायला आवडतात।", "I love reading books."],
            ["te → en", "భారతదేశం ఒక పెద్ద దేశం.", "India is a big country."],
            ["en → kn", "Water is essential for life.", "ಜೀವಕ್ಕೆ ನೀರು ಅತ್ಯಗತ್ಯ."],
            ["en → ml", "Water is essential for life", "ജീവിതത്തിന് വെള്ളം അത്യന്താപേക്ഷിതമാണ്."]]
    table(r8, rows, L, TOP, R - L, [Inches(1.1), Inches(3.75), Inches(4.15)],
          row_h=Inches(0.42), size=14, head_size=14, name="Samples", bold_first_col=True)
    bullets(r8, [
        "Concessive and counterfactual clauses survive in Hindi, Marathi and Gujarati, each in "
        "its own idiomatic form.",
        "Recurring errors: occasional repetition, transliterated rare words (o'clock), and "
        "lexical slips; they match each language's scorecard position.",
    ], y=TOP + Inches(3.95), size=14, before=5)

    # ---- snapshots (new)
    sn1 = new("Snapshots: Web Application",
              "Next.js web app running locally. English to Kannada in 86 ms on the INT4 model, "
              "with the on-device badge.")
    picture(sn1, A("snap_webapp_light.png"), L, TOP, R - L, Inches(4.75), name="Web app")
    caption(sn1, "Next.js translator: English → Kannada in 86 ms, INT4, 103.94 MB, on-device "
                 "engine", TOP + Inches(4.85))
    sn2 = new("Snapshots: CLI and REST API",
              "Real output captured on 5 Nov 2026 from the INT4 models on a laptop CPU. JSON is "
              "abridged to the key fields.")
    tw = (R - L - Inches(0.2)) // 2
    terminal(sn2, L, TOP, tw, Inches(4.75), "Command line (setu_cli.py)", [
        ("$", '$ python setu_cli.py --src hi --tgt en --text "भारत एक विशाल देश है।"'),
        (">", "India is a vast country."),
        ("$", '$ python setu_cli.py --src en --tgt kn --text "Water is essential for life."'),
        (">", "ಜೀವಕ್ಕೆ ನೀರು ಅತ್ಯಗತ್ಯ."),
        ("$", '$ python setu_cli.py --src hi --tgt bn --json --text "भारत एक विशाल देश है।"'),
        (">", '{"translated_text": "ভারত একটি বিশাল দেশ।", "latency_ms": 60.2, "pivot": "en", '
              '"stub": false}'),
    ])
    terminal(sn2, L + tw + Inches(0.2), TOP, tw, Inches(4.75), "REST API (FastAPI)", [
        ("$", "$ curl localhost:8765/health"),
        (">", '{"status": "ok", "stub": false}'),
        ("$", "$ curl -X POST localhost:8765/translate -d '{\"source_lang\": \"ta\", "
              "\"target_lang\": \"te\", \"text\": \"இந்தியா ஒரு பெரிய நாடு.\"}'"),
        (">", '{"translated_text": "భారతదేశం ఒక పెద్ద దేశం.", "latency_ms": 61.7, '
              '"pivot": "en", "stub": false}'),
        ("$", "$ curl -X POST localhost:8765/translate -d '{\"source_lang\": \"hi\", "
              "\"target_lang\": \"hi\", ...}'"),
        (">", '400 {"detail": "Source and target language are both \'hi\'"}'),
    ])
    caption(sn2, "Tamil → Telugu and Hindi → Bengali have no direct model, so both route through "
                 "English", TOP + Inches(4.85))

    # ---- applications (new)
    ap = new("Applications", "Every application relies on the same two properties: no network "
                             "needed, and text never leaves the device.")
    apps = [
        ("Rural healthcare", "Doctors and ASHA workers talk with patients across languages with "
                             "no network; symptoms never leave the device."),
        ("Defence and border operations", "Patrols beyond cellular coverage translate locally; "
                                          "nothing is transmitted to intercept."),
        ("Education", "Multilingual tutoring in the student's own language at zero cost "
                      "per query."),
        ("Government services", "Forms and notices translated at a gram panchayat counter "
                                "without internet or API fees."),
        ("Disaster relief", "Field teams communicate while networks are down, exactly when "
                            "cloud translators fail."),
        ("Privacy-sensitive documents", "Legal, medical and financial text translated with no "
                                        "disclosure to a third party."),
        ("Research artifact", "The configuration-driven pipeline transfers to any language "
                              "family with a strong teacher."),
    ]
    aw, ah = Inches(4.42), Inches(1.16)
    for i, (h, b) in enumerate(apps):
        card(ap, L + (i % 2) * (aw + Inches(0.16)), TOP + (i // 2) * (ah + Inches(0.12)), aw, ah,
             h, b, head_size=15, body_size=12.5, name=h)
    card(ap, L + aw + Inches(0.16), TOP + 3 * (ah + Inches(0.12)), aw, ah, None,
         [[("Common thread: ", {"bold": True, "color": WHITE}),
           ("works with zero connectivity, and the text never leaves the device.",
            {"color": WHITE})]], fill=BLUE, body_size=14, name="Common thread",
         anchor=MSO_ANCHOR.MIDDLE)

    # ---- conclusion: outcome against each objective
    s35 = restyle(S[34], "Conclusion")
    drop(body_of(s35))
    rows = [["Objective", "Result", "Verdict"],
            ["Quality (ratio ≥ 0.80)", "14 of 22 directions; mean 0.838, best 0.955", "Partial"],
            ["Latency (< 500 ms)", "Mean 105–202 ms per sentence", "Met"],
            ["Size (≤ 200 MB)", "103.9 MB per direction, 48% under budget", "Met"],
            ["Offline operation", "Verified with every network socket disabled", "Met"],
            ["Test the distillation hypothesis", "Refuted: SeqKD 17.09 vs DPO 11.10 BLEU", "Met"],
            ["Coverage and extensibility", "All 22 languages both ways; 44 models serve 506 "
                                           "directions", "Met"]]
    colors = {(r, 2): (AMBER if rows[r][2] == "Partial" else GREEN) for r in range(1, len(rows))}
    table(s35, rows, L, TOP, R - L, [Inches(2.9), Inches(4.8), Inches(1.3)], row_h=Inches(0.5),
          size=14, head_size=15, name="Outcomes", bold_first_col=True, colors=colors)
    card(s35, L, TOP + Inches(3.85), R - L, Inches(1.15), None,
         [[("Key finding: ", {"bold": True, "color": WHITE}),
           ("for compact on-device Indic translation, reference noise, not the training "
            "objective, is the binding constraint. Sequence-level distillation beats "
            "preference distillation by 54%.", {"color": WHITE})]],
         fill=BLUE, body_size=15, name="Key finding", anchor=MSO_ANCHOR.MIDDLE)

    fut = new("Future Scope", "Ordered roughly from cheapest to most ambitious.")
    bullets(fut, [
        ("Benchmark:", "rescore every direction on FLORES-200 with COMET for publishable, "
                       "comparable numbers."),
        ("Close the near misses:", "beam search, more epochs and more distilled data for the "
                                   "eight directions at 0.755–0.787."),
        ("Real hardware:", "measure latency on an ARM Cortex-A55 device instead of projecting "
                           "from x86."),
        ("Stronger teacher:", "the gated 1B-parameter IndicTrans2 flagship would lift the "
                              "whole quality curve."),
        ("One multilingual student:", "All-in-One KD and EWC to replace n × 104 MB of models "
                                      "with a single artifact."),
        ("Smaller and wider:", "true 4-bit runtime kernels to halve the artifact; extend to "
                               "non-scheduled languages and dialects."),
    ], size=18, before=11, line=1.05)

    pub = new("Publications and Competitions",
              "Update the status lines before presenting if anything has changed.")
    for i, (h, status, col, body) in enumerate([
        ("KSCST Student Project Programme, 50th Series (2026–27)", "Proposal prepared", AMBER,
         "Theme 4: Artificial Intelligence, Data Science and Digital Technologies; sub-theme "
         "NLP and Generative AI. Submission deadline 30 November 2026."),
        ("Research paper", "In preparation", AMBER,
         "Preference distillation vs sequence-level knowledge distillation for compact, "
         "on-device Indic machine translation."),
        ("Open release", "Published", GREEN,
         "Code and 22 quantised INT4 models on a public release, downloadable without a login; "
         "a fresh machine translates in five commands."),
    ]):
        c = card(pub, L, TOP + i * Inches(1.65), R - L, Inches(1.5), h, None, head_size=18,
                 name=h)
        para(c.text_frame, [(status, {"bold": True})], size=15, color=col, before=3)
        para(c.text_frame, body, size=15.5, before=3)

    # ---- references: fix the title, add the three works the results rest on
    for idx in (35, 36, 37, 38):
        s = S[idx]
        if s.shapes.title is not None:
            restyle(s, "References")
        for shp in s.shapes:
            if shp.has_text_frame and "[" in shp.text_frame.text and shp != s.shapes.title:
                shp.top = TOP if s.shapes.title is not None else Inches(0.35)
                shp.height = BOTTOM - shp.top
                for p in shp.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.size = Pt(17)
    last = S[38]
    tb = max((shp for shp in last.shapes if shp.has_text_frame and "[18]" in shp.text_frame.text),
             key=lambda s: len(s.text_frame.text))
    proto = next(p._p for p in tb.text_frame.paragraphs if p.text.startswith("[20]"))
    for ref in [
        "[21] Y. Kim and A. M. Rush, “Sequence-Level Knowledge Distillation,” Proc. EMNLP, 2016, "
        "pp. 1317–1327.",
        "[22] G. Ramesh et al., “Samanantar: The Largest Publicly Available Parallel Corpora "
        "Collection for 11 Indic Languages,” Trans. ACL, vol. 10, pp. 145–162, 2022.",
        "[23] NLLB Team et al., “No Language Left Behind: Scaling Human-Centered Machine "
        "Translation,” arXiv:2207.04672, 2022.",
    ]:
        q = copy.deepcopy(proto)
        rs = q.findall(qn("a:r"))
        for extra in rs[1:]:
            q.remove(extra)
        rs[0].find(qn("a:t")).text = ref
        proto.addnext(q)
        proto = q

    # ---- final order: the Phase-II final template's sequence
    order = (S[0:10] + [lit] + [S[10], S[11], S[12], S[13], S[14],
             use_case, sequence, activity, state, dfd, er,
             S[17], S[18], pert, S[19], S[20], S[21], S[22], S[23],
             comp_fig, comp, S[24], S[25], S[26], S[27], S[28], S[29], S[30], S[31],
             S[32], S[33], r1, r2, r3, r4, r5, r6, r7, r8, sn1, sn2, ap,
             S[34], fut, pub, S[35], S[36], S[37], S[38], S[39]])
    dropped = [S[15], S[16]]     # interim modelling text + small diagrams, now one slide each
    sldIdLst = prs.slides._sldIdLst
    by_rid = {sid.rId: sid for sid in sldIdLst}
    rid_of = {id(s.part): rel.rId for rel in prs.part.rels.values()
              if rel.reltype.endswith("/slide") for s in prs.slides if rel.target_part is s.part}
    ids = [by_rid[rid_of[id(s.part)]] for s in order]
    for s in dropped:
        rid = rid_of[id(s.part)]
        sldIdLst.remove(by_rid[rid])
        prs.part.drop_rel(rid)
    for sid in list(sldIdLst):
        sldIdLst.remove(sid)
    for sid in ids:
        sldIdLst.append(sid)
    assert len(set(map(id, order))) == len(order) == len(sldIdLst)
    for s in order:
        one_font(s)
        tag_indic(s)

    prs.save(OUT)
    print(f"wrote {OUT} ({len(order)} slides)")


if __name__ == "__main__":
    main()
