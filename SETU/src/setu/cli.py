"""CLI front-end. Thin argparse wrapper over the shared InferenceEngine —
no translation logic lives here.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys

from setu.inference.engine import STUB_ENGINE, InferenceEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="setu",
        description="SETU — offline translation across the 22 scheduled Indian languages.",
    )
    parser.add_argument("--src", required=True, help="source language (ISO or FLORES code, e.g. hi)")
    parser.add_argument("--tgt", required=True, help="target language (ISO or FLORES code, e.g. en)")
    parser.add_argument("--text", required=True, help="text to translate")
    parser.add_argument("--json", action="store_true", help="print the full TranslationResult as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = InferenceEngine().translate(args.text, args.src, args.tgt)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if STUB_ENGINE:
        print("[setu] stub engine (M0): output is a passthrough, not a translation", file=sys.stderr)

    if args.json:
        print(json.dumps(dataclasses.asdict(result), ensure_ascii=False, indent=2))
    else:
        print(result.translated_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
