# Project Phase-II final presentation

`build_final_ppt.py` turns the interim deck (`SETU_updated.pptx`) into the
Phase-II final presentation, following the department's
"9.1 Project Phase-II Final Presentation Template".

```
python3 build_final_ppt.py                         # ~/Downloads/SETU_updated.pptx -> ~/Downloads/SETU_Phase-II_Final_Presentation.pptx
python3 build_final_ppt.py BASE.pptx OUT.pptx      # explicit paths
```

What it does to the interim deck:

- Adds the sections the final template asks for: literature survey summary,
  problem statement input and output, component design, results and
  performance analysis, snapshots, applications, future scope and
  publications.
- Updates the text to the final report (all 22 languages, 44 models serving
  506 directions, the SeqKD vs DPO finding).
- Replaces every diagram with the report's version and gives each analysis
  diagram its own slide.
- Reorders the slides into the template's sequence.

`assets/` holds the report's figures (taken from the Word export of the report)
and two cropped screenshots of the web app. The CLI and REST API snapshot shows
real output captured from the INT4 models on 5 Nov 2026.

Needs `python-pptx` and `Pillow`.
