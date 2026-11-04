#!/usr/bin/env python3
"""Build the KSCST 50th-series SPP application pack for SETU.

    python3 build_kscst.py                      # build everything
    python3 build_kscst.py compress IN.pdf N    # shrink a signed scan to upload slot N (1-4)
    python3 build_kscst.py receipt IMG          # turn a payment screenshot into file 04

It fills KSCST's own Word template (source/03_...docx), so their layout and
footers are kept, then splits it into the three documents the Google Form
asks for and writes a copy-paste sheet for the form itself. Personal details
come from details.json in the output folder, which never enters the repo.
"""
import copy, html, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from docx.table import Table
from docx.text.paragraph import Paragraph

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import content as C  # noqa: E402

OUT = Path(os.environ.get("KSCST_OUT", Path.home() / "Downloads" / "KSCST_SETU"))
TEMPLATE = OUT / "source" / "03_KSCST_SPP_50S_Proposal_Format_2026-27.docx"
DETAILS = OUT / "details.json"
FIG = HERE / "figures"
STEM = C.FILE_STEM
NAMES = {
    1: f"01_{STEM}.pdf",
    2: f"02_{STEM}_declaration_endorsement.pdf",
    3: f"03_{STEM}_Processing_Fee.pdf",
    4: f"04_{STEM}_Payment_Receipt.pdf",
}
LIMIT_MB = {1: 3.0, 2: 1.0, 3: 1.0, 4: 1.0}

MISSING = []                      # labels of fields still to fill
MARK = re.compile(r"(\*\*.+?\*\*|\[TO FILL: [^\]]+\])")


def need(value, label):
    """Return value, or a visible marker that is also logged as missing."""
    if value is None or str(value).strip() == "":
        if label not in MISSING:
            MISSING.append(label)
        return f"[TO FILL: {label}]"
    return str(value).strip()


# ----------------------------------------------------------------- details
def load_details():
    d = json.loads(DETAILS.read_text())
    lead = d.get("team_leader_usn")
    studs = d["students"]
    studs.sort(key=lambda s: (s["usn"] != lead, s["usn"]))   # leader first
    for s in studs:
        s["leader"] = s["usn"] == lead
    d["facilities"] = {**C.FACILITIES, **(d.get("facilities") or {})}
    d["budget"] = {**C.BUDGET, **{k: int(v) for k, v in (d.get("budget") or {}).items()}}
    return d


def title_name(p, label):
    t = need(p.get("title"), f"{label} title (Mr./Ms.)")
    return f"{t} {need(p.get('name'), label + ' name')}"


def rupees(n):
    return f"Rs. {n:,}/-"


# ------------------------------------------------------------- citations
CITE_ORDER = []


def cite(text):
    def sub(m):
        k = m.group(1)
        if k not in C.REFERENCES:
            raise KeyError(f"unknown reference {k}")
        if k not in CITE_ORDER:
            CITE_ORDER.append(k)
        return f"[{CITE_ORDER.index(k) + 1}]"
    return re.sub(r"\{(\w+)\}", sub, text)


def resolve_all_citations():
    """Number references by first use, walking Part B in template order."""
    for key in C.PART_B:
        for b in C.PART_B[key]:
            for s in ([b[1]] if b[0] == "p" else [b[2]] if b[0] == "lead"
                      else b[1] if b[0] in ("ul", "ol") else []):
                cite(s)


# ------------------------------------------------------------ docx helpers
def set_font(run, size=11, bold=None, italic=None, color=None):
    rpr = run._r.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(a), "Arial")
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)


def add_text(par, text, size=11, bold=False, italic=False, color=None):
    """Append text, honouring **bold** and highlighting [TO FILL] markers."""
    for part in MARK.split(text):
        if not part:
            continue
        b = bold
        if part.startswith("**") and part.endswith("**"):
            part, b = part[2:-2], True
        r = par.add_run(part)
        set_font(r, size, b, italic, color)
        if part.startswith("[TO FILL:"):
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return par


def clear_runs(p_el):
    for ch in list(p_el):
        if ch.tag != qn("w:pPr"):
            p_el.remove(ch)


def first_rpr(p_el):
    r = p_el.find(qn("w:r"))
    rpr = r.find(qn("w:rPr")) if r is not None else None
    return copy.deepcopy(rpr) if rpr is not None else None


def set_label(par, text):
    """Keep the template's label styling but drop instructional text."""
    rpr = first_rpr(par._p)
    clear_runs(par._p)
    r = par.add_run(text)
    if rpr is not None:
        r._r.insert(0, rpr)


def set_field(par, label, value, size=11, upper=True):
    rpr = first_rpr(par._p)
    clear_runs(par._p)
    r = par.add_run(label + " ")
    if rpr is not None:
        r._r.insert(0, rpr)
    value = value if not upper or "[TO FILL" in value or "@" in value else value.upper()
    add_text(par, value, size=size, bold=False, color="000000")


def new_par_after(el, parent):
    p = OxmlElement("w:p")
    el.addnext(p)
    return Paragraph(p, parent)


def new_par_end(container_el, parent):
    p = OxmlElement("w:p")
    container_el.append(p)
    return Paragraph(p, parent)


def fmt(par, before=2, after=2, align="both", left=None, hang=None, keep=False):
    pf = par.paragraph_format
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.alignment = {"both": WD_ALIGN_PARAGRAPH.JUSTIFY, "left": WD_ALIGN_PARAGRAPH.LEFT,
                    "center": WD_ALIGN_PARAGRAPH.CENTER}[align]
    if left is not None:
        pf.left_indent = Inches(left)
    if hang is not None:
        pf.first_line_indent = Inches(-hang)
        pf.tab_stops.add_tab_stop(Inches(left))
    if keep:
        pf.keep_with_next = True


def bulletise(par):
    ppr = par._p.get_or_add_pPr()
    num = OxmlElement("w:numPr")
    il, ni = OxmlElement("w:ilvl"), OxmlElement("w:numId")
    il.set(qn("w:val"), "0")
    ni.set(qn("w:val"), "4")          # the template's own bullet list
    num.append(il)
    num.append(ni)
    ppr.insert(0, num)


