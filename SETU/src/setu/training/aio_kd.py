"""AIO-KD — All-In-One knowledge distillation: one student trained across many
translation directions at once, with cross-lingual balancing so high-resource
directions don't drown out low-resource ones.

Balancing follows the standard temperature-sampled scheme (Arivazhagan et al.
2019): a direction with probability p_i ∝ (n_i / N) ** (1/T). T=1 samples in
proportion to size (high-resource dominates); T→∞ samples uniformly. Each step
draws a direction by that distribution, then a batch from it.

This is a multilingual concern — reach for it only once the single pair works.
"""

from __future__ import annotations

from typing import Any


def balancing_weights(direction_sizes: dict[str, int], temperature: float) -> dict[str, float]:
    """Temperature-scaled sampling probability per direction. T=1 → proportional
    to size; larger T → flatter (protects low-resource directions)."""
    total = sum(direction_sizes.values())
    if total == 0:
        raise ValueError("no data in any direction")
    scaled = {d: (n / total) ** (1.0 / temperature) for d, n in direction_sizes.items()}
    z = sum(scaled.values())
    return {d: w / z for d, w in scaled.items()}


class AIOKDOrchestrator:
    """Trains one student over several direction datasets with cross-lingual
    balancing. Datasets are anything exposing `.entries` and `.collate(list)`
    (e.g. CorpusDataset), keyed by a direction label like 'hin_Deva-eng_Latn'.
    """

    def __init__(self, model, datasets: dict[str, Any], config: dict[str, Any]):
        import torch

        self.model = model
        self.datasets = datasets
        self.config = config
        self.temperature = config.get("sampling_temperature", 1.5)
        self.weights = balancing_weights(
            {d: len(ds.entries) for d, ds in datasets.items()}, self.temperature
        )
        self.optimizer = torch.optim.AdamW(model.parameters(), lr=config.get("lr", 5e-4))

    def _sample_direction(self, step: int) -> str:
        # deterministic weighted round-robin (no RNG — keeps runs reproducible):
        # pick the direction whose cumulative expected count is most behind.
        directions = list(self.weights)
        target = [(step + 1) * self.weights[d] for d in directions]
        if not hasattr(self, "_served"):
            self._served = {d: 0 for d in directions}
        deficits = [target[i] - self._served[d] for i, d in enumerate(directions)]
        chosen = directions[max(range(len(directions)), key=lambda i: deficits[i])]
        self._served[chosen] += 1
        return chosen

    def train(self, steps: int, batch_size: int | None = None) -> list[dict]:
        batch_size = batch_size or self.config.get("batch_size", 32)
        history = []
        self.model.train()
        cursors = {d: 0 for d in self.datasets}
        for step in range(steps):
            direction = self._sample_direction(step)
            ds = self.datasets[direction]
            start = cursors[direction] % max(1, len(ds.entries))
            batch_entries = ds.entries[start:start + batch_size]
            if not batch_entries:
                batch_entries = ds.entries[:batch_size]
            cursors[direction] += batch_size
            batch = ds.collate(batch_entries)

            out = self.model(
                input_ids=batch["input_ids"],
                attention_mask=batch["attention_mask"],
                labels=batch["labels"],
            )
            self.optimizer.zero_grad()
            out.loss.backward()
            self.optimizer.step()
            history.append({"step": step, "direction": direction, "loss": out.loss.item()})
        return history

    def coverage(self) -> dict[str, int]:
        return dict(getattr(self, "_served", {}))
