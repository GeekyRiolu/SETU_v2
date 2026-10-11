#!/usr/bin/env python3
"""Build a Word version of the Project Phase-II report from the LaTeX source.

Pandoc cannot draw TikZ or pgfplots, so every such figure is first rendered to
a cropped PNG at the report's own text width and substituted into a throwaway
copy of the LaTeX tree. The resulting .docx is then patched so the front matter
keeps the centring the LaTeX had.

    python3 make_docx.py            # writes SETU_Project_Phase-II_Report.docx

Needs: tectonic, pandoc, pdftoppm (poppler) and Pillow.
"""
import os, re, shutil, subprocess, sys, zipfile, glob

HERE  = os.path.dirname(os.path.abspath(__file__))
SRC   = os.path.join(HERE, "latex")
WORK  = os.path.join(HERE, ".docxbuild")
OUT   = os.path.join(HERE, "SETU_Project_Phase-II_Report.docx")
TEX   = shutil.which("tectonic") or os.path.expanduser("~/.local/bin/tectonic")
PANDOC= shutil.which("pandoc")   or os.path.expanduser("~/.local/bin/pandoc")
DPI   = 200
TEXTWIDTH = "152.85mm"          # A4 minus the report's 1.25in / 1in margins


# ---------------------------------------------------------------- figures ---
def tikz_blocks(s):
    """(start, end) of each top-level tikzpicture."""
    out, i = [], 0
    while True:
        b = s.find(r"\begin{tikzpicture}", i)
        if b < 0:
            return out
        depth, j = 0, b
        while True:
            nb = s.find(r"\begin{tikzpicture}", j + 1)
            ne = s.find(r"\end{tikzpicture}", j + 1)
            if ne < 0:
                return out
            if 0 <= nb < ne:
                depth += 1; j = nb
            elif depth:
                depth -= 1; j = ne
            else:
                e = ne + len(r"\end{tikzpicture}"); break
        out.append((b, e)); i = e


def unwrap_scalebox(t):
    """pandoc drops everything inside \\scalebox, so take the content out."""
    out, i = [], 0
    while True:
        m = re.search(r"\\scalebox\{[0-9.]+\}\{%?\s*\n?", t[i:])
        if not m:
            out.append(t[i:]); return "".join(out)
        b = i + m.start(); out.append(t[i:b])
        j, depth = i + m.end(), 1
        while depth:
            c = t[j]
            if c == "\\": j += 2; continue
            if c == "{": depth += 1
            elif c == "}": depth -= 1
            j += 1
        out.append(t[i + m.end(): j - 1]); i = j


def stage_sources():
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    tree = os.path.join(WORK, "latex")
    shutil.copytree(SRC, tree)
    for junk in glob.glob(os.path.join(tree, "main.*")):
        if not junk.endswith(".tex"):
            os.remove(junk)

    figs = []
    for f in sorted(os.listdir(os.path.join(tree, "chapters"))):
        p = os.path.join(tree, "chapters", f)
        s = open(p).read()
        parts, last = [], 0
        for b, e in tikz_blocks(s):
            name = "auto%02d" % (len(figs) + 1)
            figs.append(s[b:e])
            parts.append(s[last:b])
            parts.append(r"\includegraphics[width=\linewidth]{figures/%s.png}" % name)
            last = e
        s = "".join(parts) + s[last:] if figs and parts else s
        open(p, "w").write(s)

    # pandoc only knows the standard list environments, and drops the contents
    # of \scalebox; \textsc inside math defeats its math reader
    ENVS = {"bullets": "itemize", "paperpoints": "itemize", "terms": "description"}
    for f in glob.glob(os.path.join(tree, "**", "*.tex"), recursive=True):
        s = open(f).read()
        s = unwrap_scalebox(s)
        # pandoc prints thebibliography's widest-label argument as stray text
        s = s.replace(r"\begin{thebibliography}{99}", r"\begin{thebibliography}{}")
        for a, b in ENVS.items():
            s = s.replace(r"\begin{%s}" % a, r"\begin{%s}" % b)
            s = s.replace(r"\end{%s}" % a, r"\end{%s}" % b)
        s = re.sub(r"\$([^$]*)\$",
                   lambda m: "$" + m.group(1).replace(r"\textsc{", r"\mathrm{") + "$", s)
        open(f, "w").write(s)

    # pandoc drops \cite and the [n] labels on \bibitem, so resolve them here
    refs = os.path.join(tree, "back", "references.tex")
    keys = re.findall(r"\\bibitem\{([^}]*)\}", open(refs).read())
    num = {k: i + 1 for i, k in enumerate(keys)}
    for f in glob.glob(os.path.join(tree, "**", "*.tex"), recursive=True):
        s = open(f).read()
        s = re.sub(r"\\cite\{([^}]*)\}",
                   lambda m: "[" + ", ".join(str(num.get(k.strip(), "?"))
                                             for k in m.group(1).split(",")) + "]", s)
        s = re.sub(r"\\bibitem\{([^}]*)\}\s*\n",
                   lambda m: "[%s] " % num.get(m.group(1), "?"), s)
        open(f, "w").write(s)
    # with the numbers inlined the list environment is no longer needed; a
    # plain sequence of paragraphs survives the conversion intact
    bib = open(refs).read()
    bib = re.sub(r"\\begin\{thebibliography\}\{[^}]*\}", "", bib)
    bib = bib.replace(r"\end{thebibliography}", "")
    bib = bib.replace(r"\setlength{\itemsep}{5pt}", "")
    # the typeset report titles this page through \bibname, which pandoc does
    # not see; give it the same heading macro the appendix and glossary use
    if r"\frontheading{References}" not in bib:
        bib = bib.replace(r"\addcontentsline{toc}{chapter}{References}",
                          r"\addcontentsline{toc}{chapter}{References}" "\n"
                          r"\frontheading{References}")
    open(refs, "w").write(bib)

    # pandoc reads \newcommand definitions, but not \makebox/\hangindent inside
    # them, so give the three layout macros plain-text equivalents
    with open(os.path.join(tree, "preamble.tex"), "a") as fh:
        fh.write("\n%% simplified for the Word export\n"
                 r"\renewcommand{\paper}[4]{\par\noindent\textbf{[#1] #2}, #3, #4\par}" "\n"
                 r"\renewcommand{\decision}[1]{\par\noindent\textbf{#1}\par}" "\n"
                 r"\renewcommand{\algtitle}[1]{\par\noindent\textbf{#1}\par}" "\n")
    return tree, figs


