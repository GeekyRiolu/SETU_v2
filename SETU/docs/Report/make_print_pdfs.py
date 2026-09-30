#!/usr/bin/env python3
"""Split the report into a black-and-white set and a colour set for printing.

The two PDFs are disjoint and together cover every page, so they can be printed
on different machines and interleaved back into one bound copy. Page numbering
is untouched: pages keep the numbers printed on them.

A page goes into the COLOUR set when either
  * it carries a figure (the diagrams use colour to tell node types apart), or
  * it contains saturated colour, e.g. the green/amber Pass and Near verdicts
    or the syntax highlighting in a code listing.

Everything else goes to the BLACK AND WHITE set. That includes the pale blue
table headers and grey row shading, which carry no information and print as
light grey on a mono printer.

Usage:  python3 make_print_pdfs.py [--strong 0.02] [--dpi 50]
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "SETU_Project_Phase-II_Report.pdf")
BW_OUT = os.path.join(HERE, "SETU_Report_PRINT_bw.pdf")
COLOUR_OUT = os.path.join(HERE, "SETU_Report_PRINT_colour.pdf")
MANIFEST = os.path.join(HERE, "SETU_Report_PRINT_manifest.txt")

# A pixel counts as "saturated" above this chroma (max RGB minus min RGB).
# The pale table header #DCE6F1 has a chroma of 21 and stays below it; the
# green Pass #1B7A3D has 95 and clears it easily.
STRONG_CHROMA = 60


def page_count(pdf: str) -> int:
    out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
    return int(out.split("Pages:")[1].split()[0])


def figure_pages(pdf: str, n_pages: int) -> set[int]:
    """Pages whose text contains a figure caption."""
    pages = set()
    for p in range(1, n_pages + 1):
        txt = subprocess.run(
            ["pdftotext", "-f", str(p), "-l", str(p), pdf, "-"],
            capture_output=True, text=True).stdout
        if re.search(r"^Figure \d+\.\d+:", txt, re.M):
            pages.add(p)
    return pages


def saturated_pages(pdf: str, dpi: int, min_pct: float) -> dict[int, float]:
    """Pages carrying at least `min_pct` percent saturated-colour pixels."""
    tmp = tempfile.mkdtemp(prefix="setu-print-")
    try:
        subprocess.run(["pdftoppm", "-png", "-r", str(dpi), pdf,
                        os.path.join(tmp, "p")], check=True,
                       capture_output=True)
        found = {}
        for f in sorted(glob.glob(os.path.join(tmp, "p-*.png")),
                        key=lambda x: int(re.search(r"(\d+)", os.path.basename(x)).group(1))):
            n = int(re.search(r"p-(\d+)", os.path.basename(f)).group(1))
            a = np.asarray(Image.open(f).convert("RGB"), dtype=np.int16)
            chroma = a.max(axis=2) - a.min(axis=2)
            pct = (chroma > STRONG_CHROMA).sum() / chroma.size * 100
            if pct >= min_pct:
                found[n] = pct
        return found
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def as_ranges(pages: list[int]) -> str:
    """[1,2,3,7,9,10] -> '1-3,7,9-10' (qpdf page-range syntax)."""
    out, i = [], 0
    while i < len(pages):
        j = i
        while j + 1 < len(pages) and pages[j + 1] == pages[j] + 1:
            j += 1
        out.append(str(pages[i]) if i == j else f"{pages[i]}-{pages[j]}")
        i = j + 1
    return ",".join(out)


def extract(src: str, pages: list[int], dest: str) -> None:
    subprocess.run(["qpdf", src, "--pages", src, as_ranges(pages), "--", dest],
                   check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strong", type=float, default=0.02,
                    help="minimum %% of saturated pixels for a page to count as colour")
    ap.add_argument("--dpi", type=int, default=50, help="analysis render resolution")
    args = ap.parse_args()

    if not os.path.exists(SOURCE):
        print(f"missing {SOURCE}", file=sys.stderr)
        return 1

    total = page_count(SOURCE)
    figs = figure_pages(SOURCE, total)
    sat = saturated_pages(SOURCE, args.dpi, args.strong)

    colour = sorted(figs | set(sat))
    bw = [p for p in range(1, total + 1) if p not in set(colour)]

    extract(SOURCE, colour, COLOUR_OUT)
    extract(SOURCE, bw, BW_OUT)

    lines = [
        "SETU Project Phase-II Report: printing split",
        "=" * 60,
        f"Source                : {os.path.basename(SOURCE)}  ({total} pages)",
        f"Colour pages          : {len(colour)}",
        f"Black and white pages : {len(bw)}",
        "",
        "The two files are disjoint and together cover all "
        f"{total} pages, so they",
        "interleave back into one bound copy. The page numbers printed on the",
        "pages are unchanged.",
        "",
        f"COLOUR  -> {os.path.basename(COLOUR_OUT)}",
        f"   pages: {as_ranges(colour)}",
        "",
        f"MONO    -> {os.path.basename(BW_OUT)}",
        f"   pages: {as_ranges(bw)}",
        "",
        "Why each colour page is in the set",
        "-" * 60,
    ]
    for p in colour:
        why = []
        if p in figs:
            why.append("figure")
        if p in sat:
            why.append(f"saturated colour {sat[p]:.3f}%")
        lines.append(f"   p{p:<4} {'; '.join(why)}")
    lines.append("")
    lines.append("Regenerate after editing the report:")
    lines.append("   python3 make_print_pdfs.py            # default threshold")
    lines.append("   python3 make_print_pdfs.py --strong 0 # every tinted page to colour")
    text = "\n".join(lines) + "\n"
    open(MANIFEST, "w").write(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
