#!/bin/bash
# run_df.sh — End-to-end DF classifier pipeline
#
# Converts data, splits it, trains the DF classifier, and evaluates.
#
# Usage:
#   # Train on 2023 explainwf data (cell traces):
#   ./run_df.sh --explainwf
#
#   # Train on your own Shadow pcap data:
#   ./run_df.sh --pcap /path/to/wfclient1.pcap --log /path/to/wf-fetch.stdout
#
#   # Just evaluate an existing model:
#   ./run_df.sh --test-only --dataset MyData

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"
WFLIB_DIR="${SCRIPT_DIR}/wflib"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Defaults
DATASET_NAME="CW"
SEQ_LEN=5000
EPOCHS=30
BATCH_SIZE=128
LR="2e-3"
DEVICE="cpu"
MODE=""

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Data source (choose one):"
    echo "  --explainwf              Use 2023 explainwf cell trace data"
    echo "  --pcap FILE --log FILE   Use Shadow pcap + fetch log"
    echo "  --npz FILE               Use pre-converted .npz file"
    echo ""
    echo "Options:"
    echo "  --dataset NAME    Dataset name (default: CW)"
    echo "  --epochs N        Training epochs (default: 30)"
    echo "  --batch-size N    Batch size (default: 128)"
    echo "  --device DEV      Device: cpu, cuda, cuda:0 (default: cpu)"
    echo "  --seq-len N       Sequence length (default: 5000)"
    echo "  --test-only       Skip training, just evaluate"
    echo "  -h, --help        Show this help"
    exit 0
}

# Parse arguments
SCHEDULE_FILE=""
SHADOW_DATA=""
NPZ_FILE=""
TEST_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --explainwf) MODE="explainwf"; shift ;;
        --pcap) MODE="pcap"; shift ;;
        --schedule) SCHEDULE_FILE="$2"; shift 2 ;;
        --shadow-data) SHADOW_DATA="$2"; shift 2 ;;
        --npz) NPZ_FILE="$2"; MODE="npz"; shift 2 ;;
        --dataset) DATASET_NAME="$2"; shift 2 ;;
        --epochs) EPOCHS="$2"; shift 2 ;;
        --batch-size) BATCH_SIZE="$2"; shift 2 ;;
        --device) DEVICE="$2"; shift 2 ;;
        --seq-len) SEQ_LEN="$2"; shift 2 ;;
        --test-only) TEST_ONLY=true; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

# Activate venv
if [ -d "${VENV_DIR}" ]; then
    source "${VENV_DIR}/bin/activate"
else
    echo "Error: Virtual environment not found at ${VENV_DIR}"
    echo "Run: python3 -m venv ${VENV_DIR} && source ${VENV_DIR}/bin/activate && pip install torch numpy scikit-learn"
    exit 1
fi

echo "========================================"
echo "  DF Website Fingerprinting Pipeline"
echo "========================================"
echo "Dataset: ${DATASET_NAME}"
echo "Device: ${DEVICE}"
echo "Mode: ${MODE:-not specified}"
echo ""

# Step 1: Convert data to .npz
DATASETS_DIR="${WFLIB_DIR}/datasets"
NPZ_PATH="${DATASETS_DIR}/${DATASET_NAME}.npz"

if [ "${MODE}" = "explainwf" ]; then
    echo ">>> Step 1: Converting explainwf cell traces to npz..."
    TRACES_DIR="${REPO_ROOT}/explainwf-popets2023/data/fidelity/tornet-net_0.25-load_2.0"
    URLS_FILE="${REPO_ROOT}/explainwf-popets2023/data/urls.txt"

    TRACE_FILES=""
    for run in 1 2 3 4 5 6; do
        TRACE_FILES="${TRACE_FILES} ${TRACES_DIR}/run${run}/wget2-traces.log.xz"
    done

    python3 "${SCRIPT_DIR}/explainwf_to_npz.py" \
        --traces ${TRACE_FILES} \
        --urls "${URLS_FILE}" \
        --output "${NPZ_PATH}" \
        --direction-only \
        --seq-len "${SEQ_LEN}"

