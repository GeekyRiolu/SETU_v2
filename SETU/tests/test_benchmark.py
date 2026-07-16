"""M9 latency-benchmark tests — pure timing math, no model."""

from setu.benchmark.latency import LATENCY_TARGET_MS, benchmark_latency


def test_benchmark_reports_percentiles_and_target():
    calls = []
    result = benchmark_latency(lambda s: calls.append(s), [f"s{i}" for i in range(20)], warmup=2)
    assert result["n"] == 20
    assert result["latency_ms_p50"] <= result["latency_ms_p90"] <= result["latency_ms_max"]
    assert result["target_ms"] == LATENCY_TARGET_MS
    assert isinstance(result["meets_latency_target"], bool)
    assert "host" in result


def test_meets_target_gate():
    fast = benchmark_latency(lambda s: None, ["x"] * 10)
    assert fast["meets_latency_target"] is True  # a no-op is well under 500 ms
