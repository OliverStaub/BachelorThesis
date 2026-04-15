# Documentation: Website Fingerprinting Pipeline

Complete pipeline for Deep Fingerprinting (DF) attacks in Shadow-simulated Tor networks.
Part of Oliver Staub's bachelor thesis at HSLU.

## Architecture

```
Shadow Simulation                        ML Pipeline
┌──────────────────────────┐            ┌─────────────────────────┐
│ zimserver0               │            │                         │
│  (Wikipedia via ZIM)     │            │ pcap_to_npz.py          │
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
├── ml/
│   ├── explainwf_to_npz.py     # Convert 2023 cell traces → WFlib .npz
│   ├── pcap_to_npz.py          # Convert Shadow pcaps → WFlib .npz
│   ├── run_df.sh               # End-to-end: convert → split → train → test
│   ├── venv/                   # Python environment
│   └── wflib/                  # WFlib submodule (PyTorch DF classifier)
├── simulation/
│   ├── shadowctl.py            # Remote simulation control (SSH to shadowsrv)
│   ├── scripts/
│   │   ├── generate-wf-config.py  # Add WF nodes to shadow config
│   │   ├── setup-wf-server.sh     # Build wget2, install deps on server
│   │   └── newnym.py              # Send SIGNAL NEWNYM to Tor
│   └── exp1/                   # First experiment (base config + results)
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

**Step 2b — build wget2, install zimply, copy helper scripts (automated).**

```bash
# From your laptop:
bash src/simulation/scripts/setup-wf-server.sh
```

The script has three phases you can run individually:

```bash
bash src/simulation/scripts/setup-wf-server.sh build   # only build wget2
bash src/simulation/scripts/setup-wf-server.sh copy    # only copy scripts + install zimply
bash src/simulation/scripts/setup-wf-server.sh urls    # generate urls.txt (needs ZIM, see 2c)
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

# Rename so zimsrv.py finds it (it expects exactly wikipedia_en_all_maxi.zim)
mv wikipedia_en_simple_all_maxi_2026-02.zim wikipedia_en_all_maxi.zim

# Minimal HTML template required by zimply
echo '<html><head><title>{title}</title></head><body>{content}</body></html>' > template.html

exit
```

**Step 2d — Generate your own `urls.txt` (recommended).**

Instead of reusing the paper's hardcoded list (which references articles that
may not exist in Simple English Wikipedia), sample random articles directly
from your ZIM file. The setup script does this for you:

```bash
# From your laptop — default: 100 pages starting at port 8000
bash src/simulation/scripts/setup-wf-server.sh urls

# Pass a number as the second argument for a custom page count:
bash src/simulation/scripts/setup-wf-server.sh urls 20
```

This runs `generate-urls.py` on the server (using `libzim` to enumerate
articles in the ZIM), then pulls the generated file to your laptop at
`src/simulation/generated/urls.txt`. Every title is guaranteed to exist in the
ZIM, so no visits will 404.

## Quick Start: Train DF on 2023 Reference Data

No simulation needed — uses existing data from Jansen & Wails 2023:

```bash
cd src/ml && source venv/bin/activate
./run_df.sh --explainwf
```

## Running Your Own Simulation

### 1. Generate WF shadow config

Start from your existing tornettools config (0.01 scale) and add WF nodes:

```bash
source src/ml/venv/bin/activate

python3 src/simulation/scripts/generate-wf-config.py \
    --base-config src/simulation/exp1/shadow.config.yaml \
    --urls explainwf-popets2023/data/urls.txt \
    --output src/simulation/exp2/shadow.config.yaml \
    --num-monitors 5 \
    --num-pages 20 \
    --visits-per-page 50 \
    --visit-interval 30
```

This creates:
- `shadow.config.yaml` — Shadow config with 5 monitors + zimserver added
- `shadow.config.schedule.json` — Visit schedule for pcap segmentation

**What each monitor does:** Fetches 4 pages (20 pages / 5 monitors), one at a time,
50 visits each, 30 seconds per visit. wget2 fetches the page with all embedded
resources (images, CSS) using 30 threads through Tor's SOCKS proxy. NEWNYM resets
the circuit between visits.

### 2. Push config and run simulation

```bash
cd src/simulation

# Create experiment directory on server
python3 shadowctl.py generate --scale 0.01 --name exp2
# OR just push the config directly:
python3 shadowctl.py push-config --name exp2

# Start simulation (takes ~2 hours for 20 pages × 50 visits)
python3 shadowctl.py simulate --name exp2

# Monitor progress
python3 shadowctl.py status --name exp2
python3 shadowctl.py logs --name exp2
```

### 3. Pull results and convert

```bash
python3 shadowctl.py pull-results --name exp2

# Convert pcaps to WFlib format
cd ../ml && source venv/bin/activate
python3 pcap_to_npz.py \
    --schedule ../simulation/exp2/shadow.config.schedule.json \
    --shadow-data ../simulation/exp2/results/shadow.data/ \
    --output wflib/datasets/Exp2.npz
```

### 4. Train and evaluate DF

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

## Technical Notes

- **Adversary model:** ISP-level passive observer (sees encrypted Tor traffic at the client)
- **Closed-world scenario:** Classifier knows the set of possible pages
- **Same data for train+test:** WFlib splits the dataset (81% train, 9% valid, 10% test)
- **wget2 flags:** `--page-requisites --max-threads=30` creates realistic multi-stream traffic
  patterns matching Tor Browser behavior (validated by Jansen & Wails 2023)
- **DF input:** Direction-only sequences (+1/-1, 5000 packets), no timing
- **NEWNYM:** Sends `SIGNAL NEWNYM` to Tor control port for circuit isolation between visits
