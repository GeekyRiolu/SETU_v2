# SETU on a GPU VM (A40) — upload, train, download

Runs the same **SeqKD deployable-model** pipeline as `colab/setu_seqkd_deploy.ipynb`,
but on an SSH VM via **PuTTY + WinSCP**. Difference from Colab: the job must survive
you closing PuTTY, so we run it inside **tmux**. It is **resumable** — re-run the same
command after any disconnect and finished stages are skipped.

You upload **one file**: `setu_vm_train.sh`. It clones the repo, reuses the VM's
existing CUDA **torch** (never reinstalls it), installs the rest, trains, quantises,
and zips the model for download.

---

## 0. Before you start
- A GPU VM with an NVIDIA driver (`nvidia-smi` works) and **~30 GB free disk**.
- The env that already has **torch + CUDA** (yours looks like `ftenv`).
- Internet on the VM (it downloads the teacher model + data from HuggingFace).
  Gated sources (BPCC) are auto-skipped; it falls back to ungated Samanantar — same as Colab.

---

## 1. Upload the script (WinSCP)
1. Open **WinSCP** → protocol **SFTP** → host = VM IP, your username/key → **Login**.
2. Left pane (your PC): browse to
   `C:\Users\z005apck\Desktop\SETU_v2\SETU\vm\`
3. Right pane (VM): go to your home folder (e.g. `/home/rishabhs`).
4. Drag **`setu_vm_train.sh`** from left to right.

## 2. Connect (PuTTY)
Open **PuTTY** → same host/user → **Open**. You now have a shell on the VM.

## 3. Normalize + activate + cross-check (no training yet)
```bash
sed -i 's/\r$//' setu_vm_train.sh          # strip any Windows CR (safe if already clean)

source ~/ftenv/bin/activate                # <-- your torch+CUDA env (or: conda activate ftenv)

CHECK_ONLY=1 bash setu_vm_train.sh         # audits the env and EXITS — installs nothing
```
Read the **requirements audit** it prints:
- `torch ... cuda=True gpu=NVIDIA A40 ...` → good. **If torch is < 2.6**, do step 3b (the
  teacher's `.bin` won't load on older torch).
- `torchvision ... ok` → good; `BROKEN vs torch` → step 3b fixes it.
- Any dep marked `MISSING` gets installed automatically on the first real run.
- The script auto-picks the `transformers` ceiling from your torch (≥2.6 → up to 4.53;
  <2.6 → <4.50). To keep `ftenv` pristine, use the isolated-venv option in **Troubleshooting**.

### 3b. (only if the audit flagged torch <2.6 or a torchvision mismatch)
SETU's teacher needs **torch ≥ 2.6** with a **matching torchvision**. One command does both
(`cu124` works on driver 535; use `cu118` if `cuda=` comes back `False`):
```bash
pip install --upgrade "torch>=2.6" "torchvision==0.21.0" --index-url https://download.pytorch.org/whl/cu124
python -c "import torch, torchvision, torchvision.ops; print(torch.__version__, torchvision.__version__, 'cuda=', torch.cuda.is_available())"
```
Expect `2.6.0+cu124 0.21.0+cu124 cuda= True`, then re-run the step-5 audit to confirm.

## 4. Train — inside tmux (survives disconnects)
First time only, install tmux (skip if `tmux -V` already works):
```bash
sudo apt-get update && sudo apt-get install -y tmux    # Ubuntu/Debian
# RHEL/CentOS/Amazon Linux:  sudo yum install -y tmux
# ftenv is conda, no sudo:   conda install -y -c conda-forge tmux
```
Then start a persistent session and launch the run:
```bash
tmux new -s setu                           # start a persistent session
source ~/ftenv/bin/activate                # activate again inside tmux

bash setu_vm_train.sh 2>&1 | tee ~/setu_train.log
```
Now **detach** so it keeps running even if PuTTY closes: press **Ctrl-b**, release, then **d**.

**No tmux and no sudo?** Use `nohup` instead — same disconnect-proof result, zero install:
```bash
source ~/ftenv/bin/activate
nohup bash setu_vm_train.sh > ~/setu_train.log 2>&1 &
echo "PID $!"                              # note the PID; close PuTTY freely
```
Reconnect and check with `tail -f ~/setu_train.log` / `ps aux | grep train_full`.

Reconnect / check progress any time:
```bash
tmux attach -t setu          # jump back into the live session
tail -f ~/setu_train.log     # or just follow the log
nvidia-smi                   # confirm the GPU is busy
```

Runtime: ~5–6 h on a T4; an A40 is markedly faster. If it disconnects, just re-run the
same `bash setu_vm_train.sh` — data/distill/train/quantize each skip once done. The only
work a mid-training crash repeats is that one training pass (the ~40 min distill is saved).

**When it finishes** the log ends with:
```
=== ALL DONE
Download this file with WinSCP:
    /home/<you>/setu/out/setu_seqkd_model.zip