elif [ "${MODE}" = "pcap" ]; then
    echo ">>> Step 1: Converting pcap to npz..."
    if [ -z "${SCHEDULE_FILE}" ] || [ -z "${SHADOW_DATA}" ]; then
        echo "Error: --schedule and --shadow-data are both required with --pcap"
        exit 1
    fi
    python3 "${SCRIPT_DIR}/pcap_to_npz.py" \
        --schedule "${SCHEDULE_FILE}" \
        --shadow-data "${SHADOW_DATA}" \
        --output "${NPZ_PATH}" \
        --seq-len "${SEQ_LEN}"

elif [ "${MODE}" = "npz" ]; then
    echo ">>> Step 1: Copying npz file..."
    mkdir -p "${DATASETS_DIR}"
    cp "${NPZ_FILE}" "${NPZ_PATH}"

else
    if [ -f "${NPZ_PATH}" ]; then
        echo ">>> Step 1: Using existing ${NPZ_PATH}"
    else
        echo "Error: No data source specified. Use --explainwf, --pcap, or --npz"
        exit 1
    fi
fi

# Step 2: Split dataset
SPLIT_DIR="${DATASETS_DIR}/${DATASET_NAME}"
if [ ! -f "${SPLIT_DIR}/train.npz" ]; then
    echo ""
    echo ">>> Step 2: Splitting dataset (81/9/10 train/valid/test)..."
    cd "${WFLIB_DIR}"
    python3 exp/dataset_process/dataset_split.py --dataset "${DATASET_NAME}"
else
    echo ""
    echo ">>> Step 2: Split already exists, skipping"
fi

# Step 3: Train DF
cd "${WFLIB_DIR}"
CKP_FILE="./checkpoints/${DATASET_NAME}/DF/max_f1.pth"

if [ "${TEST_ONLY}" = true ]; then
    echo ""
    echo ">>> Step 3: Skipping training (--test-only)"
elif [ -f "${CKP_FILE}" ]; then
    echo ""
    echo ">>> Step 3: Model checkpoint already exists at ${CKP_FILE}, skipping training"
    echo "    Delete it to retrain, or use --test-only to just evaluate"
else
    echo ""
    echo ">>> Step 3: Training DF classifier (${EPOCHS} epochs)..."
    python3 -u exp/train.py \
        --dataset "${DATASET_NAME}" \
        --model DF \
        --device "${DEVICE}" \
        --feature DIR \
        --seq_len "${SEQ_LEN}" \
        --train_epochs "${EPOCHS}" \
        --batch_size "${BATCH_SIZE}" \
        --learning_rate "${LR}" \
        --optimizer Adamax \
        --num_workers 0 \
        --eval_metrics Accuracy Precision Recall F1-score \
        --save_metric F1-score \
        --save_name max_f1
fi

# Step 4: Test DF
echo ""
echo ">>> Step 4: Evaluating DF classifier..."
RESULTS_DIR="./logs/${DATASET_NAME}/DF"
mkdir -p "${RESULTS_DIR}"

python3 -u exp/test.py \
    --dataset "${DATASET_NAME}" \
    --model DF \
    --device "${DEVICE}" \
    --feature DIR \
    --seq_len "${SEQ_LEN}" \
    --batch_size 256 \
    --num_workers 0 \
    --eval_metrics Accuracy Precision Recall F1-score \
    --load_name max_f1

echo ""
echo "========================================"
echo "  Results"
echo "========================================"
RESULT_FILE="${RESULTS_DIR}/result.json"
if [ -f "${RESULT_FILE}" ]; then
    python3 -c "import json; r=json.load(open('${RESULT_FILE}')); [print(f'  {k}: {v:.4f}') for k,v in r.items()]"
else
    echo "  Results file not found at ${RESULT_FILE}"
fi
echo "========================================"
