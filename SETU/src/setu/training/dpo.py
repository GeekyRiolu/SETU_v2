"""DPO loss and trainer.

Standard DPO (Rafailov et al. 2023): no reward model, no policy gradient. The
reference model is a FROZEN copy of the SFT/distilled student — the single most
common DPO mistake is letting it train or pointing it at the wrong snapshot, so
this module freezes it explicitly and never exposes it as trainable.

    L = -E[ log σ( β·( (logπ_θ(y_w|x) - logπ_ref(y_w|x))
                     - (logπ_θ(y_l|x) - logπ_ref(y_l|x)) ) ) ]
"""

from __future__ import annotations

import copy
from typing import Any

from setu.training.device import batch_to, model_device, resolve_device


def _sequence_logprob(model, input_ids, attention_mask, labels):
    """Sum of log-probs of `labels` under the seq2seq model, PAD-masked."""
    import torch
    import torch.nn.functional as F

    out = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
    logits = out.logits  # (B, T, V)
    logprobs = F.log_softmax(logits, dim=-1)
    # gather the log-prob of each gold token
    gathered = logprobs.gather(-1, labels.unsqueeze(-1)).squeeze(-1)  # (B, T)
    mask = (labels != 0).float()  # PAD id = 0
    return (gathered * mask).sum(dim=-1)


def dpo_loss(policy_model, reference_model, batch, beta: float):
    import torch
    import torch.nn.functional as F

    inp, att = batch["input_ids"], batch["attention_mask"]
    pref, dispref = batch["preferred_labels"], batch["dispreferred_labels"]

    pol_pref = _sequence_logprob(policy_model, inp, att, pref)
    pol_dispref = _sequence_logprob(policy_model, inp, att, dispref)
    with torch.no_grad():
        ref_pref = _sequence_logprob(reference_model, inp, att, pref)
        ref_dispref = _sequence_logprob(reference_model, inp, att, dispref)

    pol_logratio = pol_pref - pol_dispref
    ref_logratio = ref_pref - ref_dispref
    logits = beta * (pol_logratio - ref_logratio)
    loss = -F.logsigmoid(logits).mean()
    accuracy = (logits > 0).float().mean().item()  # fraction preferring y_w
    return loss, {"loss": loss.item(), "margin_accuracy": accuracy}


def freeze_reference(model):
    """Return a frozen deep copy of `model` to serve as π_ref."""
    ref = copy.deepcopy(model)
    ref.eval()
    for p in ref.parameters():
        p.requires_grad_(False)
    return ref


class DPOTrainer:
    def __init__(self, policy_model, dpo_config: dict[str, Any]):
        import torch

        self.config = dpo_config
        self.device = resolve_device(dpo_config.get("device", "auto"))
        self.policy = policy_model.to(self.device)
        self.reference = freeze_reference(self.policy)  # frozen snapshot BEFORE training
        self.beta = dpo_config.get("beta", 0.1)
        self.optimizer = torch.optim.AdamW(
            self.policy.parameters(), lr=dpo_config.get("lr", 5e-6)
        )

    def train(self, dataset, epochs: int | None = None, batch_size: int | None = None):
        epochs = epochs or self.config.get("epochs", 1)
        batch_size = batch_size or self.config.get("batch_size", 8)
        history = []
        self.policy.train()
        device = model_device(self.policy)
        for epoch in range(epochs):
            for step, batch in enumerate(dataset.batches(batch_size)):
                batch = batch_to(batch, device)
                loss, metrics = dpo_loss(self.policy, self.reference, batch, self.beta)
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                metrics["epoch"] = epoch
                metrics["step"] = step
                history.append(metrics)
        return history
