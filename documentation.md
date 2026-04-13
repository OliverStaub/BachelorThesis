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
python3 -m venv venv && source venv/bin/activate
pip install numpy torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install tqdm pandas scikit-learn einops timm pytorch-metric-learning captum pyyaml dpkt
pip install -e wflib/
```

### 2. Server setup

```bash
# Build wget2 + install zimply + copy scripts to shadowsrv-001
bash src/simulation/scripts/setup-wf-server.sh

# You also need Wikipedia ZIM data on the server (see script output)
```

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