def render_figures(tree, figs):
    """One figure per page at the report's text width, then crop to the ink."""
    helper = [r"\documentclass[12pt,a4paper]{report}",
              r"\input{preamble}",
              r"\geometry{paperwidth=340mm, paperheight=340mm, margin=10mm}",
              r"\pagestyle{empty}", r"\begin{document}", r"\usemainmatterstyle"]
    for t in figs:
        helper.append(r"\thispagestyle{empty}\noindent\begin{minipage}{%s}%%" % TEXTWIDTH
                      + "\n" + t + "%\n" + r"\end{minipage}\clearpage")
    helper.append(r"\end{document}")
    hp = os.path.join(SRC, "_figs.tex")
    open(hp, "w").write("\n".join(helper))
    subprocess.run([TEX, "-X", "compile", "_figs.tex"], cwd=SRC,
                   check=True, capture_output=True)
    png_dir = os.path.join(WORK, "pages")
    os.makedirs(png_dir, exist_ok=True)
    subprocess.run(["pdftoppm", "-png", "-r", str(DPI),
                    os.path.join(SRC, "_figs.pdf"), os.path.join(png_dir, "p")], check=True)

    from PIL import Image
    for i, f in enumerate(sorted(glob.glob(os.path.join(png_dir, "p-*.png"))), 1):
        im = Image.open(f).convert("RGB")
        box = im.convert("L").point(lambda v: 0 if v > 245 else 255).getbbox()
        if box:
            pad = 14
            im = im.crop((max(0, box[0] - pad), max(0, box[1] - pad),
                          min(im.width, box[2] + pad), min(im.height, box[3] + pad)))
        im.save(os.path.join(tree, "figures", "auto%02d.png" % i), optimize=True)
    for junk in glob.glob(os.path.join(SRC, "_figs.*")):
        os.remove(junk)


# ------------------------------------------------------------- reference ----
def reference_doc():
    """pandoc's default reference docx, restyled to Times New Roman 12 pt."""
    ref = os.path.join(WORK, "reference.docx")
    base = subprocess.run([PANDOC, "--print-default-data-file", "reference.docx"],
                          check=True, capture_output=True).stdout
    tmp = ref + ".orig"
    open(tmp, "wb").write(base)
    TIMES = ('<w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" '
             'w:hAnsi="Times New Roman" w:cs="Times New Roman"/>')
    zin, zout = zipfile.ZipFile(tmp), zipfile.ZipFile(ref, "w", zipfile.ZIP_DEFLATED)
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "word/styles.xml":
            s = data.decode("utf-8")
            s = re.sub(r'<w:rFonts [^/]*?/>', TIMES, s)
            s = re.sub(r"(<w:docDefaults>.*?<w:rPr>)",
                       r"\1" + TIMES + '<w:sz w:val="24"/><w:szCs w:val="24"/>',
                       s, flags=re.S)
            # black headings and a justified body, as in the typeset report
            s = re.sub(r"<w:color [^>]*/>", '<w:color w:val="000000"/>', s)
            s = re.sub(r'(<w:style [^>]*w:styleId="(?:BodyText|FirstParagraph|Compact)"[^>]*>.*?<w:pPr>)',
                       r'\1<w:jc w:val="both"/>', s, flags=re.S)
            data = s.encode("utf-8")
        zout.writestr(item, data)
    zin.close(); zout.close(); os.remove(tmp)
    return ref


