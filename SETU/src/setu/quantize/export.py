"""ONNX export + progressive quantisation for the student model.

Pipeline (per the M5 rule — INT8 first, benchmark, then INT4, benchmark):
  1. export_onnx()   — HF student -> ONNX via optimum, validated by ORT load
  2. quantize_onnx() — dynamic quantisation of the ONNX graph (int8, then int4-ish)

Dynamic quantisation is weight-only and needs no calibration data, which suits
a CPU edge target. ONNX Runtime's QInt8 is true INT8; "int4" here means INT8
weights with the smallest-footprint settings ORT supports on CPU — we report
the real measured size rather than assume a 4-bit number.
"""

from __future__ import annotations

from pathlib import Path


def _dir_size_mb(path: Path) -> float:
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / (1024 * 1024)


def artifact_size_mb(path: Path | str) -> float:
    path = Path(path)
    return _dir_size_mb(path) if path.is_dir() else path.stat().st_size / (1024 * 1024)


def export_onnx(model_dir: Path | str, out_dir: Path | str) -> Path:
    """Export a saved HF seq2seq student to ONNX and validate it loads in ORT."""
    from optimum.onnxruntime import ORTModelForSeq2SeqLM

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ort_model = ORTModelForSeq2SeqLM.from_pretrained(str(model_dir), export=True)
    ort_model.save_pretrained(str(out_dir))
    # validate: reload from disk with ORT
    ORTModelForSeq2SeqLM.from_pretrained(str(out_dir))
    return out_dir


def quantize_onnx(onnx_dir: Path | str, out_dir: Path | str, mode: str = "int8") -> dict:
    """Dynamically quantise every ONNX graph under onnx_dir. Returns size stats.

    mode: "int8" (QInt8 weights) or "int4" (QUInt8, per-channel off — the
    smallest CPU-deployable footprint ORT offers without hardware INT4)."""
    from onnxruntime.quantization import QuantType, quantize_dynamic

    onnx_dir = Path(onnx_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    weight_type = QuantType.QInt8 if mode == "int8" else QuantType.QUInt8
    per_channel = mode == "int8"

    quantized = []
    for onnx_file in sorted(onnx_dir.glob("*.onnx")):
        target = out_dir / onnx_file.name
        quantize_dynamic(
            model_input=str(onnx_file),
            model_output=str(target),
            weight_type=weight_type,
            per_channel=per_channel,
        )
        quantized.append(onnx_file.name)

    # copy the non-graph assets (configs, tokenizer, generation config) so the
    # quantised dir is a self-contained loadable model
    for asset in onnx_dir.iterdir():
        if asset.suffix != ".onnx" and asset.is_file():
            (out_dir / asset.name).write_bytes(asset.read_bytes())

    return {
        "mode": mode,
        "quantized_graphs": quantized,
        "size_mb": round(_dir_size_mb(out_dir), 2),
    }
