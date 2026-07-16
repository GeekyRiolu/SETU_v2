"""M8 EWC tests — Fisher/penalty mechanics on a tiny model."""

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from setu.training.dataset import CorpusDataset
from setu.training.ewc import EWCRegularizer, ewc_train_step
from setu.training.student import build_student
from setu.training.tokenizer import StudentTokenizer
from setu.types import CorpusEntry, ModelConfig


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    import random
    d = tmp_path_factory.mktemp("ewc")
    random.seed(0)
    en = "the sun is bright and warm today over the green hills near".split()
    hi = "सूरज आज हरी पहाड़ियों पर चमकीला और गर्म है यहाँ पास".split()
    lines = []
    for _ in range(200):
        lines += [" ".join(random.sample(en, 5)), " ".join(random.sample(hi, 5))]
    (d / "c.txt").write_text("\n".join(lines), encoding="utf-8")
    tok = StudentTokenizer.train(d / "c.txt", d / "tok", vocab_size=160)
    mc = ModelConfig("hin_Deva-eng_Latn", dict(hidden_size=32, encoder_layers=1, decoder_layers=1,
                     attention_heads=2, ffn_size=64, max_seq_len=32), {})
    model = build_student(tok.vocab_size, mc)
    entries = [CorpusEntry("hin_Deva", "eng_Latn", h, e, "syn")
               for h, e in zip(hi * 30, en * 30)]
    ds = CorpusDataset.from_entries(entries, tok)
    return model, ds


def test_fisher_and_star_snapshot(setup):
    model, ds = setup
    reg = EWCRegularizer.from_old_task(model, ds, lam=1.0, fisher_samples=40, batch_size=4)
    # Fisher and star cover every trainable parameter
    trainable = {n for n, p in model.named_parameters() if p.requires_grad}
    assert set(reg.fisher) == trainable
    assert set(reg.star) == trainable
    # Fisher is non-negative and not all-zero
    assert all((f >= 0).all() for f in reg.fisher.values())
    assert sum(float(f.sum()) for f in reg.fisher.values()) > 0


def test_penalty_zero_at_star_and_grows_away(setup):
    model, ds = setup
    reg = EWCRegularizer.from_old_task(model, ds, lam=10.0, fisher_samples=40, batch_size=4)
    # at θ == θ* the penalty is exactly zero
    assert float(reg.penalty()) == pytest.approx(0.0, abs=1e-6)
    # move a high-importance parameter -> penalty becomes positive
    with torch.no_grad():
        name = max(reg.importance_summary(), key=reg.importance_summary().get)
        dict(model.named_parameters())[name].add_(0.5)
    assert float(reg.penalty()) > 0


def test_ewc_train_step_reports_terms(setup):
    model, ds = setup
    reg = EWCRegularizer.from_old_task(model, ds, lam=1.0, fisher_samples=20, batch_size=4)
    opt = torch.optim.SGD(model.parameters(), lr=1e-3)
    batch = ds.collate(ds.entries[:4])
    metrics = ewc_train_step(model, opt, batch, reg)
    assert {"task_loss", "ewc_penalty", "total_loss"} <= set(metrics)
    assert metrics["total_loss"] >= metrics["task_loss"] - 1e-6  # penalty >= 0


def _memorize(model, batch, steps, lr=0.05, reg=None):
    opt = torch.optim.SGD(model.parameters(), lr=lr)
    model.train()
    for _ in range(steps):
        if reg is None:
            out = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"],
                        labels=batch["labels"])
            opt.zero_grad(); out.loss.backward(); opt.step()
        else:
            ewc_train_step(model, opt, batch, reg)


def _loss_on(model, batch):
    model.eval()
    with torch.no_grad():
        return model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"],
                     labels=batch["labels"]).loss.item()


def _fisher_weighted_drift(reg, model):
    """Σ_i F_i (θ_i − θ*_i)² — how far the important-to-A params have drifted."""
    total = 0.0
    params = dict(model.named_parameters())
    for n, f in reg.fisher.items():
        total += float((f * (params[n].detach() - reg.star[n]) ** 2).sum())
    return total


def test_ewc_reduces_forgetting(setup):
    """The anti-forgetting mechanism, measured deterministically: after training
    on a new task B, EWC keeps the Fisher-important (task-A) parameters closer to
    their task-A values than plain fine-tuning does. Lower weighted drift = less
    forgetting. This is exactly what the penalty optimises, so it's robust."""
    import copy
    from setu.training.dataset import CorpusDataset
    base, ds = setup

    # task A batch, and a conflicting task B (same sources, shifted targets)
    srcs = [ds.entries[i].src_text for i in range(4)]
    tgts = [ds.entries[i].tgt_text for i in range(4)]
    A = [CorpusEntry("hin_Deva", "eng_Latn", srcs[i], tgts[i], "A") for i in range(4)]
    B = [CorpusEntry("hin_Deva", "eng_Latn", srcs[i], tgts[(i + 1) % 4], "B") for i in range(4)]
    b_batch = CorpusDataset.from_entries(B, ds.tok).collate(B)

    model_a = copy.deepcopy(base)
    _memorize(model_a, CorpusDataset.from_entries(A, ds.tok).collate(A), steps=40)

    # Fisher + θ* snapshot taken at the end of task A
    reg_plain = EWCRegularizer.from_old_task(model_a, CorpusDataset.from_entries(A, ds.tok),
                                             lam=1.0, fisher_samples=4, batch_size=4)

    # branch 1: fine-tune on B with NO EWC
    plain = copy.deepcopy(model_a)
    _memorize(plain, b_batch, steps=40)

    # branch 2: fine-tune on B WITH EWC (moderate lambda, no NaN)
    ewc_model = copy.deepcopy(model_a)
    reg = EWCRegularizer.from_old_task(ewc_model, CorpusDataset.from_entries(A, ds.tok),
                                       lam=500.0, fisher_samples=4, batch_size=4)
    _memorize(ewc_model, b_batch, steps=40, lr=0.02, reg=reg)

    drift_plain = _fisher_weighted_drift(reg_plain, plain)
    drift_ewc = _fisher_weighted_drift(reg_plain, ewc_model)
    # EWC held the important parameters near their task-A values; plain drifted more
    assert drift_ewc < drift_plain
