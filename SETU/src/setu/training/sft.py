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
        self.optimizer = torch.optim.AdamW(
            model.parameters(), lr=sft_config.get("lr", 5e-4)
        )

    def train(self, dataset, epochs: int | None = None, batch_size: int | None = None):
        epochs = epochs or self.config.get("epochs", 3)
        batch_size = batch_size or self.config.get("batch_size", 32)
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
                self.optimizer.zero_grad()
                out.loss.backward()
                self.optimizer.step()
                history.append({"epoch": epoch, "step": step, "loss": out.loss.item()})
        return history