def render_blocks(cell, blocks, size=11):
    """Append content blocks to the end of a table cell."""
    tc = cell._tc
    fig_no = [0]
    for b in blocks:
        kind = b[0]
        if kind == "p":
            p = new_par_end(tc, cell)
            fmt(p, 3, 3)
            add_text(p, cite(b[1]), size)
        elif kind == "lead":
            p = new_par_end(tc, cell)
            fmt(p, 4, 2, keep=not b[2])
            add_text(p, b[1] + (" " if b[2] else ""), size, bold=True)
            if b[2]:
                add_text(p, cite(b[2]), size)
        elif kind == "ul":
            for item in b[1]:
                p = new_par_end(tc, cell)
                bulletise(p)
                fmt(p, 1, 1, left=0.35, hang=0.2)
                add_text(p, cite(item), size)
        elif kind == "ol":
            for i, item in enumerate(b[1], 1):
                p = new_par_end(tc, cell)
                fmt(p, 2, 2, left=0.35, hang=0.3)
                add_text(p, f"{i}.\t", size, bold=True)
                add_text(p, cite(item), size)
        elif kind == "fig":
            _, name, width, cap = b
            p = new_par_end(tc, cell)
            fmt(p, 6, 0, "center", keep=True)
            p.add_run().add_picture(str(FIG / name), width=Inches(width))
            c = new_par_end(tc, cell)
            fmt(c, 2, 6, "center")
            add_text(c, cap, 9.5, italic=True)


SYMBOL_FONT = "Noto Sans Symbols 2"     # monochrome ballot boxes (Arial lacks them)


def symbol_runs(p_el):
    """Give every run holding a ballot box a font that has the glyph."""
    for r in p_el.iter(qn("w:r")):
        t = "".join(x.text or "" for x in r.iter(qn("w:t")))
        if any(ch in t for ch in "☐☑□✓"):
            rpr = r.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr"); r.insert(0, rpr)
            f = rpr.find(qn("w:rFonts"))
            if f is None:
                f = OxmlElement("w:rFonts"); rpr.insert(0, f)
            for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                f.set(qn(a), SYMBOL_FONT)


def cell_kids(cell):
    return [e for e in cell._tc if e.tag in (qn("w:p"), qn("w:tbl"))]


def strip_cell(cell, keep_first=1, keep_tables=True):
    """Remove everything after the label except nested tables."""
    for e in cell_kids(cell)[keep_first:]:
        if keep_tables and e.tag == qn("w:tbl"):
            continue
        cell._tc.remove(e)


def ensure_trailing_par(cell):
    if cell_kids(cell)[-1].tag == qn("w:tbl"):
        new_par_end(cell._tc, cell)


def fill_cell(cell, text, size=10, bold=False, align="left", upper=True):
    p = cell.paragraphs[0]
    for extra in cell.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)
    clear_runs(p._p)
    fmt(p, 1, 1, align)
    if upper and "@" not in text and "[TO FILL" not in text:
        text = text.upper()
    add_text(p, text, size, bold)


def append_value(par, value, size=10):
    add_text(par, " " + value, size, color="000000")


def cell_unique(row):
    seen, out = set(), []
    for c in row.cells:
        if id(c._tc) not in seen:
            seen.add(id(c._tc))
            out.append(c)
    return out


