#!/usr/bin/env bash
# =============================================================================
# SETU - SeqKD deployable-model training on a GPU VM (A40 / any CUDA GPU)
#
# Mirrors colab/setu_seqkd_deploy.ipynb but built for an SSH VM:
#   * resumable (done-markers) - safe to re-run after any disconnect
#   * REUSES the torch + CUDA already installed on the VM (never reinstalls it)
#   * packages the final model into one zip for WinSCP download
#
# QUICK START (see vm/README_VM.md for the full PuTTY/WinSCP walkthrough)
#   1. activate the env that already has torch+CUDA, e.g.
#        source ~/ftenv/bin/activate        # venv     OR
#        conda activate ftenv               # conda
#   2. cross-check the environment first (no install, no training):
#        CHECK_ONLY=1 bash setu_vm_train.sh
#   3. run the full pipeline INSIDE tmux so it survives a disconnect:
#        tmux new -s setu
#        bash setu_vm_train.sh 2>&1 | tee ~/setu_train.log
#        # detach with Ctrl-b then d ; reattach with: tmux attach -t setu
#
# ENV OVERRIDES (all optional)
#   LIMIT=500000       training sentences (250k = strongest deployable target)
#   BATCH=32           distill batch size (32 is safe for 16 GB; raise on 48 GB)
#   SETU_BASE=~/setu   where the repo, state markers and outputs live
#   CHECK_ONLY=1       audit the environment and exit (no install / no training)
#   MANAGE_TORCH=1     allow installing torch if the VM has none (default: 0)
# =============================================================================
set -euo pipefail

LIMIT="${LIMIT:-500000}"
BATCH="${BATCH:-32}"
SETU_BASE="${SETU_BASE:-$HOME/setu}"
CHECK_ONLY="${CHECK_ONLY:-0}"
MANAGE_TORCH="${MANAGE_TORCH:-0}"
REPO_URL="https://github.com/GeekyRiolu/SETU_v2.git"
REPO="$SETU_BASE/SETU_v2/SETU"
STATE="$SETU_BASE/state"
OUT="$SETU_BASE/out"

mkdir -p "$SETU_BASE" "$STATE" "$OUT"
log(){ echo; echo "=== $(date '+%F %T')  $*"; }
have(){ command -v "$1" >/dev/null 2>&1; }
PY="$(command -v python3 || command -v python)"

# vGPU note: A40-16Q (and MIG / vGPU profiles generally) lack the CUDA virtual-memory
# APIs that PyTorch's expandable_segments allocator uses -> "CUDA driver error: operation
# not supported" on the first CUDA alloc. train_full.py now defaults this OFF; we also
# export it here (respecting any value you already set) so a hand-run stays safe too.
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:False}"

# ----------------------------------------------------------------------------
log "environment"
echo "python : $PY  ($($PY -V 2>&1))"
echo "alloc  : PYTORCH_CUDA_ALLOC_CONF=$PYTORCH_CUDA_ALLOC_CONF"
echo "pip    : $(command -v pip || command -v pip3 || echo MISSING)"
if have nvidia-smi; then nvidia-smi -L || true; else echo "nvidia-smi: NOT FOUND (no driver?)"; fi
echo "base   : $SETU_BASE   | LIMIT=$LIMIT  BATCH=$BATCH"
echo "disk   : $(df -h "$SETU_BASE" | tail -1)"

# ----------------------------------------------------------------------------
log "requirements audit (matches SETU pyproject.toml)"
"$PY" - <<'PYCODE'
import importlib.metadata as md
def ver(pkg):
    try: return md.version(pkg)
    except Exception: return None
tv = (0, 0)
try:
    import torch
    tv = tuple(map(int, torch.__version__.split("+")[0].split(".")[:2]))
    cu = torch.cuda.is_available()
    name = torch.cuda.get_device_name(0) if cu else "-"
    mem  = f"{torch.cuda.get_device_properties(0).total_memory/1e9:.0f} GB" if cu else "-"
    print(f"  torch          {torch.__version__:14} cuda={cu}  gpu={name} {mem}")
except Exception as e:
    print(f"  torch          MISSING        ({e})")
# torchvision is optional for SETU, but if present it MUST match torch's ABI -
# transformers imports it while loading the teacher. importing .ops forces the check.
try:
    import torchvision, torchvision.ops  # noqa: F401
    print(f"  torchvision    {torchvision.__version__:14} ok (matches torch)")
