"""M5 export + quantise + offline-inference tests on a tiny trained student.

Reuses the tiny_project fixture to train a real (small) model, then exercises
ONNX export, INT8/INT4 quantisation, size measurement, the ONNX InferenceEngine
backend, and the networking-disabled offline guarantee.
"""

import pytest

pytest.importorskip("torch")
pytest.importorskip("onnx")
pytest.importorskip("onnxruntime")
pytest.importorskip("optimum")

from tests.test_train_pipeline import tiny_project  # noqa: F401  (fixture reuse)

from setu.quantize.export import artifact_size_mb, export_onnx, quantize_onnx


@pytest.fixture
def trained_student(tiny_project):  # noqa: F811
    from setu.training.pipeline import run

    run(pair="hin_Deva-eng_Latn", limit=60,
        ckpt_root=tiny_project / "checkpoints", data_root=tiny_project / "data",
        dev_size=6)
    return tiny_project


def test_export_and_progressive_quantize(trained_student):
    ck = trained_student / "checkpoints" / "hin_Deva-eng_Latn"
    onnx_dir = export_onnx(ck / "sft", trained_student / "onnx")
    assert any(onnx_dir.glob("*.onnx"))
    fp32 = artifact_size_mb(onnx_dir)

    int8 = quantize_onnx(onnx_dir, trained_student / "int8", mode="int8")
    int4 = quantize_onnx(onnx_dir, trained_student / "int4", mode="int4")
    assert int8["quantized_graphs"], "expected encoder/decoder graphs quantised"
    # quantisation shrinks the artifact
    assert int8["size_mb"] < fp32
    assert int4["size_mb"] <= int8["size_mb"] * 1.1  # int4 no larger (± rounding)


def test_onnx_engine_translates_offline(trained_student, monkeypatch):
    # deploy the int8 artifact where the engine looks
    from setu.quantize.export import export_onnx, quantize_onnx
    import shutil

    ck = trained_student / "checkpoints" / "hin_Deva-eng_Latn"
    onnx_dir = export_onnx(ck / "sft", trained_student / "onnx2")
    quantize_onnx(onnx_dir, trained_student / "models" / "hin_Deva-eng_Latn" / "int8", mode="int8")
    shutil.copytree(ck / "tokenizer", trained_student / "models" / "hin_Deva-eng_Latn" / "tokenizer")

    from setu.inference.engine import InferenceEngine, assert_offline

    assert_offline()  # any socket connect now raises
    engine = InferenceEngine(models_root=trained_student / "models")
    assert not engine.is_stub  # real ONNX backend picked up
    result = engine.translate("सूरज चमकीला है", "hi", "en")
    assert isinstance(result.translated_text, str)  # produced output with no network
    assert result.latency_ms is not None