# --------------------------------------------------------------- the fill
def fill(doc, d):
    body = doc.element.body
    kids = list(body.iterchildren())
    P = {i: Paragraph(e, doc) for i, e in enumerate(kids) if e.tag == qn("w:p")}
    T = [Table(e, doc) for e in kids if e.tag == qn("w:tbl")]
    text = {i: p.text.strip() for i, p in P.items()}

    def find(pred, start=0):
        return next(i for i in sorted(P) if i >= start and pred(text[i]))

    idx = {
        "note": find(lambda t: t == "NOTE:"),
        "instr_end": find(lambda t: t.startswith("* ~ * ~")),
        "decl": find(lambda t: t == "DECLARATION"),
        "endorse": find(lambda t: t == "ENDORSEMENT"),
        "fee": find(lambda t: t.startswith("DETAILS OF PROCESSING FEES")),
    }
    idx["bank"] = find(lambda t: t.startswith("KARNATAKA STATE COUNCIL"), idx["fee"])
    idx["last"] = len(kids) - 1

    # Template highlights mark instructions; the filled form must not carry them.
    for h in body.iter(qn("w:highlight")):
        h.getparent().remove(h)

    for t in (T[0], T[3]):
        for tr in t._tbl.iterchildren(qn("w:tr")):
            for h in tr.iter(qn("w:trHeight")):
                if h.getparent().getparent() is tr:
                    h.getparent().remove(h)

    g, sc = d["guide"], d["spp_coordinator"]
    studs = d["students"]
    leader = studs[0]
    inst = C.INSTITUTION

    # ---- cover: header kept, instructions replaced by a title block
    for i in range(idx["note"]):
        if text.get(i, "").startswith("FORMAT FOR STUDENT PROJECT PROPOSAL"):
            set_label(P[i], "STUDENT PROJECT PROPOSAL FOR THE")
        if text.get(i, "").startswith("CALL FOR PROJECT PROPOSALS"):
            cover_anchor = P[i]
    clear_runs(cover_anchor._p)
    anchor = cover_anchor._p
    lines = [
        ("", 10, False), ("PROJECT TITLE", 11, True), (C.TITLE, 15, True), ("", 6, False),
        (f"Broad Theme {C.THEME_NO}: Artificial Intelligence, Data Science and Digital Technologies", 10.5, False),
        ("Sub-theme: Natural Language Processing (NLP) and Generative AI", 10.5, False),
        ("", 8, False), ("Submitted by", 11, True),
    ]
    lines += [(f"{s['name']} ({s['usn']})" + ("  (TEAM LEADER)" if s["leader"] else ""), 11, False)
              for s in studs]
    lines += [("", 8, False), ("Under the guidance of", 11, True),
              (f"{g['title']} {g['name']}, {g['designation'].title()}", 11, False),
              ("", 8, False),
              ("Department of Artificial Intelligence and Machine Learning", 11, True),
              ("BANGALORE INSTITUTE OF TECHNOLOGY", 12, True),
              ("K.R. Road, V.V. Pura, Bengaluru - 560004", 10.5, False),
              ("Affiliated to Visvesvaraya Technological University, Belagavi", 10.5, False)]
    first = True
    for t, sz, b in lines:
        p = Paragraph(anchor, doc) if first else new_par_after(anchor, doc)
        first = False
        anchor = p._p
        fmt(p, 1, 1, "center")
        add_text(p, t, sz, b, color="1F3864" if sz >= 15 else None)

    # ---- PART A
    A = T[0]
    rows = A.rows
    set_label(rows[1].cells[1].paragraphs[0], "Project Title:")
    strip_cell(rows[1].cells[1])
    p = new_par_end(rows[1].cells[1]._tc, rows[1].cells[1]); fmt(p, 2, 4, "left")
    add_text(p, C.TITLE, 12, True)
    set_label(rows[2].cells[1].paragraphs[0], "Keywords (5–8):")
    strip_cell(rows[2].cells[1])
    p = new_par_end(rows[2].cells[1]._tc, rows[2].cells[1]); fmt(p, 2, 4, "left")
    add_text(p, C.KEYWORDS, 11)

    th = rows[3].cells[1].paragraphs
    for p_ in th[1:7]:
        p_._p.getparent().remove(p_._p)
    set_field(th[7], "Theme No.:", C.THEME_NO)
    set_field(th[8], "Theme Name:", C.THEME_NAME)
    set_field(th[9], "3. Sub-theme / Focus Area:", C.SUB_THEME)

    ins = rows[4].cells[1].paragraphs
    set_field(ins[1], "Name of Institution:", inst["name"])
    set_field(ins[2], "Course Name:", inst["course"])
    set_field(ins[3], "Department Name:", inst["department"])
    set_field(ins[4], "Affiliated University:", inst["university"])
    set_field(ins[5], "5. District of Your Institution:", inst["district"])
    set_field(ins[6], "6. Complete Postal Address of the Institution with Pin code:", inst["address"])

    gp = rows[5].cells[1].paragraphs
    set_field(gp[1], "Project Guide Name:", f"{g['title']} {g['name']}")
    set_field(gp[2], "Project Guide Designation:", g["designation"])
    set_field(gp[3], "Project Guide Department:", g["department"])
    set_field(gp[4], "Project Guide Email id:", need(g.get("email"), "guide email"))
    set_field(gp[5], "Project Guide Mobile Number:", need(g.get("mobile"), "guide mobile"))
    cg = d.get("co_guide")
    if not cg:
        set_field(gp[6], "Project Co-Guide (if applicable):", "NOT APPLICABLE")
        for p_ in gp[7:]:
            p_._p.getparent().remove(p_._p)
    else:
        set_field(gp[7], "Project Co-Guide Name:", f"{cg['title']} {cg['name']}")
        set_field(gp[8], "Project Co-Guide Designation:", cg["designation"])
        set_field(gp[9], "Project Co-Guide Department:", cg["department"])
        set_field(gp[10], "Project Co-Guide Email id:", cg["email"])
        set_field(gp[11], "Project Co-Guide Mobile Number:", cg["mobile"])

    # ---- student table
    S = T[1]
    for k, s in enumerate(studs, 1):
        cells = cell_unique(S.rows[k])
        if s.get("photo"):
            add_photo(cells[1], OUT / "photos" / s["photo"])
        nm = f"{need(s.get('title'), s['name'].title() + ' title (Mr./Ms.)')} {s['name']}"
        fill_cell(cells[2], nm + ("\n(TEAM LEADER)" if s["leader"] else ""), 9, True)
        fix_newlines(cells[2])
        fill_cell(cells[3], s["usn"], 9)
        no_split(S.rows[k])
        for dp in cells[4].paragraphs:
            if not dp.text.strip():
                dp._p.getparent().remove(dp._p)
                continue
            for lab, val in (("Degree:", C.DEGREE), ("Branch:", C.BRANCH), ("Semester:", C.SEMESTER)):
                if dp.text.strip().startswith(lab):
                    set_field(dp, lab, val, 7.5)
        fill_cell(cells[5], need(s.get("category"), s["name"].title() + " category"), 9)
        fill_cell(cells[6], need(s.get("mobile"), s["name"].title() + " mobile"), 9)
        fill_cell(cells[7], need(s.get("email"), s["name"].title() + " email"), 8, upper=False)
    # Part A's template spacing is very loose; tighten it so the student table
    # and section 7 share a page.
    for t in (T[0], T[1]):
        for row in t.rows:
            for c in cell_unique(row):
                for cp in c.paragraphs:
                    pf = cp.paragraph_format
                    pf.space_before, pf.space_after, pf.line_spacing = Pt(2), Pt(2), 1.0
    for row in T[2].rows:
        no_split(row)

    # T[2]: row 0 is KSCST's note on the student table, row 1 is section 7
    note_row = T[2].rows[0]._tr
    note_row.getparent().remove(note_row)
    spp_cell = cell_unique(T[2].rows[0])[-1]
    for sp in spp_cell.paragraphs:
        t = sp.text.strip()
        for lab, val in (("SPP Coordinator Name:", title_name(sc, "SPP coordinator")),
                         ("SPP Coordinator Designation:", need(sc.get("designation"), "SPP coordinator designation")),
                         ("SPP Coordinator Email:", need(sc.get("email"), "SPP coordinator email")),
                         ("SPP Coordinator Mobile Number:", need(sc.get("mobile"), "SPP coordinator mobile"))):
            if t.startswith(lab):
                set_field(sp, lab, val)

    # ---- PART B
    B = T[3]
    for row in B.rows[1:]:
        cell = cell_unique(row)[-1]
        label = cell.paragraphs[0].text.strip()
        if label.startswith(("Relevance", "Work Plan", "Facilities", "Budget", "Student Details")):
            no_split(row)
        key = next((k for k in C.PART_B if label.startswith(k)), None)
        if key:
            set_label(cell.paragraphs[0], key + ":")
            strip_cell(cell, keep_tables=False)
            render_blocks(cell, C.PART_B[key])
        elif label.startswith("Relevance"):
            fill_relevance(cell)
        elif label.startswith("Work Plan"):
            fill_workplan(cell)
        elif label.startswith("Facilities"):
            set_label(cell.paragraphs[0], "Facilities Available:")
            strip_cell(cell)
            ft = cell.tables[0]
            for r, (k, v) in zip(ft.rows, d["facilities"].items()):
                fill_cell(cell_unique(r)[1], v, 10, upper=False)
            ensure_trailing_par(cell)
        elif label.startswith("Major Requirements"):
            set_label(cell.paragraphs[0], "Major Requirements for the Project:")
            strip_cell(cell, keep_tables=False)
            render_blocks(cell, C.REQUIREMENTS)
        elif label.startswith("Budget"):
            fill_budget(cell, d["budget"])
        elif label.startswith("References"):
            set_label(cell.paragraphs[0], "References (IEEE format):")
            strip_cell(cell, keep_tables=False)
            for n, k in enumerate(CITE_ORDER, 1):
                p = new_par_end(cell._tc, cell)
                fmt(p, 1, 1, "left", left=0.42, hang=0.42)
                add_text(p, f"[{n}]\t{C.REFERENCES[k]}", 9.5)
        elif label.startswith("Processing Fee"):
            fill_fee_section(cell, d["payment"])
        elif label.startswith("Student Details with Signature"):
            st = cell.tables[0]
            for r, s in zip(st.rows[1:], studs):
                cs = cell_unique(r)
                fill_cell(cs[1], s["name"], 9.5)
                fill_cell(cs[2], s["usn"], 9.5)

    signature_block(T[4], [("SPP Coordinator", sc, "SPP coordinator"), ("Guide", g, "guide")])
    # five blank lines separate Part B from the signatures; two leave room to sign
    nxt, dropped = B._tbl.getnext(), 0
    while nxt is not None and nxt.tag == qn("w:p") and not Paragraph(nxt, doc).text.strip() and dropped < 3:
        after = nxt.getnext()
        nxt.getparent().remove(nxt)
        nxt, dropped = after, dropped + 1
    for i in range(idx["instr_end"], idx["decl"]):
        if text.get(i, "") and P[i]._p.find(".//" + qn("w:sdt")) is not None:
            if not text[i].startswith("☐ Any other") and "Any other" not in text[i]:
                for t_ in P[i]._p.iter(qn("w:t")):
                    t_.text = t_.text.replace("☐", "☑")
            symbol_runs(P[i]._p)

    # ---- DECLARATION
    decl_fields = [("Title of the Project:", C.TITLE),
                   ("Broad Theme:", f"{C.THEME_NO}) {C.THEME_NAME}"),
                   ("Sub-theme / Focus Area:", C.SUB_THEME),
                   ("Department:", inst["department"]),
                   ("Institution:", inst["name"])]
    for i in range(idx["decl"], idx["endorse"]):
        for lab, val in decl_fields:
            if text.get(i, "").startswith(lab):
                set_field(P[i], lab, val, 11)
    dt = next(t for t in T if t._tbl in kids[idx["decl"]:idx["endorse"]]
              and t.rows[0].cells[0].text.startswith("Sl."))
    for r, s in zip(dt.rows[1:], studs):
        cs = cell_unique(r)
        fill_cell(cs[1], s["name"], 10)
        fill_cell(cs[2], s["usn"], 10)
    sig_tables = [t for t in T if t.rows[0].cells[0].text.strip().startswith("(Name & Signature of")]
    signature_block(sig_tables[1], [("SPP Coordinator", sc, "SPP coordinator"), ("Guide", g, "guide")])

    # ---- ENDORSEMENT (printed on department letterhead: leave room at the top)
    en = P[idx["endorse"]]
    for br in list(en._p.iter(qn("w:br"))):
        br.getparent().getparent().remove(br.getparent())
    en.paragraph_format.page_break_before = True
    en.paragraph_format.space_before = Pt(80)
    names = iter(studs)
    for i in range(idx["endorse"], idx["fee"]):
        t = text.get(i, "")
        if t.startswith("Mr./Ms."):
            s = next(names)
            clear_runs(P[i]._p)
            add_text(P[i], f"{need(s.get('title'), s['name'].title() + ' title (Mr./Ms.)')} "
                     f"**{s['name']}** ({s['usn']})", 12)
        elif t.startswith("are bonafide final-year students"):
            clear_runs(P[i]._p)
            add_text(P[i], "are bonafide final-year students of the Department of "
                     "**Artificial Intelligence and Machine Learning**, pursuing **B.E.** at "
                     "**Bangalore Institute of Technology, Bengaluru** (Name of the Institution).", 12)
    hod, pr = d["hod"], d["principal"]
    endorse_sig = next(t for t in T if t.rows[0].cells[-1].text.strip().startswith("(Signature of HoD"))
    signature_block(endorse_sig, [("Guide", g, "guide"), ("SPP Coordinator", sc, "SPP coordinator"),
                                  ("HoD", {"title": "", **hod}, "HoD")])
    princ = next(t for t in T if t.rows[0].cells[-1].text.strip().startswith("(Signature of the Principal"))
    signature_block(princ, [None, None, ("Principal", {"title": "", **pr}, "principal")])

    # ---- FEE PAGE
    fee_t = [t for t in T if t.rows[0].cells[0].text.strip().startswith("TITLE OF THE PROJECT")][0]
    pay_t = [t for t in T if t.rows[0].cells[0].text.strip().startswith("BANK REF")][0]
    pm = d["payment"]
    vals = [C.TITLE, f"{leader['name']}",
            need(leader.get("email"), leader["name"].title() + " email"),
            need(leader.get("mobile"), leader["name"].title() + " mobile")]
    for r, v in zip(fee_t.rows, vals):
        fill_cell(cell_unique(r)[2], v, 10, upper="@" not in v)
    pvals = [need(pm.get("utr"), "payment UTR / UPI reference (12 digits)"),
             need(pm.get("transaction_id"), "payment transaction ID"),
             f"{need(pm.get('account_holder'), 'payment account holder name')}, "
             f"{need(pm.get('account_holder_mobile'), 'payment account holder mobile')}",
             need(pm.get("bank"), "payment bank name"),
             None,
             need(pm.get("date"), "payment date (DD/MM/YYYY)"),
             need(pm.get("time"), "payment time"),
             need(pm.get("mode"), "payment mode (UPI or NEFT)")]
    for r, v in zip(pay_t.rows, pvals):
        if v is not None:
            fill_cell(cell_unique(r)[2], v, 10)
    last_sig = [t for t in T if t.rows[0].cells[0].text.strip().startswith("(Name & Signature of")
                and "team leader" in t.rows[0].cells[0].text][0]
    c0, c1 = cell_unique(last_sig.rows[0])
    p = new_par_end(c0._tc, c0); fmt(p, 2, 0, "center"); add_text(p, leader["name"], 10, True)
    p = new_par_end(c1._tc, c1); fmt(p, 2, 0, "center"); add_text(p, f"{g['title']} {g['name']}", 10, True)
    return kids, idx