```

## 5. Download the model (WinSCP)
In WinSCP, right pane → go to `/home/<you>/setu/out/` → drag
**`setu_seqkd_model.zip`** (and `report_seqkd.json` for the BLEU scores) to your PC.

## 6. Use it locally
Unzip into your local repo's `models/` folder, then translate:
```powershell
# PowerShell, from C:\Users\z005apck\Desktop\SETU_v2\SETU
Expand-Archive .\setu_seqkd_model.zip -DestinationPath .\models\ -Force
python setu_cli.py --src hi --tgt en --text "भारत एक विशाल देश है।"
```
You should get `models\hin_Deva-eng_Latn\...` and a real (non-stub) translation.

---

## Knobs (set before the run)
```bash
LIMIT=250000  bash setu_vm_train.sh    # default; strongest deployable target
LIMIT=100000  bash setu_vm_train.sh    # faster if GPU time is tight
BATCH=64      bash setu_vm_train.sh    # only if nvidia-smi shows a full 48 GB A40
```

## Troubleshooting
- **"no torch in the active Python"** → you forgot to activate the env. Run
  `source ~/ftenv/bin/activate` first. (Or `MANAGE_TORCH=1 bash setu_vm_train.sh`
  to let the script install a CUDA torch itself.)
- **Protect `ftenv` from the `transformers<4.54` pin** — run in an isolated venv that
  still *sees* the CUDA torch:
  ```bash
  source ~/ftenv/bin/activate
  python -m venv --system-site-packages ~/setu-venv   # inherits torch+CUDA, isolates the rest
  source ~/setu-venv/bin/activate
  bash setu_vm_train.sh
  ```
- **`ValueError: ... upgrade torch to at least v2.6` (CVE-2025-32434)** — transformers ≥4.50
  won't load the teacher's `.bin` on torch <2.6. Either upgrade torch (below) or let the
  script pin `transformers<4.50` (it does this automatically when it sees torch <2.6).
- **Upgrading torch (to satisfy the above)** — pick a CUDA build your driver supports
  (`nvidia-smi` shows the CUDA version); `cu124` works on driver 535, `cu118` on anything 12.x:
  ```bash
  pip install --upgrade "torch>=2.6" --index-url https://download.pytorch.org/whl/cu124
  ```
  Then **match torchvision** or the teacher load crashes with
  `RuntimeError: operator torchvision::nms does not exist` (torchvision built for the old torch):
  ```bash
  pip install "torchvision==0.21.0" --index-url https://download.pytorch.org/whl/cu124   # pairs with torch 2.6.0
  # if a torchaudio error follows: pip install "torchaudio==2.6.0" --index-url .../cu124
  ```
  The `CHECK_ONLY=1` audit flags a torchvision/torch mismatch before you start.
- **`RuntimeError: CUDA driver error: operation not supported`** (hits at the SFT step) —
  the vGPU (A40-16Q / MIG) doesn't support the CUDA virtual-memory APIs that PyTorch's
  `expandable_segments` allocator needs. The script now exports
  `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:False` to avoid it; if you run
  `scripts/train_full.py` by hand, `export` that first.
- **CUDA out of memory** → lower it: `BATCH=16 LIMIT=150000 bash setu_vm_train.sh`.
- **Start a stage over** → delete its marker in `~/setu/state/` (e.g.
  `rm ~/setu/state/.done_distill`) and re-run.
- **Can't reach GitHub from the VM** → instead of relying on the clone, WinSCP your whole
  local `SETU` folder to `~/setu/SETU_v2/SETU`, then run the script — it detects the repo
  and skips cloning.

## Disk & starting clean
- **Space needed:** the run adds ~10–15 GB total (torch+CUDA ~3 GB, teacher cache ~1 GB,
  corpora ~0.2 GB, checkpoint ~1 GB, ONNX ~0.5 GB). Everything lives under `/home`
  (`~/setu` + `~/.cache`), so check it has room with `df -h /home`.
- **Upgrading torch removes the old one automatically** — `pip install --upgrade` uninstalls
  the previous torch + CUDA libs (and pinning `torchvision==0.21.0` replaces the old
  torchvision). No manual cleanup of old installs is needed.
- **Clean restart (reuse the ready env):** `rm -rf ~/setu` wipes the repo, data, distilled
  corpus, checkpoints, models and all `.done_*` markers. Re-run the steps; since the env
  already has the deps, it goes straight to data → distill → train.
- **Reclaim cache space (optional):** `pip cache purge` and `rm -rf ~/.cache/huggingface`
  (the teacher + datasets re-download on the next run).
