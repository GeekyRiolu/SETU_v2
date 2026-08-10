"""CLI front-end. Thin argparse wrapper over the shared InferenceEngine —
no translation logic lives here.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys

from setu.inference.router import translate as route_translate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="setu",
        description="SETU — offline translation across the 22 scheduled Indian languages.",
    )
    parser.add_argument("--src", required=True, help="source language (ISO or FLORES code, e.g. hi)")
    parser.add_argument("--tgt", required=True, help="target language (ISO or FLORES code, e.g. en)")
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--text", help="text to translate")
    src.add_argument("--file", help="translate each line of this file ('-' for stdin)")
    parser.add_argument("--json", action="store_true", help="print the full TranslationResult as JSON")
    return parser


def _read_inputs(args) -> list[str]:
    if args.text is not None:
        return [args.text]
    if args.file:
        stream = sys.stdin if args.file == "-" else open(args.file, encoding="utf-8")
        with stream as f:
            return [line.rstrip("\n") for line in f if line.strip()]
    # no --text/--file: read stdin (piped input)
    return [line.rstrip("\n") for line in sys.stdin if line.strip()]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    inputs = _read_inputs(args)
    if not inputs:
        print("error: no input text (pass --text, --file, or pipe stdin)", file=sys.stderr)
        return 2

    # route each line to its pair's model (or English pivot for Indic<->Indic)
    try:
        routed = [route_translate(t, args.src, args.tgt) for t in inputs]
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if any(stub for _, _, stub in routed):
        print("[setu] no trained model for this pair — output is a passthrough", file=sys.stderr)
    elif any(pivot for _, pivot, _ in routed):
        print("[setu] no direct model — translated via English pivot", file=sys.stderr)

    if args.json:
        payload = []
        for res, pivot, stub in routed:
            d = dataclasses.asdict(res)
            d["pivot"], d["stub"] = pivot, stub
            payload.append(d)
        print(json.dumps(payload if len(payload) > 1 else payload[0], ensure_ascii=False, indent=2))
    else:
        for res, _, _ in routed:
            print(res.translated_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