def fix_newlines(cell):
    for t_ in cell._tc.iter(qn("w:t")):
        if "\n" in t_.text:
            a, b = t_.text.split("\n", 1)
            t_.text = a
            r = t_.getparent()
            br = OxmlElement("w:br")
            t2 = OxmlElement("w:t"); t2.text = b
            r.append(br); r.append(t2)


def add_photo(cell, path):
    from PIL import Image
    if not path.exists():
        raise SystemExit(f"photo not found: {path}")
    im = Image.open(path).convert("RGB")
    w, h = im.size
    target = 35 / 45                             # passport aspect
    if w / h > target:
        nw = int(h * target); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / target); im = im.crop((0, (h - nh) // 4, w, (h - nh) // 4 + nh))
    im.thumbnail((360, 460))
    tmp = Path(tempfile.mkdtemp()) / (path.stem + ".jpg")
    im.save(tmp, quality=85)
    p = cell.paragraphs[0]
    fmt(p, 2, 2, "center")
    p.add_run().add_picture(str(tmp), width=Inches(0.78))


def signature_block(table, who):
    """who: list per column of (role, person, label) or None to skip."""
    for col, w in enumerate(who):
        if not w:
            continue
        role, person, label = w
        cells = [cell_unique(r)[col] for r in table.rows[:3]]
        name = (f"{person.get('title', '')} {person.get('name', '')}".strip()
                if person.get("name") else need("", f"{label} name"))
        p = new_par_end(cells[0]._tc, cells[0])
        fmt(p, 2, 0, "center")
        add_text(p, name.upper() if "[TO FILL" not in name else name, 9.5, True)
        for c, key, lab in ((cells[1], "email", "email"), (cells[2], "mobile", "mobile")):
            par = c.paragraphs[0]
            add_text(par, " " + need(person.get(key), f"{label} {lab}"), 9.5, color="000000")


def fill_relevance(cell):
    ps = cell.paragraphs
    set_label(ps[0], "Relevance:")
    ps[1]._p.getparent().remove(ps[1]._p)
    for p in cell.paragraphs[1:]:
        t = p.text.replace("□", "").strip()
        on = any(t.startswith(opt) for opt in C.RELEVANCE)
        for t_ in p._p.iter(qn("w:t")):
            if "□" in t_.text:
                t_.text = t_.text.replace("□", "☑" if on else "☐")
        symbol_runs(p._p)
        if on and t.startswith("SDGs"):
            add_text(p, f": {C.SDG_NOTE}", 11, True)
        if on and t.startswith("Others"):
            for t_ in p._p.iter(qn("w:t")):
                t_.text = t_.text.rstrip()
            add_text(p, " " + C.RELEVANCE_OTHER.title(), 11)


def fill_workplan(cell):
    set_label(cell.paragraphs[0], "Work Plan (month-wise; ✓ marks the active months):")
    strip_cell(cell)
    wt = cell.tables[0]
    for j, m in enumerate(C.MONTHS, 1):
        c = cell_unique(wt.rows[0])[j]
        p = new_par_end(c._tc, c)
        fmt(p, 0, 0, "center")
        add_text(p, m, 8)
    for r in wt.rows[1:]:
        cs = cell_unique(r)
        act = cs[0].text.strip()
        for j in C.WORK_PLAN.get(act, []):
            fill_cell(cs[j], "✓", 12, True, "center")
            symbol_runs(cs[j].paragraphs[0]._p)
    keep_table_together(wt)
    ensure_trailing_par(cell)


def no_split(row):
    """Short boxes move to the next page whole instead of breaking mid-table."""
    trpr = row._tr.get_or_add_trPr()
    if trpr.find(qn("w:cantSplit")) is None:
        trpr.append(OxmlElement("w:cantSplit"))


def keep_table_together(table):
    for row in table.rows[:-1]:
        for c in cell_unique(row):
            for p in c.paragraphs:
                p.paragraph_format.keep_with_next = True


def fill_budget(cell, budget):
    set_label(cell.paragraphs[0], "Budget Estimate:")
    strip_cell(cell)
    bt = cell.tables[0]
    total = 0
    for r in bt.rows[1:]:
        cs = cell_unique(r)
        item = cs[0].text.strip()
        if item == "Total":
            fill_cell(cs[1], rupees(total), 10, True, "center")
        else:
            v = budget.get(item, 0)
            total += v
            fill_cell(cs[1], rupees(v), 10, False, "center")
    keep_table_together(bt)
    p = new_par_end(cell._tc, cell)
    fmt(p, 4, 2)
    add_text(p, "Basis: ", 10, True)
    add_text(p, C.BUDGET_NOTE, 10)


def fill_fee_section(cell, pm):
    ps = cell.paragraphs
    set_label(ps[0], "Processing Fee Payment Details:")
    for p in ps[1:10]:                                   # KSCST's own instructions
        p._p.getparent().remove(p._p)
    ps = cell.paragraphs
    mode = need(pm.get("mode"), "payment mode (UPI or NEFT)")
    set_field(ps[2], "Mode of Payment:", mode)
    set_field(ps[3], "Transaction / UTR / Reference Number:", need(pm.get("utr"), "payment UTR / UPI reference (12 digits)"))
    set_field(ps[4], "Date of Payment:", need(pm.get("date"), "payment date (DD/MM/YYYY)"))
    set_field(ps[5], "Amount Paid:", "₹1,180/- (₹1,000/- + 18% GST)", upper=False)
    set_field(ps[6], "Name of Account Holder:", need(pm.get("account_holder"), "payment account holder name"))
    nb = pm.get("bank") if mode.upper() == "NEFT" else ("NOT APPLICABLE (UPI PAYMENT)" if mode.upper() == "UPI" else "")
    set_field(ps[7], "Name of Bank (for NEFT):", need(nb, "payment bank name"))
    nu = pm.get("upi_id") if mode.upper() == "UPI" else ("NOT APPLICABLE (NEFT PAYMENT)" if mode.upper() == "NEFT" else "")
    set_field(ps[8], "UPI ID Used:", need(nu, "UPI ID used"), upper=False)
    att = ps[9]
    rpr = first_rpr(att._p)
    clear_runs(att._p)
    r = att.add_run("Attachment: ")
    if rpr is not None:
        r._r.insert(0, rpr)
    add_text(att, "☑", 11)
    symbol_runs(att._p)
    add_text(att, " Copy of UPI Payment Receipt / NEFT Transaction Receipt enclosed.", 11)


# --------------------------------------------------------- split & convert
def prune(doc, kids, keep):
    """Keep original elements by index; inserted ones follow their predecessor."""
    body = doc.element.body
    orig = {id(e): i for i, e in enumerate(kids)}
    state = False
    for e in list(body):
        if id(e) in orig:
            state = orig[id(e)] in keep
        if not state:
            body.remove(e)


def strip_leading_break(doc):
    for e in doc.element.body.iterchildren():
        if e.tag == qn("w:p"):
            for br in list(e.iter(qn("w:br"))):
                if br.get(qn("w:type")) == "page":
                    br.getparent().remove(br)
            Paragraph(e, doc).paragraph_format.page_break_before = False
            return


def build_docs(d):
    outs = {}
    for part in (1, 2, 3):
        doc = docx.Document(str(TEMPLATE))
        kids, idx = fill(doc, d)
        CITE_ORDER[:] = CITE_ORDER  # numbering already fixed by resolve_all_citations
        last = idx["last"]
        if part == 1:
            keep = set(range(0, idx["note"])) | set(range(idx["instr_end"] + 1, idx["decl"])) \
                | set(range(idx["fee"], idx["bank"])) | {last}
        elif part == 2:
            keep = set(range(idx["decl"], idx["fee"])) | {last}
        else:
            keep = set(range(idx["fee"], idx["bank"])) | {last}
        prune(doc, kids, keep)
        if part == 1:
            drop_empty_tail_before_fee(doc)
        if part in (2, 3):
            strip_leading_break(doc)
            carry_footer(doc, kids)
        if part == 2:
            tighten_declaration(doc)
        path = OUT / "word" / NAMES[part].replace(".pdf", ".docx")
        path.parent.mkdir(exist_ok=True)
        doc.save(str(path))
        outs[part] = path
    return outs


def carry_footer(doc, kids):
    """The footer belongs to the first template section, which parts 2-3 drop."""
    first = next(e for e in kids if e.find(".//" + qn("w:sectPr")) is not None and e.tag == qn("w:p"))
    refs = first.find(".//" + qn("w:sectPr")).findall(qn("w:footerReference"))
    final = doc.element.body.find(qn("w:sectPr"))
    for r in reversed(refs):
        final.insert(0, copy.deepcopy(r))


def tighten_declaration(doc):
    """Drop one empty spacer before each signature block so the declaration fits two pages."""
    body = doc.element.body
    ch = list(body.iterchildren())
    for i, e in enumerate(ch):
        if e.tag == qn("w:tbl") and Table(e, doc).rows[0].cells[0].text.strip().startswith("(Name & Signature of"):
            j = i - 1
            if ch[j].tag == qn("w:p") and not Paragraph(ch[j], doc).text.strip():
                body.remove(ch[j])
            break


def drop_empty_tail_before_fee(doc):
    """Empty spacer paragraphs left before the fee page create a blank page."""
    body = doc.element.body
    ch = list(body.iterchildren())
    fee = next(i for i, e in enumerate(ch) if e.tag == qn("w:p")
               and Paragraph(e, doc).text.strip().startswith("DETAILS OF PROCESSING FEES"))
    j = fee - 1
    while j > 0 and ch[j].tag == qn("w:p") and not Paragraph(ch[j], doc).text.strip() \
            and ch[j].find(".//" + qn("w:sectPr")) is None and ch[j].find(".//" + qn("w:drawing")) is None:
        body.remove(ch[j])
        j -= 1


def to_pdf(docx_path):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(OUT),
                    str(docx_path)], check=True, capture_output=True)
    return OUT / (docx_path.stem + ".pdf")