except ModuleNotFoundError:
    pass
except Exception as e:
    print(f"  torchvision    BROKEN vs torch ({type(e).__name__}) -> reinstall a matching torchvision build")
checks = [
    ("transformers",     ">=4.42,<4.54 (4.50+ needs torch>=2.6; else pinned <4.50)"),
    ("datasets",         ">=3.0"),
    ("sacrebleu",        ">=2.3"),
    ("sentencepiece",    ">=0.2"),
    ("einops",           "(rotary IndicTrans2)"),
    ("IndicTransToolkit",">=1.1"),
    ("onnx",             ">=1.16"),
    ("onnxruntime",      ">=1.18"),
    ("optimum",          ">=1.20  (optimum[onnxruntime])"),
    ("PyYAML",           "(core)"),
]
for pkg, note in checks:
    v = ver(pkg); tag = v if v else "MISSING"; flag = ""
    if pkg == "transformers" and v:
        maj = tuple(int(x) for x in (v.split(".")[:2] + ["0"])[:2])
        if maj >= (4, 50) and tv < (2, 6):
            flag = "  <-- torch<2.6 + this version can't load the teacher .bin (install pins it <4.50)"
    print(f"  {pkg:16} {tag:14} {note}{flag}")
PYCODE

if [ "$CHECK_ONLY" = "1" ]; then
  log "CHECK_ONLY=1 - audit done, exiting before any install / training."
  exit 0
fi

# ----------------------------------------------------------------------------
# system tools (best effort; needs sudo - harmless if already present)
if ! have git || ! have zip || ! have unzip; then
  log "installing git/zip via apt (sudo - best effort)"
  sudo apt-get update -y || true
  sudo apt-get install -y git zip unzip || true
fi

# ----------------------------------------------------------------------------
# torch guard - we NEVER reinstall a working CUDA torch
if ! "$PY" -c 'import torch' 2>/dev/null; then
  if [ "$MANAGE_TORCH" = "1" ]; then
    log "no torch found - installing CUDA torch (MANAGE_TORCH=1)"
    pip install torch --index-url https://download.pytorch.org/whl/cu121
  else
    echo
    echo "ERROR: no 'torch' in the active Python ($PY)."
    echo "Activate the env that already has torch+CUDA first, e.g.:"
    echo "    source ~/ftenv/bin/activate      # or:  conda activate ftenv"
    echo "then re-run.  (Or pass MANAGE_TORCH=1 to let this script install torch.)"
    exit 1
  fi
fi

# ----------------------------------------------------------------------------
log "clone SETU_v2 (only if absent - keeps distilled corpus + checkpoints)"
# git puts .git at the clone ROOT ($SETU_BASE/SETU_v2/.git); the project is the SETU/
# subdir ($REPO). Detect an existing repo by either, so re-runs reuse it (and keep the
# distilled corpus) instead of trying to re-clone into a non-empty dir.
if [ -d "$SETU_BASE/SETU_v2/.git" ] || [ -f "$REPO/pyproject.toml" ]; then
  echo "repo present at $REPO - reusing (distilled corpus + checkpoints kept)"
else
  rm -rf "$SETU_BASE/SETU_v2"        # clear any partial/empty dir so the clone can't wedge
  git clone "$REPO_URL" "$SETU_BASE/SETU_v2"
fi
cd "$REPO"

# ----------------------------------------------------------------------------
if [ ! -f "$STATE/.done_install" ]; then
  log "install SETU + deps (torch left untouched)"
  pip install -q --upgrade pip
  pip install -q -e .                       # core package + setu-* commands (pyyaml)
  # transformers upper bound depends on torch: 4.50+ adds a torch.load guard
  # (CVE-2025-32434) that refuses the teacher's .bin checkpoint unless torch>=2.6.
  # So on torch>=2.6 allow up to <4.54 (the real cap: IndicTrans2 remote code breaks
  # at 4.54); on older torch stay just under the guard at <4.50.
  if "$PY" -c 'import torch,sys; v=tuple(map(int,torch.__version__.split("+")[0].split(".")[:2])); sys.exit(0 if v>=(2,6) else 1)'; then
    TF="transformers>=4.42,<4.54"; echo "torch>=2.6 -> $TF"
  else
    TF="transformers>=4.42,<4.50"; echo "torch<2.6  -> $TF (avoids the .bin load guard)"
  fi
  pip install -q "$TF" "sacrebleu>=2.3" "sentencepiece>=0.2" einops \
      "IndicTransToolkit>=1.1" "datasets>=3.0" \
      "onnx>=1.16" "onnxruntime>=1.18" "optimum[onnxruntime]>=1.20"
  touch "$STATE/.done_install"
