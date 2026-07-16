#!/usr/bin/env python3
"""Live interactive translator (real Tamil output, offline).

Uses the IndicTrans2 teacher via SETU's TeacherModel wrapper — the trained SETU
student only covers Hindi<->English and is undertrained, so for real
English->Tamil we drive the teacher directly.

    python translate_live.py                 # English -> Tamil REPL
    python translate_live.py --src hi --tgt en
    echo "How are you?" | python translate_live.py    # one-shot from stdin

Type a sentence, press Enter, see the translation. Ctrl-D / Ctrl-C to quit.
Runs fully offline after the model is cached (~2-3 s/sentence on CPU).
"""

import argparse
import os
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from setu.config import resolve_language  # noqa: E402
from setu.teacher import IndicTrans2Teacher  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Live IndicTrans2 translator")
    ap.add_argument("--src", default="en", help="source language (ISO, default en)")
    ap.add_argument("--tgt", default="ta", help="target language (ISO, default ta = Tamil)")
    args = ap.parse_args()

    src_name = resolve_language(args.src)["name"]
    tgt_name = resolve_language(args.tgt)["name"]

    print(f"Loading IndicTrans2 teacher ({src_name} -> {tgt_name})…", file=sys.stderr, flush=True)
    teacher = IndicTrans2Teacher()
    # warm up (first call loads the checkpoint)
    teacher.generate_candidates("Hello", args.src, args.tgt, n=1)
    print(f"Ready. Type {src_name} text and press Enter (Ctrl-D to quit).\n", file=sys.stderr, flush=True)

    interactive = sys.stdin.isatty()
    while True:
        if interactive:
            try:
                line = input(f"{src_name} > ")
            except (EOFError, KeyboardInterrupt):
                print(file=sys.stderr)
                break
        else:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.rstrip("\n")
        if not line.strip():
            continue
        t0 = time.time()
        out = teacher.generate_candidates(line, args.src, args.tgt, n=1)[0]
        dt = (time.time() - t0) * 1000
        print(f"{tgt_name}: {out}   ({dt:.0f} ms)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
