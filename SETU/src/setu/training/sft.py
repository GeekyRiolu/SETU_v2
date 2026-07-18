"""SFT / distillation trainer for the student baseline.

Trains the student on corpus (or teacher-distilled) targets with plain
cross-entropy. The resulting checkpoint is the baseline DPO must beat, and its
frozen snapshot becomes the DPO reference model.
"""

from __future__ import annotations

from typing import Any

from setu.training.device import batch_to, model_device, resolve_device


class SFTTrainer:
    def __init__(self, model, sft_config: dict[str, Any]):
        import torch

        self.config = sft_config
        self.device = resolve_device(sft_config.get("device", "auto"))
        self.model = model.to(self.device)
        self.label_smoothing = sft_config.get("label_smoothing", 0.0)
        self.max_grad_norm = sft_config.get("max_grad_norm", 1.0)
        self.optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=sft_config.get("lr", 5e-4),
            weight_decay=sft_config.get("weight_decay", 0.01),
        )

    def train(self, dataset, epochs: int | None = None, batch_size: int | None = None):
        import torch
        from transformers import get_linear_schedule_with_warmup

        epochs = epochs or self.config.get("epochs", 3)
        batch_size = batch_size or self.config.get("batch_size", 32)

        # linear warmup + decay — a from-scratch transformer is unstable under a
        # constant LR (the old code silently ignored warmup_steps). Cap warmup at
        # 10% of the run so short runs still get a real decay phase.
        n_batches = max(1, (len(dataset.entries) + batch_size - 1) // batch_size)
        total_steps = n_batches * epochs
        warmup = min(self.config.get("warmup_steps", 0), max(1, total_steps // 10))
        scheduler = get_linear_schedule_with_warmup(self.optimizer, warmup, total_steps)

        history = []
        self.model.train()
        device = model_device(self.model)
        for epoch in range(epochs):
            for step, batch in enumerate(dataset.batches(batch_size)):
                batch = batch_to(batch, device)
                out = self.model(
                    input_ids=batch["input_ids"],
                    attention_mask=batch["attention_mask"],
                    labels=batch["labels"],
                )
                if self.label_smoothing > 0:
                    import torch.nn.functional as F

                    logits = out.logits
                    loss = F.cross_entropy(
                        logits.reshape(-1, logits.size(-1)),
                        batch["labels"].reshape(-1),
                        ignore_index=-100,
                        label_smoothing=self.label_smoothing,
                    )
                else:
                    loss = out.loss
                self.optimizer.zero_grad()
                loss.backward()
                # gradient clipping — the key stabiliser for a from-scratch
                # transformer. Without it, a gradient spike collapses the model to
                # a degenerate output ("What is the …") — seen at 200k train.
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                self.optimizer.step()
                scheduler.step()
                history.append({"epoch": epoch, "step": step, "loss": loss.item()})
        return history