else
  echo "deps already installed - skipping (delete $STATE/.done_install to redo)"
fi

# ----------------------------------------------------------------------------
log "GPU configs"
cp -f configs/model.gpu.yaml configs/model.yaml
cp -f configs/training.gpu.yaml configs/training.yaml
sed -i 's/device: cpu/device: cuda/' configs/teacher.yaml

# hard preflight - training needs a visible GPU
"$PY" - <<'PYCODE'
import torch
assert torch.cuda.is_available(), "CUDA not available to torch - check drivers / env"
print("GPU OK:", torch.cuda.get_device_name(0))
PYCODE

# ----------------------------------------------------------------------------
log "resume status"
for m in data:.done_data distill:.done_distill seqkd:.done_seqkd quantize:.done_quantize; do
  n="${m%%:*}"; f="${m##*:}"
  if [ -f "$STATE/$f" ]; then echo "  [DONE] $n"; else echo "  [ -- ] $n"; fi
done

# 1) DATA  (SeqKD needs no preference pairs)
if [ ! -f "$STATE/.done_data" ]; then
  log "M1 data (limit $((LIMIT+2000)))"
  setu-data --limit $((LIMIT+2000))
  touch "$STATE/.done_data"
else echo "data done - skip"; fi

# 2) DISTILL  (teacher 1-best corpus, greedy)
if [ ! -f "$STATE/.done_distill" ]; then
  log "distill teacher corpus (limit $LIMIT, batch $BATCH, greedy)"
  setu-distill --limit "$LIMIT" --batch-size "$BATCH" --beams 1
  touch "$STATE/.done_distill"
else echo "distill done - skip"; fi
D="data/distilled/hin_Deva-eng_Latn/train.jsonl"
test -s "$D" || { echo "ERROR: distill produced no corpus"; exit 1; }
echo "distilled rows: $(wc -l < "$D")"

# 3) SeqKD training  (SFT on teacher targets, no DPO; eval on real refs)
if [ ! -f "$STATE/.done_seqkd" ]; then
  log "SeqKD SFT on teacher targets (limit $LIMIT)"
  "$PY" scripts/train_full.py --train-corpus distilled --skip-dpo --limit "$LIMIT" --dev-size 500
  cp checkpoints/hin_Deva-eng_Latn/train_report.json "$OUT/report_seqkd.json"
  touch "$STATE/.done_seqkd"
else echo "SeqKD done - skip"; fi
"$PY" -c "import json;print('SeqKD eval:',json.load(open('$OUT/report_seqkd.json'))['sft_eval'])" || true

# 4) QUANTIZE  -> INT8/INT4 ONNX, deployed under models/
if [ ! -f "$STATE/.done_quantize" ]; then
  log "quantise -> ONNX INT8/INT4 + deploy under models/"
  setu-quantize --student sft
  touch "$STATE/.done_quantize"
else echo "quantize done - skip"; fi
setu-report --offline-proof || true

# 5) offline smoke-test
log "offline translation smoke-test"
"$PY" - <<'PYCODE'
import sys; sys.path.insert(0, 'src')
from setu.inference.engine import InferenceEngine
eng = InferenceEngine(models_root='models')
print("using trained model:", not eng.is_stub)
for s in ['भारत एक विशाल देश है।', 'मुझे किताबें पढ़ना पसंद है।', 'आज मौसम अच्छा है।']:
    print("  ", s, "->", eng.translate(s, 'hi', 'en').translated_text)
PYCODE

# 6) package for download
log "package deployable model"
rm -f "$OUT/setu_seqkd_model.zip"
( cd models && zip -qr "$OUT/setu_seqkd_model.zip" hin_Deva-eng_Latn )
cp -f checkpoints/hin_Deva-eng_Latn/train_report.json "$OUT/report_seqkd.json" 2>/dev/null || true

log "ALL DONE"
echo "Download this file with WinSCP:"
echo "    $OUT/setu_seqkd_model.zip"
ls -lh "$OUT/"
