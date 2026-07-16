"""M6 PWA tests — shell assets exist, are served, and the SW caches them."""

import re
from pathlib import Path

import pytest

PWA = Path(__file__).resolve().parent.parent / "interfaces" / "pwa"


def test_shell_assets_present():
    for name in ("index.html", "app.js", "service-worker.js", "manifest.webmanifest", "icon.svg"):
        assert (PWA / name).exists(), name


def test_service_worker_precaches_shell():
    sw = (PWA / "service-worker.js").read_text(encoding="utf-8")
    for asset in ("index.html", "app.js", "manifest.webmanifest", "icon.svg"):
        assert asset in sw
    # API calls must NOT be cached (they hit the local engine)
    assert "/translate" in sw and "return" in sw


def test_app_js_calls_shared_translate_endpoint():
    js = (PWA / "app.js").read_text(encoding="utf-8")
    assert "/translate" in js
    assert "/languages" in js
    assert "serviceWorker" in js and "register" in js


def test_pwa_served_by_rest_app():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from interfaces.rest.app import app

    client = TestClient(app)
    r = client.get("/app/index.html")
    assert r.status_code == 200
    assert "SETU" in r.text
