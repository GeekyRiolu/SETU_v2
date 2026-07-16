"""EWC — Elastic Weight Consolidation for adding a language without forgetting.

When expanding to a new language, a Fisher-weighted quadratic penalty anchors
each parameter to its old value in proportion to how important it was to the
already-learned languages:

    L_total = L_new  +  (lambda/2) * Σ_i  F_i * (θ_i − θ*_i)²

F_i is the diagonal Fisher information estimated on old-language data; θ*_i is
the consolidated (old) parameter value. Parameters that mattered a lot to old
languages (high F_i) are held near θ*; the rest are free to adapt.

The failure mode — catastrophic forgetting — is invisible unless the old
languages are re-evaluated after expansion, so always pair this with a
before/after eval (see the M8 procedure).
"""

from __future__ import annotations

from typing import Any


class EWCRegularizer:
    def __init__(self, model, fisher: dict[str, "Any"], star_params: dict[str, "Any"], lam: float):
        self.model = model
        self.fisher = fisher
        self.star = star_params
        self.lam = lam

    @classmethod
    def from_old_task(cls, model, old_dataset, lam: float, fisher_samples: int = 200,
                      batch_size: int = 8) -> "EWCRegularizer":
        """Estimate diagonal Fisher on old-language data and snapshot θ*."""
        import torch

        fisher = {n: torch.zeros_like(p) for n, p in model.named_parameters() if p.requires_grad}
        star = {n: p.detach().clone() for n, p in model.named_parameters() if p.requires_grad}

        model.eval()
        seen = 0
        entries = old_dataset.entries[:fisher_samples]
        for i in range(0, len(entries), batch_size):
            batch = old_dataset.collate(entries[i:i + batch_size])
            model.zero_grad()
            out = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"],
                        labels=batch["labels"])
            out.loss.backward()
            for n, p in model.named_parameters():
                if p.grad is not None and n in fisher:
                    fisher[n] += p.grad.detach() ** 2 * len(batch["input_ids"])
            seen += len(batch["input_ids"])
        if seen:
            for n in fisher:
                fisher[n] /= seen
        model.zero_grad()
        return cls(model, fisher, star, lam)

    def penalty(self):
        """The EWC penalty term to ADD to the new-task loss."""
        import torch

        loss = None
        for n, p in self.model.named_parameters():
            if n in self.fisher:
                term = (self.fisher[n] * (p - self.star[n]) ** 2).sum()
                loss = term if loss is None else loss + term
        if loss is None:
            return torch.tensor(0.0)
        return (self.lam / 2.0) * loss

    def importance_summary(self) -> dict[str, float]:
        """Total Fisher importance per parameter tensor — useful for logging
        which parts of the network EWC is protecting most."""
        return {n: float(f.sum()) for n, f in self.fisher.items()}


def ewc_train_step(model, optimizer, batch, regularizer: EWCRegularizer) -> dict:
    """One new-language training step with the EWC penalty added to the loss."""
    out = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"],
                labels=batch["labels"])
    penalty = regularizer.penalty()
    total = out.loss + penalty
    optimizer.zero_grad()
    total.backward()
    optimizer.step()
    return {"task_loss": out.loss.item(), "ewc_penalty": float(penalty), "total_loss": total.item()}
