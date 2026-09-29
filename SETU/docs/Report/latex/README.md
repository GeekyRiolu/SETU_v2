# SETU — Project Phase-II Report (LaTeX source)

Built PDF: `../SETU_Project_Phase-II_Report.pdf` (130 pages, A4).

## Build

The document is XeLaTeX (it uses system Noto Serif Indic fonts for the
translation samples). Either engine works:

```bash
tectonic -X compile main.tex        # self-contained, downloads packages on demand
# or
xelatex main.tex && xelatex main.tex && xelatex main.tex   # 3 passes for TOC/refs
```

Requires the Noto Serif Indic fonts (Devanagari, Bengali, Gujarati, Gurmukhi,
Oriya, Tamil, Telugu, Kannada, Malayalam). On Arch: `noto-fonts`.

## Layout

```
main.tex          document skeleton and \input order
preamble.tex      all formatting rules from R.1.Guidelines.docx
front/            title page, certificate, declaration, abstract,
                  acknowledgement, contents / list of tables / list of figures
chapters/         ch1 .. ch9
back/             references, appendix, glossary
figures/          diagram PNGs (copied from SETU/vm/diagrams/)
```

## Formatting (per R.1.Guidelines.docx)

| Rule | Implementation |
|------|----------------|
| A4, 1.5 line spacing, Times New Roman | `geometry`, `setspace`, TeX Gyre Termes (metric Times clone) |
| Margins L 1.25in, R 1in, T/B 0.75in | `geometry` |
| Chapter no. left, 16pt; title CAPS centred 18pt bold | `titlesec` `\titleformat{\chapter}` |
| Section 16pt bold left; subsection 14pt bold left | `titlesec` |
| Body 12pt | `\documentclass[12pt]` |
| Header: title on the right, none on chapter-opening pages | `fancyhdr` `setumain` / `plain` styles |
| Footer: department left, 2025-2026 centre, page right | `fancyhdr` |
| Figures numbered chapter-wise, caption below | `report` class + `caption` |
| Tables numbered chapter-wise, caption above | `\captionsetup[table]{position=top}` |
| References numbered `[n]` in order of occurrence | `thebibliography` + `\cite` |
| No chapter number or header for References | `\renewcommand{\bibname}` |
| Front matter: no header/footer, Roman number centred at the foot | `frontmatter` page style + `\usefrontmatterstyle` / `\usemainmatterstyle` in `main.tex` |
| TOC stops at section level (no 1.3.1 entries) | `\setcounter{tocdepth}{1}` (`secnumdepth` stays 3, so they remain numbered in the text) |
| Wide diagrams on sideways pages | `pdflscape` + the `\widefigure` macro |
| Roman numbering starts at the Abstract (page i) | `\pagenumbering{roman}` + `\setcounter{page}{1}` in `front/abstract.tex`; pages before it use `frontblank` (no number at all) |
| Justified prose in tables | `J{w}` column type (`ragged2e`'s `\justifying`) for prose columns of 6 cm or more; `L{w}` stays ragged for narrower ones, `r`/`c` for numbers and short labels |

## Logos

`figures/bit_logo.jpg` is the Bangalore Institute of Technology crest, taken
from the department's own `R.1.Guidelines.docx` (274x318, the highest-resolution
copy in the project). It appears on the title page (30 mm) and the certificate
(26 mm). `figures/bit_logo_colour.jpg` is the green version from the SETU deck's
title slide, if that one is preferred: just change the filename in
`front/titlepage.tex` and `front/certificate.tex`.

No VTU emblem exists anywhere in the project. To add one, drop the file into
`figures/` and uncomment the prepared line in `front/titlepage.tex`.

## Placeholders to replace before printing

- `back/appendix.tex`: the reserved block for the paper publication certificate.
