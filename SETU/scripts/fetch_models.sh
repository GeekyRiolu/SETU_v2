#!/usr/bin/env bash
# Fetch SETU's Phase-1 trained models (11 languages, 22 INT4 ONNX pairs, ~1.8 GB)
# from the GitHub release and extract them into models/.
#
#   bash scripts/fetch_models.sh
#
# Everything runs fully offline afterwards. Needs ~2.4 GB free disk.
set -euo pipefail

REPO="GeekyRiolu/SETU_v2"
TAG="phase1-models"
ASSETS=(setu_models_indic-en.tar.gz setu_models_en-indic.tar.gz)

# this script lives in SETU/scripts/ -> resolve the SETU/ dir
SETU_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SETU_DIR"
mkdir -p models

echo "Downloading model archives from $REPO ($TAG) ..."
if command -v gh >/dev/null 2>&1; then
  gh release download "$TAG" -R "$REPO" -p 'setu_models_*.tar.gz' -D /tmp --clobber
else
  base="https://github.com/$REPO/releases/download/$TAG"
  for a in "${ASSETS[@]}"; do
    echo "  $a"
    curl -fL --retry 3 -o "/tmp/$a" "$base/$a"
  done
fi

for a in "${ASSETS[@]}"; do
  echo "Extracting $a ..."
  tar xzf "/tmp/$a" -C "$SETU_DIR"
done

echo "Done. models/ now has $(ls models | wc -l) language pairs."
echo "Next: PYTHONPATH=src:. uvicorn interfaces.rest.app:app --port 8000"