def pages(pdf):
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", out).group(1))


# --------------------------------------------------------- form answers
def plain(blocks):
    out, fig = [], 0
    for b in blocks:
        if b[0] == "p":
            out.append(cite(b[1]))
        elif b[0] == "lead":
            out.append((b[1] + " " + cite(b[2])).strip())
        elif b[0] == "ul":
            out += ["- " + cite(i).replace("**", "") for i in b[1]]
        elif b[0] == "ol":
            out += [f"{n}. " + cite(i) for n, i in enumerate(b[1], 1)]
        elif b[0] == "fig":
            fig += 1
            if out and out[-1].endswith(":"):        # an empty lead introduces it
                out[-1] += f" SEE FIGURE {fig} IN THE UPLOADED PROPOSAL."
    return "\n".join(out)


def up(s):
    """Form rule: everything except email ids in UPPERCASE, single spaces."""
    s = re.sub(r"[ \t]+", " ", s)
    parts = re.split(r"(\S+@\S+)", s)
    return "".join(p if "@" in p else p.upper() for p in parts)


def form_rows(d, files):
    g, sc, pm = d["guide"], d["spp_coordinator"], d["payment"]
    R = []
    sec = lambda t: R.append(("SECTION", t, None))
    q = lambda label, val, kind="text": R.append((label, val, kind))
    sec("PART–A: GENERAL INFORMATION")
    q("1. PROJECT TITLE", C.TITLE)
    q("2. KEYWORDS (5–8)", C.KEYWORDS)
    q("3. PROJECT BROAD THEME (choose)", f"{C.THEME_NO}) {C.THEME_NAME}", "choice")
    q("Sub-theme (next page, choose)", C.SUB_THEME, "choice")
    sec("4. INSTITUTION DETAILS")
    inst = C.INSTITUTION
    q("1. NAME OF INSTITUTION (dropdown)", inst["name"], "choice")
    q("2. COURSE NAME (dropdown)", inst["course"], "choice")
    q("3. DEPARTMENT NAME (dropdown)", inst["department"], "choice")
    q("4. AFFILIATED UNIVERSITY", inst["university"])
    q("5. DISTRICT OF YOUR INSTITUTION (dropdown)", inst["district"], "choice")
    q("6. COMPLETE POSTAL ADDRESS OF THE INSTITUTION WITH PINCODE", inst["address"])
    sec("5. PROJECT GUIDES DETAILS")
    q("1. TITLE OF THE PROJECT GUIDE (choose)", g["title"], "choice")
    q("2. PROJECT GUIDE NAME", g["name"])
    q("3. PROJECT GUIDE DESIGNATION", g["designation"])
    q("4. PROJECT GUIDE DEPARTMENT", g["department"])
    q("5. PROJECT GUIDE EMAIL ID", need(g.get("email"), "guide email"))
    q("6. PROJECT GUIDE MOBILE NUMBER", need(g.get("mobile"), "guide mobile"))
    q("7–12. CO-GUIDE FIELDS", "LEAVE BLANK (NO CO-GUIDE)" if not d.get("co_guide") else "SEE PROPOSAL", "note")
    sec("6. STUDENT TEAM DETAILS")
    for n, s in enumerate(d["students"], 1):
        tag = f"STUDENT {n}" + (" (TEAM LEADER)" if s["leader"] else "")
        nm = s["name"].title()
        q(f"PASSPORT-SIZE PHOTOGRAPH OF {tag} (upload)",
          f"photos/{s['photo']}" if s.get("photo") else need("", nm + " photo file"), "file")
        q(f"TITLE OF {tag} (choose)", need(s.get("title"), nm + " title (Mr./Ms.)"), "choice")
        q(f"NAME OF {tag}", s["name"])
        q(f"REGISTRATION NO. / USN OF {tag}", s["usn"])
        q(f"DEGREE OF STUDENT {n} (choose)", C.DEGREE, "choice")
        q(f"BRANCH OF STUDENT {n} (choose)", C.BRANCH, "choice")
        q(f"SEMESTER OF {tag} (dropdown)", C.SEMESTER, "choice")
        q(f"CATEGORY OF STUDENT {n} AS PER COLLEGE RECORDS (choose)",
          need(s.get("category"), nm + " category"), "choice")
        q(f"MOBILE NO. OF {tag}", need(s.get("mobile"), nm + " mobile"))
        q(f"EMAIL ID OF {tag}", need(s.get("email"), nm + " email"))
    sec("7. SPP COORDINATOR DETAILS")
    q("1. TITLE OF SPP COORDINATOR (choose)", need(sc.get("title"), "SPP coordinator title"), "choice")
    q("2. SPP COORDINATOR NAME", need(sc.get("name"), "SPP coordinator name"))
    q("3. SPP COORDINATOR DESIGNATION", need(sc.get("designation"), "SPP coordinator designation"))
    q("4. SPP COORDINATOR EMAIL ID", need(sc.get("email"), "SPP coordinator email"))
    q("5. SPP COORDINATOR MOBILE NO.", need(sc.get("mobile"), "SPP coordinator mobile"))
    sec("PART–B: PROJECT DESCRIPTION")
    labels = {"Background and Need of the Project": "8. BACKGROUND AND NEED OF THE PROJECT",
              "Review of Existing Work": "9. REVIEW OF EXISTING WORK",
              "Problem Statement": "10. PROBLEM STATEMENT", "Objectives": "11. OBJECTIVES",
              "Innovation / Novelty": "12. INNOVATION / NOVELTY",
              "Proposed Methodology": "13. PROPOSED METHODOLOGY",
              "Expected Deliverables": "14. EXPECTED DELIVERABLES",
              "Expected Outcomes and Impact": "15. EXPECTED OUTCOMES AND IMPACT"}
    for k, lab in labels.items():
        q(lab, plain(C.PART_B[k]), "para")
    q("16. RELEVANCE (tick these)", "\n".join(C.RELEVANCE_FORM), "choice")
    sec("17. WORK PLAN (tick the months)")
    for act, ms in C.WORK_PLAN.items():
        q(act.upper(), ", ".join(f"MONTH {m}" for m in ms), "choice")
    sec("18. FACILITIES AVAILABLE")
    for n, (k, v) in enumerate(d["facilities"].items(), 1):
        q(f"{n}. {k.upper()}", v, "para")
    q("19. MAJOR REQUIREMENTS FOR THE PROJECT", plain(C.REQUIREMENTS), "para")
    sec("20. BUDGET ESTIMATE")
    total = 0
    for n, (k, v) in enumerate(d["budget"].items(), 1):
        total += v
        q(f"{n}. {k.upper()}", rupees(v))
    q("8. TOTAL AMOUNT", rupees(total))
    q("21. REFERENCES", "\n".join(f"[{n}] {C.REFERENCES[k]}" for n, k in enumerate(CITE_ORDER, 1)), "para")
    sec("22. UPLOAD THE FOLLOWING DOCUMENTS (PDF)")
    q("1. PROJECT PROPOSAL", NAMES[1] + "  (signed scan, under 3 MB)", "file")
    q("2. DECLARATION ENDORSEMENT", NAMES[2] + "  (signed scan, under 1 MB)", "file")
    q("3. DETAILS OF PROCESSING FEES MADE THROUGH NEFT / UPI PAYMENT", NAMES[3] + "  (signed scan, under 1 MB)", "file")
    q("4. ANY OTHER SUPPORTING DOCUMENTS (optional)", "LEAVE EMPTY", "note")
    sec("23. PROCESSING FEE PAYMENT DETAILS")
    mode = need(pm.get("mode"), "payment mode (UPI or NEFT)")
    q("1. MODE OF PAYMENT (choose)", mode, "choice")
    q("2. TRANSACTION / UTR / REFERENCE NUMBER", need(pm.get("utr"), "payment UTR / UPI reference (12 digits)"))
    q("3. DATE OF PAYMENT", need(pm.get("date"), "payment date (DD/MM/YYYY)"))
    q("4. AMOUNT PAID (choose)", "Rs. 1,180/- (Inclusive of 18% GST)", "choice")
    q("5. NAME OF ACCOUNT HOLDER", need(pm.get("account_holder"), "payment account holder name"))
    if mode.upper() == "NEFT":
        q("6. NAME OF BANK", need(pm.get("bank"), "payment bank name"))
    else:
        q("6. UPI ID USED", need(pm.get("upi_id"), "UPI ID used"))
    q("7. COPY OF PAYMENT RECEIPT (upload)", NAMES[4], "file")
    sec("MANDATORY ATTACHMENTS")
    q("Tick every box", "ALL BOXES", "note")
    return R


