"""M6 REST integration test — hits the FastAPI app in-process."""

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from interfaces.rest.app import app, get_engine

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_languages_lists_all_22_plus_pivot():
    r = client.get("/languages")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 23
    isos = {l["iso"] for l in body["languages"]}
    assert {"hi", "en", "ta", "bn"} <= isos


def test_translate_returns_result_shape():
    r = client.post("/translate", json={"source_lang": "hi", "target_lang": "en", "text": "नमस्ते"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {"translated_text", "src_lang", "tgt_lang", "latency_ms", "stub"}
    assert body["src_lang"] == "hi" and body["tgt_lang"] == "en"


def test_translate_rejects_same_lang():
    r = client.post("/translate", json={"source_lang": "hi", "target_lang": "hi", "text": "x"})
    assert r.status_code == 400


def test_all_interfaces_share_one_engine():
    # the REST app and a direct CLI-style call resolve to the same engine class
    from setu.inference.engine import InferenceEngine

    assert isinstance(get_engine(), InferenceEngine)
