"""Latency benchmarking against the < 500 ms/sentence target.

Reports mean / p50 / p90 / max wall-clock per sentence. On an ARM-class CPU
these are the deployment numbers; on a dev box they are indicative and the
report says which host produced them.
"""

from __future__ import annotations

import platform
import time
from typing import Any, Callable

LATENCY_TARGET_MS = 500.0


def benchmark_latency(
    translate_fn: Callable[[str], Any], sentences: list[str], warmup: int = 2
) -> dict[str, Any]:
    for s in sentences[:warmup]:  # warm caches / graph
        translate_fn(s)

    latencies = []
    for s in sentences:
        t0 = time.perf_counter()
        translate_fn(s)
        latencies.append((time.perf_counter() - t0) * 1000)

    latencies.sort()
    n = len(latencies)
    mean = sum(latencies) / n
    return {
        "host": f"{platform.machine()} / {platform.processor() or platform.system()}",
        "n": n,
        "latency_ms_mean": round(mean, 1),
        "latency_ms_p50": round(latencies[n // 2], 1),
        "latency_ms_p90": round(latencies[int(n * 0.9)], 1),
        "latency_ms_max": round(latencies[-1], 1),
        "target_ms": LATENCY_TARGET_MS,
        "meets_latency_target": latencies[int(n * 0.9)] < LATENCY_TARGET_MS,
    }