def write_form_sheet(d, files):
    rows = form_rows(d, files)
    esc = html.escape
    items = []
    for label, val, kind in rows:
        if label == "SECTION":
            items.append(f'<h2>{esc(val)}</h2>')
            continue
        shown = val if kind in ("file", "note", "choice") or "[TO FILL" in val else up(val)
        missing = "[TO FILL" in shown
        cls = "row miss" if missing else "row"
        btn = "" if kind in ("file", "note") or missing else '<button type="button">Copy</button>'
        tag = {"choice": '<span class="k">select</span>', "file": '<span class="k">upload</span>',
               "note": '<span class="k">note</span>'}.get(kind, "")
        items.append(f'<div class="{cls}"><div class="q">{esc(label)} {tag}</div>'
                     f'<pre class="a">{esc(shown)}</pre>{btn}</div>')
    filelist = "".join(
        f"<li><code>{esc(p.name)}</code> {p.stat().st_size / 1e6:.2f} MB, {pages(p)} pages"
        f"{'' if p.stat().st_size / 1e6 < LIMIT_MB[n] else ' <b>OVER LIMIT</b>'}</li>"
        for n, p in sorted(files.items()))
    miss = "".join(f"<li>{esc(m)}</li>" for m in MISSING) or "<li>Nothing. Every field is filled.</li>"
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>KSCST Form Answers</title>
<style>
:root{{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--card:#fff;--line:#e4e1da;--acc:#1f4e8c;--warn:#fff3c4;--warnfg:#6a4b00}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--fg:#ecebe7;--mut:#a3a29d;--card:#1f1f1d;--line:#34332f;--acc:#8db4ee;--warn:#3d3415;--warnfg:#f1d58a}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}}
main{{max-width:900px;margin:0 auto;padding:24px 16px 80px}}h1{{font-size:24px;margin:0 0 4px}}
h2{{font-size:15px;letter-spacing:.04em;color:var(--acc);margin:32px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}}
.sub{{color:var(--mut);margin:0 0 16px}}.box{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:12px 0}}
.row{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:8px 0;position:relative}}
.row.miss{{background:var(--warn);color:var(--warnfg)}}.q{{font-size:12.5px;color:var(--mut);margin-bottom:4px;padding-right:64px}}
.row.miss .q{{color:inherit}}.k{{font-size:11px;border:1px solid var(--line);border-radius:4px;padding:0 4px;margin-left:4px}}
pre.a{{margin:0;white-space:pre-wrap;word-break:break-word;font:14px/1.45 ui-monospace,monospace}}
button{{position:absolute;top:8px;right:8px;font:12px system-ui;padding:4px 10px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--fg);cursor:pointer}}
button.ok{{border-color:var(--acc);color:var(--acc)}}ol li,ul li{{margin:3px 0}}code{{font-size:13px}}
</style></head><body><main>
<h1>KSCST SPP 50th Series: form answers</h1>
<p class="sub">Copy each answer into <a href="https://forms.gle/VPPewZnbUhw1V8KdA">the Google Form</a> in order. Answers are already in UPPERCASE (emails excepted), as the form requires. Deadline: 30 November 2026, 5:00 PM.</p>
<div class="box"><b>Before you open the form</b><ol>
<li>Pay Rs. 1,180 in one UPI/NEFT transaction to KSCST (account and QR on the last page of <code>source/03_KSCST_SPP_50S_Proposal_Format_2026-27.docx</code>). Save the receipt.</li>
<li>Put the payment details and every missing field below into <code>details.json</code>, add photos to <code>photos/</code>, then rebuild: <code>python3 ~/Work/SETU_v2/SETU/docs/KSCST/build_kscst.py</code></li>
<li>Print the three PDFs. Get signatures and seals: proposal (guide, SPP coordinator), declaration (all four students, guide, SPP coordinator), endorsement on department letterhead (guide, SPP coordinator, HoD, Principal), fee page (team leader, guide).</li>
<li>Scan each signed document to PDF and shrink it to its limit: <code>build_kscst.py compress scan.pdf 1</code> (then 2, 3). Turn the receipt screenshot into file 04: <code>build_kscst.py receipt screenshot.png</code></li>
<li>Sign in with a Gmail ID (team leader) and fill the form below. Nothing can be changed after submitting.</li></ol></div>
<div class="box"><b>Still to fill ({len(MISSING)})</b><ul>{miss}</ul></div>
<div class="box"><b>Files built</b><ul>{filelist}</ul></div>
{''.join(items)}
</main><script>
document.querySelectorAll('button').forEach(b=>b.addEventListener('click',async()=>{{
 const t=b.parentElement.querySelector('pre').innerText;
 try{{await navigator.clipboard.writeText(t)}}catch(e){{const r=document.createRange();r.selectNode(b.parentElement.querySelector('pre'));getSelection().removeAllRanges();getSelection().addRange(r);document.execCommand('copy')}}
 b.textContent='Copied';b.classList.add('ok');setTimeout(()=>{{b.textContent='Copy';b.classList.remove('ok')}},1400)}}));
