# Documentation: Website Fingerprinting Pipeline

Complete pipeline for Deep Fingerprinting (DF) attacks in Shadow-simulated Tor networks.
Part of Oliver Staub's bachelor thesis at HSLU.

## Architecture

```
Shadow Simulation                        ML Pipeline
┌──────────────────────────┐            ┌─────────────────────────┐
│ zimserver0               │            │                         │
│  (zimsrv.py × N ports,   │            │ pcap_to_npz.py          │
│   one per page)          │            │                         │
│                          │            │  reads: schedule.json   │
│ monitor0..N              │  pcaps     │  reads: monitor pcaps   │
│  (Tor + wget2, one page  │──────────> │  outputs: dataset.npz   │
│   at a time, pcap on)    │            │        │                │
│                          │            │ WFlib dataset_split.py  │
│ Tor relays (from         │            │  train/valid/test.npz   │
│  tornettools generate)   │            │        │                │
└──────────────────────────┘            │ WFlib train.py (DF)     │
                                        │        │                │
                                        │ WFlib test.py → results │
                                        └─────────────────────────┘
```

**Approach:** Each monitor node fetches one page at a time using wget2
(`--page-requisites --max-threads=30`) through Tor, with NEWNYM between visits
for circuit isolation. pcap captures on each monitor provide labeled traffic
samples segmented by the known timing schedule.

## Files

```
src/
├── ml/2023
│   ├── explainwf_to_npz.py     # Convert 2023 cell traces → WFlib .npz
│   ├── pcap_to_npz.py          # Convert Shadow pcaps → WFlib .npz
│   ├── run_df.sh               # End-to-end: convert → split → train → test
│   ├── venv/                   # Python environment
│   └── wflib/                  # WFlib submodule (PyTorch DF classifier)
├── simulation/
│   ├── shadowctl.py            # Main entry point: simulation control over SSH
│   ├── generate-wf-config.py   # Add WF monitor+zimserver nodes to a shadow config
│   ├── setup-wf-server.sh      # Build wget2, install deps, generate urls.txt
│   ├── generate-urls.py        # (runs on server) sample random articles from ZIM
│   ├── newnym.py               # (runs on server) SIGNAL NEWNYM to Tor control port
│   ├── generated/              # URL list(s) generated from the ZIM file
│   └── exp1/, exp2/, …         # One sub-directory per experiment
```

## Setup

### 1. Local environment

```bash
cd src/ml
python3 -m venv venv

# Activate the venv — use the line matching your shell:
source venv/bin/activate          # bash / zsh
source venv/bin/activate.fish     # fish

pip install numpy torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install tqdm pandas scikit-learn einops timm pytorch-metric-learning captum pyyaml dpkt
pip install -e wflib/
```

> **Note on shell activation:** Every `source venv/bin/activate` below assumes
> bash or zsh. If you use fish, replace with `source venv/bin/activate.fish`.
> Alternatively, skip activation and call the venv's Python directly:
> `./venv/bin/python3 script.py` and `./venv/bin/pip install ...`

### 2. Server setup

**Step 2a — install build dependencies on the server (manual, one-time).**

