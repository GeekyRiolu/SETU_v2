#!/usr/bin/env bash
# =============================================================================
# SETU - batch-train many language pairs, BIDIRECTIONAL, at scale.
#
# Loops the per-pair runner (setu_vm_train.sh) over a list of Indic languages,
# training BOTH directions of each (X -> English and English -> X) at LIMIT
# sentences. Fully resumable:
#   * the runner's per-pair stage markers skip finished data/distill/train/quantize
#   * a per-pair .batch_done marker skips whole finished pairs on a re-run
# One pair failing does NOT abort the batch; a summary + FLORES scorecard print
# at the end.
#
# ENV OVERRIDES
#   LANGS      space-separated FLORES codes (default: top-10 incl. Kannada)
#   LIMIT      training sentences per direction (default 500000)
#   DOEVAL     1 = run setu-eval on FLORES after each pair (default 1)
#   EVAL_ARGS  extra setu-eval args, e.g. "--teacher" (adds ratio + significance)
#   DRYRUN     1 = print the plan (pairs + rough GPU-hours) and exit
#   SETU_BASE  where repo/state/out/logs live (default ~/setu)
#
# RUN (inside tmux — this is a multi-DAY job at 500k; see the time note it prints):
#   source ~/ftenv/bin/activate
#   tmux new -s setu_all
#   bash setu_train_all.sh 2>&1 | tee -a ~/setu_all.log
#   # detach: Ctrl-b then d ; reattach: tmux attach -t setu_all
#   # watch one pair:  tail -f ~/setu/logs/kan_Knda-eng_Latn.log
#
# EXAMPLES
#   DRYRUN=1 bash setu_train_all.sh                       # just show the plan
#   LANGS="hin_Deva kan_Knda tam_Taml" bash setu_train_all.sh
#   LIMIT=50000 bash setu_train_all.sh                    # fast full-matrix smoke test
#   EVAL_ARGS="--teacher" bash setu_train_all.sh          # eval vs IndicTrans2 too
#   # ALL 22 scheduled languages:
#   LANGS="asm_Beng ben_Beng brx_Deva doi_Deva guj_Gujr hin_Deva kan_Knda kas_Arab \
#          gom_Deva mai_Deva mal_Mlym mni_Beng mar_Deva npi_Deva ory_Orya pan_Guru \
#          san_Deva sat_Olck snd_Arab tam_Taml tel_Telu urd_Arab" bash setu_train_all.sh
# =============================================================================
set -uo pipefail    # deliberately NOT -e: keep going past a failed pair

LIMIT="${LIMIT:-500000}"
DOEVAL="${DOEVAL:-1}"
EVAL_ARGS="${EVAL_ARGS:-}"
DRYRUN="${DRYRUN:-0}"
SETU_BASE="${SETU_BASE:-$HOME/setu}"
HERE="$(cd "$(dirname "$0")" && pwd)"
RUNNER="$HERE/setu_vm_train.sh"
REPO="$SETU_BASE/SETU_v2/SETU"
LOGDIR="$SETU_BASE/logs"
PY="$(command -v python3 || command -v python)"
mkdir -p "$LOGDIR" "$SETU_BASE/state"

# top-10 scheduled Indian languages by speakers, incl. Kannada (FLORES codes)
DEFAULT_LANGS="hin_Deva ben_Beng mar_Deva tel_Telu tam_Taml guj_Gujr urd_Arab kan_Knda ory_Orya mal_Mlym"
LANGS="${LANGS:-$DEFAULT_LANGS}"

# build the bidirectional pair list: X->en and en->X for each language
PAIRS=()
for L in $LANGS; do
  PAIRS+=( "${L}-eng_Latn" "eng_Latn-${L}" )
done

echo "=============================================================="
echo " SETU batch — ${#PAIRS[@]} pairs (bidirectional)  LIMIT=$LIMIT"
echo " languages : $LANGS"
echo " eval      : $([ "$DOEVAL" = 1 ] && echo "setu-eval flores $EVAL_ARGS" || echo off)"
echo " runner    : $RUNNER"
echo "=============================================================="
printf '   %s\n' "${PAIRS[@]}"
echo "  rough budget: ~$(( ${#PAIRS[@]} * 10 )) GPU-hours at LIMIT=500000 (order of magnitude,"
echo "  ~8-12 h/pair on the A40-16Q vGPU). Lower LIMIT or trim LANGS to fit your window."

if [ ! -f "$RUNNER" ]; then
  echo "ERROR: runner not found at $RUNNER — keep setu_train_all.sh next to setu_vm_train.sh"
  exit 1
fi
if [ "$DRYRUN" = "1" ]; then echo; echo "DRYRUN=1 — plan only, exiting."; exit 0; fi

start=$(date +%s)
declare -A RESULT
for P in "${PAIRS[@]}"; do
  MARK="$SETU_BASE/state/$P/.batch_done"
  if [ -f "$MARK" ]; then echo; echo ">> $P — already complete, skipping"; RESULT["$P"]=skip; continue; fi
  echo; echo ">> ================= $P   ($(date '+%F %T')) ================="
  LOG="$LOGDIR/${P}.log"
  echo "   training (log: $LOG) ..."
  if PAIR="$P" LIMIT="$LIMIT" bash "$RUNNER" >>"$LOG" 2>&1; then
    touch "$MARK"; RESULT["$P"]=ok
    echo "   trained OK -> $SETU_BASE/out/setu_${P}_model.zip"
    if [ "$DOEVAL" = "1" ]; then
      echo "   eval on FLORES ..."
      if ( cd "$REPO" && setu-eval --pair "$P" --testset flores $EVAL_ARGS ) >>"$LOG" 2>&1; then
        RESULT["$P"]="ok+eval"
      else
        RESULT["$P"]="ok/eval-failed"; echo "   (eval failed — see $LOG; training is fine)"
      fi
    fi
  else
    RESULT["$P"]=FAIL
    echo "   FAILED — see $LOG ; continuing with the next pair"
  fi
done

echo; echo "===================== BATCH SUMMARY ====================="
for P in "${PAIRS[@]}"; do printf '  %-26s %s\n' "$P" "${RESULT["$P"]:-?}"; done
echo "  elapsed: $(( ($(date +%s) - start) / 3600 ))h $(( (($(date +%s) - start) % 3600) / 60 ))m"

# consolidated FLORES scorecard from the per-pair eval JSONs
echo; echo "===================== FLORES SCORECARD =================="
"$PY" - "$REPO" "${PAIRS[@]}" <<'PYCODE'
import json, sys
from pathlib import Path
repo = Path(sys.argv[1]); pairs = sys.argv[2:]
print(f"  {'pair':26} {'BLEU':>6} {'chrF':>6} {'ratio':>6}")
for p in pairs:
    f = repo / "models" / p / "eval_flores_devtest.json"
    if not f.exists():
        print(f"  {p:26} {'-':>6} {'-':>6} {'-':>6}"); continue
    d = json.loads(f.read_text(encoding="utf-8")); st = d.get("student", {})
    def fmt(x, w=6, p=2): return (f"%{w}.{p}f" % x) if isinstance(x, (int, float)) else f"{'-':>{w}}"
    print(f"  {p:26} {fmt(st.get('bleu'))} {fmt(st.get('chrf'))} {fmt(d.get('bleu_ratio'), 6, 3)}")
PYCODE

echo; echo "ALL PAIRS PROCESSED."
echo "  model zips : $SETU_BASE/out/setu_<pair>_model.zip"
echo "  per-pair logs: $LOGDIR/<pair>.log"
echo "  re-run this script any time — finished pairs are skipped."
