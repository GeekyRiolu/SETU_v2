import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Put src/ ahead of the project root so `import setu` resolves to the package.
# (The root entry script is setu_cli.py — deliberately not setu.py — so it can't
# shadow the package; src-first keeps things robust regardless.)
sys.path.insert(0, os.path.join(_ROOT, "src"))
# ...but append the root too, so `interfaces` (the REST/PWA/SDK front-ends) is
# importable. src/ comes first, so `import setu` still resolves to the package.
sys.path.append(_ROOT)


@pytest.fixture(autouse=True)
def _isolate_deployed_models(tmp_path, monkeypatch):
    """Point the engine at an empty models dir so tests don't accidentally pick
    up a real trained model committed/deployed in the repo. Tests that exercise
    ONNX inference pass their own models_root explicitly, overriding this."""
    monkeypatch.setenv("SETU_MODELS_ROOT", str(tmp_path / "empty_models"))