`sudo` needs a TTY for the password prompt, so this can't run from the automated
script. SSH in and run the apt command **as one single line** (line-wrapped
versions with `\` often lose characters when copy-pasted):

```bash
ssh projectadmin@shadowsrv-001.prod.projects.ls.eee.intern
```

Then on the server, paste this entire command on one line:

```
sudo apt-get update && sudo apt-get install -y git autoconf automake libtool libtool-bin pkg-config libgnutls28-dev libpcre2-dev flex texinfo gettext autopoint libnghttp2-dev libbrotli-dev libzstd-dev lzip
```

Then `exit` the SSH session.

**Step 2b — build wget2, install libzim, copy helper scripts (automated).**

```bash
# From your laptop:
bash src/simulation/setup-wf-server.sh
```

The script has three phases you can run individually:

```bash
bash src/simulation/setup-wf-server.sh build   # only build wget2
bash src/simulation/setup-wf-server.sh copy    # install libzim + copy helper scripts (newnym.py, zimsrv.py, generate-urls.py)
bash src/simulation/setup-wf-server.sh urls    # generate urls.txt (needs ZIM, see 2c)
```

Note: the script downloads the wget2 SOCKS patch directly from the upstream
[explainwf-popets2023 GitHub repo](https://github.com/explainwf-popets2023/explainwf-popets2023.github.io),
so no local copy of that repo is needed on your laptop.

**Step 2c — Wikipedia ZIM data.**

You need a Wikipedia ZIM file on the server to serve as the target websites.
The Jansen & Wails 2023 paper uses the full English Wikipedia (~120 GB); for
our thesis experiment we use the **Simple English Wikipedia with images** —
only ~3.4 GB but still thousands of distinct pages for the WF classifier.

> **Note:** The Kiwix ZIM dumps are rotated. Old snapshots get removed when new
> ones are published. If the URL below returns 404, check the current listings
> at <https://dumps.wikimedia.org/other/kiwix/zim/wikipedia/> and adjust the
> date in the filename.

SSH in and download:

```bash
ssh projectadmin@shadowsrv-001.prod.projects.ls.eee.intern
mkdir -p ~/wikidata && cd ~/wikidata

# Simple English Wikipedia with images (~3.4 GB, recommended)
wget https://dumps.wikimedia.org/other/kiwix/zim/wikipedia/wikipedia_en_simple_all_maxi_2026-02.zim

# Rename so the Shadow config finds it at a stable path
mv wikipedia_en_simple_all_maxi_2026-02.zim wikipedia_en_all_maxi.zim

exit
```

**Step 2d — Generate `urls.txt`.**

Instead of reusing the paper's hardcoded list (which references articles that
may not exist in Simple English Wikipedia), sample random articles directly
from your ZIM file. The setup script does this for you:

```bash
# From your laptop — default: 100 pages starting at port 8000
bash src/simulation/setup-wf-server.sh urls

# Pass a number as the second argument for a custom page count:
bash src/simulation/setup-wf-server.sh urls 20
```

## Running Your Own Simulation

> **Important:** always run `shadowctl.py` (especially `run`, `pull-config`,
> `push-config`, `pull-results`) from **`src/simulation/`**, not from the repo
> root. The tool creates and reads per-experiment directories at `<CWD>/<name>/`,
> so running from the wrong place leads to pull/push path mismatches.
>
> ```bash
> cd src/simulation
> python3 shadowctl.py run exp2
> ```

### 1. One-shot: `shadowctl.py run exp2`

The simplest way: one command that runs the full pipeline (generate base config
→ add WF nodes → push → simulate → status) with sensible defaults:

```bash
source src/ml/venv/bin/activate   # or .fish

# One-time per Tor month (downloads Tor metrics + stages them on the server):
python3 src/simulation/shadowctl.py download-data --month 2025-01
python3 src/simulation/shadowctl.py stage        --month 2025-01

# Run a full experiment:
python3 src/simulation/shadowctl.py run exp2

# Override any defaults you like:
python3 src/simulation/shadowctl.py run exp2 \
    --pages 20 --monitors 5 --visits 50 --visit-interval 30
```

Defaults: `--scale 0.01 --monitors 5 --pages 5 --visits 50 --visit-interval 30`,
and URLs come from `src/simulation/generated/urls.txt`.

### What `run` does under the hood

| Step | Subcommand called | Effect |
|------|-------------------|--------|
| 1 | `generate` | `tornettools generate` on server (creates base Tor network config) |
| 2 | `pull-config` | SCP config to `src/simulation/<name>/` |
| 3 | (local) `generate-wf-config.py` | Adds monitor + zimserver hosts to the YAML; writes `schedule.json` |
| 4 | `push-config` + `simulate` | Uploads the modified config and launches Shadow in the background |
| 5 | `status` | Shows initial status + last 20 lines of `sim.log` |

You can of course still run each step individually with its own subcommand
(`generate`, `pull-config`, `push-config`, `simulate`, `status`, `logs`, etc.).

### Check progress

```bash
python3 src/simulation/shadowctl.py status --name exp2           # snapshot
python3 src/simulation/shadowctl.py status --name exp2 --tail 50 # more log
python3 src/simulation/shadowctl.py logs   --name exp2 -f        # stream live
```

### 2. Pull results and convert

Once status shows `COMPLETED`:

```bash
python3 src/simulation/shadowctl.py pull-results --name exp2

# Convert pcaps to WFlib format
cd src/ml && source venv/bin/activate
python3 pcap_to_npz.py \
    --schedule ../simulation/exp2/shadow.config.schedule.json \
    --shadow-data ../simulation/exp2/results/shadow.data/ \
    --output wflib/datasets/Exp2.npz
```

### 3. Train and evaluate DF

```bash
cd wflib
python3 exp/dataset_process/dataset_split.py --dataset Exp2

python3 -u exp/train.py \
    --dataset Exp2 --model DF --device cpu \
    --feature DIR --seq_len 5000 \
    --train_epochs 30 --batch_size 128 \
    --learning_rate 2e-3 --optimizer Adamax \
    --num_workers 0 \
    --eval_metrics Accuracy Precision Recall F1-score \
    --save_metric F1-score --save_name max_f1

python3 -u exp/test.py \
    --dataset Exp2 --model DF --device cpu \
    --feature DIR --seq_len 5000 \
    --batch_size 256 --num_workers 0 \
    --eval_metrics Accuracy Precision Recall F1-score \
    --load_name max_f1
```

Or use the all-in-one script:
```bash
./run_df.sh --pcap --schedule ../simulation/exp2/shadow.config.schedule.json \
    --shadow-data ../simulation/exp2/results/shadow.data/ --dataset Exp2
```

## Circuit Padding Experiment

1. **Baseline:** Run simulation with default Tor config → train DF → record accuracy
2. **With padding:** Edit `tor.client.torrc` to enable/configure Circuit Padding → rerun → compare
3. The hypothesis: Circuit Padding should reduce DF classification accuracy

## WF Defenses

Two defense layers can be combined or used independently:

| Flag | Layer | Mechanism |
|------|-------|-----------|
| `--padding {on,off,reduced}` | Core Tor | Tor's built-in Circuit Padding state machines |
| `--defense tamaraw` | Pluggable transport bridge | WFDefProxy applies constant-rate Tamaraw padding on the monitor↔bridge link |

`--padding` toggles a feature inside the Tor binary itself. `--defense tamaraw`
adds a separate `wfbridge0` host running [WFDefProxy](https://github.com/websitefingerprinting/wfdef)
and rewrites every monitor's torrc so its Tor process tunnels through that
bridge via the `tamaraw` pluggable transport.

### One-time setup for Tamaraw

Build WFDefProxy on the server and materialise the bridge keypair / cert.
Both steps are idempotent.

```bash
# Install Go and build obfs4proxy on the server (~5 min, first run only).
bash src/simulation/setup-wf-server.sh wfdef

# One-time bridge cert generation. Writes src/simulation/conf/tamaraw_cert.txt
# and stages ~/tamaraw-state-template/pt_state/ on the server for shadowctl
# to copy into every Tamaraw run.
bash src/simulation/setup-wf-server.sh wfdef-cert
```

The cert is the public part of the bridge's persistent keypair. It must be
known to every monitor's torrc *before* the bridge boots — Shadow starts all
hosts in parallel, so we can't rely on the bridge generating the cert at
runtime. The keypair is staged once on the server and re-used for every run.

### Running a Tamaraw experiment

```bash
cd src/simulation

# Smoke test: 5 pages × 20 visits × 2 monitors, ~30 min wall-clock.
python3 shadowctl.py run exp-tamaraw-smoke \
    --pages 5 --visits 20 --monitors 2 --defense tamaraw

# Full closed-world run matching exp-baseline-20, exp-padding-20, exp-reduced-20.
python3 shadowctl.py run exp-tamaraw-20 \
    --pages 20 --visits 80 --monitors 20 --defense tamaraw
```

The same `--pages`, `--visits`, `--monitors`, `--open-world`, `--correlation`
flags work unchanged. Tamaraw parameters are tunable:

```bash
python3 shadowctl.py run exp-tamaraw-tuned \
    --pages 20 --defense tamaraw \
    --tamaraw-rho-client 12 --tamaraw-rho-server 4 --tamaraw-nseg 200
```

`--padding` and `--defense` are orthogonal, but if you set both `shadowctl.py`
warns: Tamaraw's constant-rate scheduler dominates the on-wire packet pattern,
so CircuitPadding's contribution is largely masked.

### Verifying that Tamaraw is engaged

After pull-results, three quick checks:

1. Bridge bootstrapped:
   `grep -E "Bootstrapped 100|tamaraw" exp-tamaraw-smoke/results/shadow.data/hosts/wfbridge0/tor.*.stdout`
2. PT FSM transitions:
   `grep -E "state.*Start|state.*Padding" exp-tamaraw-smoke/results/shadow.data/hosts/wfbridge0/pt_state/obfs4proxy.log`
3. Constant-rate signature in monitor pcap — see Traffic-overhead measurement below.

### Traffic-overhead measurement

`src/ml/pcap_overhead.py` reads each monitor's pcap, segments it by the visit
windows recorded in `schedule.json`, and reports bytes / packets sent in each
direction per visit. Compare a defended run against a baseline to get the
defense's overhead percentage.

```bash
cd src/ml && source venv/bin/activate

# Per-visit summary of a single experiment.
python3 pcap_overhead.py \
    --schedule    ../simulation/exp-tamaraw-20/shadow.config.schedule.json \
    --shadow-data ../simulation/exp-tamaraw-20/results/shadow.data/

# Compare against a baseline (overhead vs. exp-baseline-20).
python3 pcap_overhead.py \
    --schedule    ../simulation/exp-tamaraw-20/shadow.config.schedule.json \
    --shadow-data ../simulation/exp-tamaraw-20/results/shadow.data/ \
    --baseline-schedule    ../simulation/exp-baseline-20/shadow.config.schedule.json \
    --baseline-shadow-data ../simulation/exp-baseline-20/results/shadow.data/

# Emit per-visit CSV for plotting.
python3 pcap_overhead.py \
    --schedule    ../simulation/exp-tamaraw-20/shadow.config.schedule.json \
    --shadow-data ../simulation/exp-tamaraw-20/results/shadow.data/ \
    --csv tamaraw_overhead.csv
```

The script also works on baseline / Circuit-Padding runs — useful for putting
all four defense rows in the same overhead table.

## Technical Notes

- **Adversary model:** ISP-level passive observer (sees encrypted Tor traffic at the client)
- **Closed-world scenario:** Classifier knows the set of possible pages
- **Same data for train+test:** WFlib splits the dataset (81% train, 9% valid, 10% test)
- **wget2 flags:** `--page-requisites --max-threads=30` creates realistic multi-stream traffic
  patterns matching Tor Browser behavior (validated by Jansen & Wails 2023)
- **DF input:** Direction-only sequences (+1/-1, 5000 packets), no timing
- **NEWNYM:** Sends `SIGNAL NEWNYM` to Tor control port for circuit isolation between visits
- **Web server:** `zimsrv.py` — a tiny custom HTTP server (~100 lines)
  that wraps the `libzim` Python bindings. Runs under the dynamically-linked
  toolsenv Python so Shadow can `LD_PRELOAD` its shim into the process.

  Earlier attempts that didn't work:
  - **`zimply`** (Python library) — supports only the pre-v6 ZIM namespace
    format (`A/ArticleName`); modern Kiwix ZIMs (2022+) store articles at
    flat paths, so every request 404s.
  - **`kiwix-serve`** (from kiwix-tools) — handles modern ZIMs correctly,
    but the prebuilt binary is **statically linked**, which Shadow rejects
    (it needs to inject its shim via `LD_PRELOAD`, which only works with
    dynamically-linked ELFs). Building kiwix-serve from source with
    dynamic linking is possible but adds a large dependency footprint.

## Traffic Correlation Attack (End-to-End)

In addition to the Website Fingerprinting (WF) attack, the pipeline supports a
simplified **end-to-end traffic correlation attack**.

### Adversary Model

The adversary controls (or observes) traffic at both ends of a Tor circuit:
- **Entry side:** encrypted traffic between the client and the guard relay
  (captured via monitor pcaps, same as the WF attack)
- **Exit side:** cleartext HTTP traffic between the exit relay and the
  destination (captured via exit relay pcaps, enabled with `--correlation`)

The adversary's goal: given an entry-side flow and an exit-side flow, determine
whether they belong to the same Tor circuit.

### Approach: Pcap-based Statistical Correlation

Instead of patching Tor's source code to log circuit IDs (which would require
the unreleased `tor-gwf` binary or deep Tor internals knowledge), we use a
simplified pcap-based approach:

1. **Capture pcaps on both sides.** Monitor pcaps (entry) are already captured.
   The `--correlation` flag additionally enables pcap capture on 5 exit relays.
2. **Segment by time window.** Each 30-second fetch window has exactly one
   page load from one monitor (entry side). On the exit side, traffic to the
   matching zimserver port during the same window corresponds to the same circuit.
3. **Bin packet timestamps.** Divide each 30-second window into 100ms bins
   and count packets per bin on both sides.
4. **Compute correlation.** Pearson, cosine similarity, and cross-correlation
   between the entry and exit bin vectors. High correlation = same circuit.
5. **Generate ROC curves.** True pairs (same circuit) vs false pairs (random
   mismatched entry/exit flows). Report AUC and TPR at low FPR thresholds.

### Why This Works (and Its Limitations)

**Why it works:** Tor relays forward cells with minimal buffering. A burst of
packets entering the circuit at the guard appears (with some delay) as a burst
leaving at the exit. This timing correlation survives Tor's encryption because
Tor does not add significant timing noise — unless Circuit Padding is enabled.

**Limitations (document in thesis):**
- No true circuit ID ground truth — we match entry/exit flows by timing window
  + destination port heuristic
- Our one-page-at-a-time setup means minimal circuit multiplexing at the entry,
  which makes correlation easier than in a real scenario with concurrent tabs
- Shadow's deterministic simulated network has lower latency variance than real
  Tor, which also inflates correlation accuracy
- Statistical correlation only (Pearson, cosine, cross-correlation) — no learned
  correlators like DeepCorr (Sun et al. 2018)
- We only capture pcaps on 5 of 22 exit relays to limit disk/RAM usage; circuits
  using other exits produce no exit-side data

### Running a Correlation Experiment

```bash
# Generate URLs if needed
bash src/simulation/setup-wf-server.sh urls 20

# Run with correlation mode (enables exit relay pcaps)
cd src/simulation
python3 shadowctl.py run exp-corr --pages 20 --visits 50 --correlation --padding off

# Wait for completion, pull results
python3 shadowctl.py status --name exp-corr
python3 shadowctl.py pull-results --name exp-corr

# Run correlation analysis
cd ../ml
python3 correlation.py \
    --schedule ../simulation/exp-corr/shadow.config.schedule.json \
    --shadow-data ../simulation/exp-corr/results/shadow.data/ \
    --output results/correlation/ \
    -v
```

Output in `results/correlation/`:
- `roc_curves.pdf/svg/png` — ROC curves for all three metrics
- `score_distributions.pdf/svg/png` — histograms of true vs false pair scores
- `correlation_results.json` — AUC, TPR@FPR=0.01, TPR@FPR=0.001
- `roc_data.csv` — raw data for custom plotting

### Comparing with Circuit Padding

Run two correlation experiments (same pages/visits, different padding):

```bash
python3 shadowctl.py run exp-corr-off --pages 20 --visits 50 --correlation --padding off
python3 shadowctl.py run exp-corr-on  --pages 20 --visits 50 --correlation --padding on
```

Then compare the ROC curves: padding ON should produce lower AUC (harder to
correlate) because padding inserts dummy packets that add noise to the timing
signal.
