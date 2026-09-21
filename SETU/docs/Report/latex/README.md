# SETU — Project Phase-II Report (LaTeX source)

Built PDF: `../SETU_Project_Phase-II_Report.pdf` (129 pages, A4).

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

## Placeholders to replace before printing

- `front/titlepage.tex` and `front/certificate.tex`: the emblem boxes
  (`\begin{tikzpicture}...`) — swap in `\includegraphics` of the real logos.
- `front/certificate.tex`: `[Principal's name]`.
- `back/appendix.tex`: the reserved block for the paper publication certificate.