# ------------------------------------------------------------- post-edit ----
def patch(path):
    """Centre the front matter and put the contents before Chapter 1."""
    zin = zipfile.ZipFile(path)
    doc = zin.read("word/document.xml").decode("utf-8")
    b = doc.index("<w:body>") + len("<w:body>")
    e = doc.rindex("</w:body>")
    head, body, tail = doc[:b], doc[b:e], doc[e:]

    paras = re.findall(r"<w:p\b[^>]*/>|<w:p\b.*?</w:p>|<w:tbl\b.*?</w:tbl>|<w:sectPr\b.*?</w:sectPr>",
                       body, re.S)
    txt = lambda p: "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))

    def centre(p):
        if p.startswith("<w:tbl"):
            if "<w:jc " in p.split("</w:tblPr>")[0]:
                return p
            return p.replace("<w:tblPr>", '<w:tblPr><w:jc w:val="center"/>', 1)
        if "<w:jc " in p:
            return re.sub(r'<w:jc w:val="[^"]*"/>', '<w:jc w:val="center"/>', p)
        if "<w:pPr>" in p:
            return p.replace("<w:pPr>", '<w:pPr><w:jc w:val="center"/>', 1)
        return re.sub(r"(<w:p\b[^>]*>)", r'\1<w:pPr><w:jc w:val="center"/></w:pPr>', p, count=1)

    brk = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'

    def break_before(p):
        """Start this paragraph on a fresh page without adding an empty one."""
        if "<w:pageBreakBefore/>" in p:
            return p
        if "<w:pPr>" in p:
            return p.replace("<w:pPr>", "<w:pPr><w:pageBreakBefore/>", 1)
        return re.sub(r"(<w:p\b[^>]*>)", r"\1<w:pPr><w:pageBreakBefore/></w:pPr>", p, count=1)

    toc_a = next((i for i, p in enumerate(paras) if "Table of Contents" in txt(p)), None)
    toc_b = next((i for i, p in enumerate(paras)
                  if toc_a is not None and i > toc_a and 'w:fldCharType="end"' in p), None)
    toc = []
    if toc_a is not None and toc_b is not None:
        toc = paras[toc_a:toc_b + 1]
        del paras[toc_a:toc_b + 1]

    MARKS = {"CERTIFICATE", "DECLARATION", "ACKNOWLEDGEMENT", "ABSTRACT",
             "REFERENCES", "APPENDIX", "GLOSSARY"}
    cert = next((i for i, p in enumerate(paras) if txt(p).strip().upper() == "CERTIFICATE"), 0)

    # a section's page break belongs before its header block, not before its
    # title: the certificate's crest and institute line precede the word
    # CERTIFICATE and must stay on the same page as it
    breaks = set()
    for i, p in enumerate(paras):
        if txt(p).strip().upper() not in MARKS or i == 0:
            continue
        j = i
        while j > 0 and not txt(paras[j - 1]).strip() and "<a:blip" not in paras[j - 1]:
            j -= 1
        if j > 0 and "<a:blip" in paras[j - 1]:
            j -= 1
        breaks.add(j)

    out = []
    for i, p in enumerate(paras):
        t = txt(p).strip()
        if i <= cert or t.upper() in MARKS:
            p = centre(p) if (t or "<a:blip" in p or p.startswith("<w:tbl")) else p
        if i in breaks:
            p = break_before(p) if not p.startswith("<w:tbl") else brk + p
        out.append(p)

    if toc:
        h1 = next((i for i, p in enumerate(out) if 'w:val="Heading1"' in p), len(out))
        out[h1:h1] = [brk] + toc

    zout = zipfile.ZipFile(path + ".tmp", "w", zipfile.ZIP_DEFLATED)
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "word/document.xml":
            data = (head + "".join(out) + tail).encode("utf-8")
        zout.writestr(item, data)
    zin.close(); zout.close()
    shutil.move(path + ".tmp", path)


def main():
    tree, figs = stage_sources()
    print("figures to render: %d" % len(figs))
    render_figures(tree, figs)
    ref = reference_doc()
    subprocess.run([PANDOC, "main.tex", "-f", "latex", "-t", "docx",
                    "--reference-doc", ref, "--resource-path", ".:figures",
                    "--toc", "--toc-depth=2", "-o", OUT],
                   cwd=tree, check=True, capture_output=True)
    patch(OUT)
    shutil.rmtree(WORK)
    print("wrote %s (%.1f MB)" % (OUT, os.path.getsize(OUT) / 1e6))


if __name__ == "__main__":
    main()
