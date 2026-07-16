"""M4 training tests — tiny synthetic model, no real data or downloads.

Verifies the mechanics that are easy to get subtly wrong: the DPO reference
model is frozen and distinct from the policy, and the DPO loss actually pushes
the policy toward preferred completions.
"""

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from setu.training.dpo import DPOTrainer, dpo_loss, freeze_reference
from setu.training.student import build_student, param_count
from setu.types import ModelConfig

TINY = ModelConfig(
    language_pair="hin_Deva-eng_Latn",
    params=dict(hidden_size=32, encoder_layers=1, decoder_layers=1,
                attention_heads=2, ffn_size=64, max_seq_len=32, vocab_size=64),
    quantization={},
)


def _tiny_model():
    torch.manual_seed(0)
    return build_student(vocab_size=64, model_config=TINY)


def _pref_batch():
    # ids avoid PAD=0; preferred and dispreferred differ
    return {
        "input_ids": torch.tensor([[10, 11, 12, 13, 3]]),
        "attention_mask": torch.ones(1, 5, dtype=torch.long),
        "preferred_labels": torch.tensor([[2, 20, 21, 22, 3]]),
        "dispreferred_labels": torch.tensor([[2, 40, 41, 42, 3]]),
    }


def test_student_param_count_reasonable():
    model = _tiny_model()
    assert 0 < param_count(model) < 1_000_000


def test_reference_is_frozen_and_separate():
    model = _tiny_model()
    ref = freeze_reference(model)
    assert all(not p.requires_grad for p in ref.parameters())
    assert ref is not model
    # mutating the policy must not change the reference snapshot
    with torch.no_grad():
        next(model.parameters()).add_(1.0)
    pol_p = next(model.parameters())
    ref_p = next(ref.parameters())
    assert not torch.allclose(pol_p, ref_p)


def test_dpo_loss_is_finite_and_reports_accuracy():
    model = _tiny_model()
    model.eval()  # disable dropout so policy==reference identity is exact
    ref = freeze_reference(model)
    loss, metrics = dpo_loss(model, ref, _pref_batch(), beta=0.1)
    assert torch.isfinite(loss)
    assert 0.0 <= metrics["margin_accuracy"] <= 1.0
    # at init, policy == reference, so the DPO logit is 0 and loss = -log(0.5)
    assert loss.item() == pytest.approx(0.6931, abs=1e-3)


def test_sequences_truncated_to_max_len():
    # long inputs must never exceed the student's positional limit (regression:
    # position-embedding index overflow crashed SFT on very long sentences)
    from setu.training.dataset import _truncate
    from setu.training.tokenizer import EOS

    out = _truncate(list(range(500)), 128)
    assert len(out) == 128 and out[-1] == EOS
    assert _truncate([1, 2, 3], 128) == [1, 2, 3]  # short unchanged


def test_dpo_training_reduces_loss():
    model = _tiny_model()
    trainer = DPOTrainer(model, {"beta": 0.1, "lr": 1e-3, "epochs": 1, "batch_size": 1})

    class OneBatch:
        def batches(self, bs):
            for _ in range(30):
                yield _pref_batch()

    history = trainer.train(OneBatch())
    assert history[-1]["loss"] < history[0]["loss"]  # DPO objective decreases
    # reference stayed frozen throughout
    assert all(not p.requires_grad for p in trainer.reference.parameters())
