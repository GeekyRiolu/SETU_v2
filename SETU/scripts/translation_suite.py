#!/usr/bin/env python3
"""Smoke-test every trained model under models/<pair>/.

For each deployed pair it loads the quantised ONNX student and translates one
sample sentence in the pair's own direction, then reports latency and whether the
output looks healthy (non-empty, not a passthrough, not a collapse signature).

    cd SETU && PYTHONPATH=src:. .venv/bin/python scripts/translation_suite.py

Runs one model at a time and frees it before the next, to stay within RAM.
"""

from __future__ import annotations

import gc
import sys
import time
from pathlib import Path

from setu.config import resolve_language
from setu.inference.engine import InferenceEngine, models_root
from setu.types import ModelConfig

# One source-language sample per language (the sentence is in the SOURCE lang).
SAMPLES = {
    "en": "India is a big country.",
    "hi": "भारत एक विशाल देश है।",
    "bn": "আমি বই পড়তে ভালোবাসি।",
    "mr": "भारत हा एक मोठा देश आहे.",
    "te": "భారతదేశం ఒక పెద్ద దేశం.",
    "ta": "இந்தியா ஒரு பெரிய நாடு.",
    "gu": "ભારત એક મોટો દેશ છે.",
    "kn": "ಭಾರತ ಒಂದು ದೊಡ್ಡ ದೇಶ.",
    "or": "ଭାରତ ଏକ ବଡ଼ ଦେଶ।",
    "ml": "ഇന്ത്യ ഒരു വലിയ രാജ്യമാണ്.",
}

# phrases the collapsed students fell back to regardless of input
COLLAPSE_MARKERS = ("police have registered a case", "the first one.")


def discover_pairs() -> list[str]:
    root = models_root()
    pairs = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        if (d / "tokenizer" / "student_sp.model").exists() and any(d.glob("*/*.onnx")):
            pairs.append(d.name)
    return pairs


def health(text_in: str, text_out: str, stub: bool) -> tuple[bool, str]:
    out = (text_out or "").strip()
    low = out.lower()
    if stub:
        return False, "STUB (no model loaded)"
    if not out:
        return False, "empty output"
    if out == text_in.strip():
        return False, "output == input (passthrough)"
    if any(m in low for m in COLLAPSE_MARKERS):
        return False, "collapse signature"
    words = low.split()
    if len(words) >= 4 and len(set(words)) <= 2:
        return False, "degenerate repetition"
    return True, "ok"


def main() -> int:
    pairs = discover_pairs()
    if not pairs:
        print("No models found under", models_root().resolve())
        return 1

    print(f"Translation suite over {len(pairs)} models\n" + "=" * 72)
    results = []
    for pair in pairs:
        src_f, tgt_f = pair.split("-")
        src, tgt = resolve_language(src_f), resolve_language(tgt_f)
        text = SAMPLES.get(src["iso"], "India is a big country.")
        label = f"{src['name']} -> {tgt['name']}"
        try:
            engine = InferenceEngine(ModelConfig(language_pair=pair))
            t0 = time.perf_counter()
            res = engine.translate(text, src["iso"], tgt["iso"])
            ms = (time.perf_counter() - t0) * 1000
            ok, why = health(text, res.translated_text, engine.is_stub)
            results.append((pair, ok))
            mark = "PASS" if ok else "FAIL"
            print(f"[{mark}] {label:26} {ms:6.0f} ms  ({why})")
            print(f"        in : {text}")
            print(f"        out: {res.translated_text!r}")
            del engine
            gc.collect()
        except Exception as exc:  # noqa: BLE001 - report and continue
            results.append((pair, False))
            print(f"[ERR ] {label:26}  {type(exc).__name__}: {exc}")
        print("-" * 72)

    ok_n = sum(1 for _, ok in results if ok)
    print(f"\nSummary: {ok_n}/{len(results)} models produced healthy output.")
    if ok_n < len(results):
        print("Not healthy: " + ", ".join(p for p, ok in results if not ok))
    return 0 if ok_n == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