</script></body></html>"""
    path = OUT / "START_HERE_form_answers.html"
    path.write_text(page)
    return path


# ------------------------------------------------------------ subcommands
def compress(src, slot):
    slot = int(slot)
    dst = OUT / "upload" / NAMES[slot]
    dst.parent.mkdir(exist_ok=True)
    for dpi in (200, 150, 120, 100, 85, 72):
        subprocess.run(["gs", "-q", "-dBATCH", "-dNOPAUSE", "-dSAFER", "-sDEVICE=pdfwrite",
                        "-dCompatibilityLevel=1.5", "-dDownsampleColorImages=true",
                        "-dDownsampleGrayImages=true", f"-dColorImageResolution={dpi}",
                        f"-dGrayImageResolution={dpi}", "-dJPEGQ=70",
                        f"-sOutputFile={dst}", str(src)], check=True)
        mb = dst.stat().st_size / 1e6
        if mb < LIMIT_MB[slot] * 0.95:
            print(f"{dst}  {mb:.2f} MB at {dpi} dpi (limit {LIMIT_MB[slot]} MB)")
            return
    print(f"WARNING: {dst} is still {mb:.2f} MB; rescan in black and white or at lower resolution")


def receipt(img):
    from PIL import Image
    dst = OUT / "upload" / NAMES[4]
    dst.parent.mkdir(exist_ok=True)
    im = Image.open(img).convert("RGB")
    im.thumbnail((1400, 2400))
    im.save(dst, "PDF", resolution=150, quality=80)
    print(f"{dst}  {dst.stat().st_size / 1e6:.2f} MB")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "compress":
        return compress(sys.argv[2], sys.argv[3])
    if len(sys.argv) > 1 and sys.argv[1] == "receipt":
        return receipt(sys.argv[2])
    d = load_details()
    resolve_all_citations()
    docs = build_docs(d)
    pdfs = {}
    for n, p in docs.items():
        pdfs[n] = to_pdf(p)
    sheet = write_form_sheet(d, pdfs)
    for n, p in pdfs.items():
        print(f"{p.name}: {pages(p)} pages, {p.stat().st_size / 1e6:.2f} MB (limit {LIMIT_MB[n]} MB)")
    print(f"form sheet: {sheet}")
    print(f"still to fill: {len(MISSING)}")
    for m in MISSING:
        print("  -", m)


if __name__ == "__main__":
    main()
