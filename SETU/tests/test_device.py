"""Device-resolution tests — the CPU/GPU-agnostic training helper."""

import pytest

torch = pytest.importorskip("torch")

from setu.training.device import batch_to, model_device, resolve_device


def test_resolve_device_falls_back_to_cpu_when_no_cuda():
    # this box has no CUDA; auto and explicit cuda both resolve to cpu
    assert resolve_device("cpu") == "cpu"
    if not torch.cuda.is_available():
        assert resolve_device("auto") == "cpu"
        assert resolve_device("cuda") == "cpu"


def test_batch_to_moves_all_tensors():
    batch = {"input_ids": torch.ones(2, 3, dtype=torch.long),
             "attention_mask": torch.ones(2, 3, dtype=torch.long)}
    moved = batch_to(batch, "cpu")
    assert all(str(v.device) == "cpu" for v in moved.values())


def test_model_device_reads_param_device():
    lin = torch.nn.Linear(2, 2)
    assert str(model_device(lin)) == "cpu"
