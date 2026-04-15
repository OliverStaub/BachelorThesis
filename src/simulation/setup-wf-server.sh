#!/bin/bash
# setup-wf-server.sh — Set up WF experiment dependencies on shadowsrv-001.
#
# Prerequisites (install manually via SSH on the server — requires sudo).
# Copy the whole line as-is; do NOT add backslashes or linebreaks:
#
#   sudo apt-get update && sudo apt-get install -y git autoconf automake libtool libtool-bin pkg-config libgnutls28-dev libpcre2-dev flex texinfo gettext autopoint libnghttp2-dev libbrotli-dev libzstd-dev lzip
#
# Two phases:
#   1. Build wget2 with the SOCKS patch (no sudo needed).
#   2. Install zimply (in the tornettools venv) and copy helper scripts.
#
# Usage:
#   bash src/simulation/setup-wf-server.sh              # full setup (build + copy)
#   bash src/simulation/setup-wf-server.sh build        # only build wget2
#   bash src/simulation/setup-wf-server.sh copy         # only copy scripts + install zimply
#   bash src/simulation/setup-wf-server.sh urls [N]     # generate urls.txt with N pages (default 100)

set -euo pipefail

SSH_HOST="projectadmin@shadowsrv-001.prod.projects.ls.eee.intern"
REMOTE_BASE="/home/projectadmin"
# SCRIPT_DIR = src/simulation/ ; REPO_ROOT = repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PHASE="${1:-all}"
NUM_PAGES="${2:-100}"

step() { echo ""; echo ">>> $1"; }
ok()   { echo "  OK: $1"; }
warn() { echo "  WARN: $1"; }

ssh_cmd() { ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH_HOST" "$1"; }

# ─── Phase 1: Build wget2 ───────────────────────────────────────────────────
phase_build() {
    step "Building wget2 with SOCKS patch..."

    if ssh_cmd "test -x ${REMOTE_BASE}/wget2_noinstall" 2>/dev/null; then
        ok "wget2_noinstall already exists at ${REMOTE_BASE}/wget2_noinstall"
        return 0
    fi

    # Build (no sudo needed). The SOCKS patch is fetched directly from the
    # upstream explainwf-popets2023 GitHub repo on the server.
    # If ssh_cmd returns non-zero we exit explicitly — `&&` chaining in the
    # dispatcher suppresses bash -e inside this function.
    PATCH_URL="https://raw.githubusercontent.com/explainwf-popets2023/explainwf-popets2023.github.io/main/wget2/socks.patch"
    if ! ssh_cmd "bash -c '
        set -e
        cd ${REMOTE_BASE}

        # Clone + patch wget2 if not already done
        if [ ! -d wget2-src ]; then
            wget -q -O socks.patch ${PATCH_URL}
            git clone https://gitlab.com/gnuwget/wget2.git wget2-src
            cd wget2-src
            git checkout edfd08
            git am ../socks.patch
        else
            cd wget2-src
        fi

        # Build. Prefer libtoolize; fall back to glibtoolize.
        export LIBTOOLIZE=\$(command -v libtoolize || command -v glibtoolize)
        if [ -z \"\$LIBTOOLIZE\" ]; then
            echo \"ERROR: libtoolize not found. Install build dependencies first\" >&2
            echo \"  (see README comments at the top of this script).\" >&2
            exit 1
        fi

        ./bootstrap && ./configure && make -j\$(nproc)

        # The wget2 binary ends up at src/wget2_noinstall
        if [ ! -f src/wget2_noinstall ]; then
            echo \"ERROR: build produced no src/wget2_noinstall\" >&2
            exit 1
        fi
        cp src/wget2_noinstall ${REMOTE_BASE}/wget2_noinstall
        chmod +x ${REMOTE_BASE}/wget2_noinstall
    '"; then
        echo ""
        echo "  BUILD FAILED. Likely cause: missing build dependencies." >&2
        echo "  SSH to the server and run the prerequisites command shown" >&2
        echo "  at the top of $0 — make sure to paste it as ONE line." >&2
        exit 1
    fi
    ok "wget2_noinstall built"
}

# ─── Phase 2: Install zimply + copy helper scripts ──────────────────────────
phase_copy() {
    step "Installing zimply + libzim in toolsenv..."
    ssh_cmd "bash -lc 'source ${REMOTE_BASE}/toolsenv/bin/activate && pip install --quiet zimply libzim'"
    ok "zimply + libzim installed"

    step "Copying helper scripts..."
    scp "${SCRIPT_DIR}/newnym.py"        "${SSH_HOST}:${REMOTE_BASE}/newnym.py"
    scp "${SCRIPT_DIR}/generate-urls.py" "${SSH_HOST}:${REMOTE_BASE}/generate-urls.py"

    cat > /tmp/zimsrv.py << 'PYEOF'
#!/usr/bin/env python3
import os
from zimply import ZIMServer
root, ip, port = os.getenv('ZIMROOT'), os.getenv('ZIMIP'), os.getenv('ZIMPORT')
ZIMServer(f"{root}/wikipedia_en_all_maxi.zim", index_file=f"{root}/index.idx",
          template=f"{root}/template.html", ip_address=ip, port=int(port), encoding="utf-8")
PYEOF
    scp /tmp/zimsrv.py "${SSH_HOST}:${REMOTE_BASE}/zimsrv.py"
    rm /tmp/zimsrv.py
    ok "newnym.py, zimsrv.py, generate-urls.py copied"

    step "Checking Wikipedia ZIM data..."
    if ssh_cmd "test -f ${REMOTE_BASE}/wikidata/wikipedia_en_all_maxi.zim"; then
        ok "Wikipedia ZIM present"
    else
        warn "ZIM file not found. SSH in and run:"
        echo ""
        echo "    mkdir -p ${REMOTE_BASE}/wikidata && cd ${REMOTE_BASE}/wikidata"
        echo "    wget https://dumps.wikimedia.org/other/kiwix/zim/wikipedia/wikipedia_en_simple_all_maxi_2026-02.zim"
        echo "    mv wikipedia_en_simple_all_maxi_2026-02.zim wikipedia_en_all_maxi.zim"
        echo "    echo '<html><head><title>{title}</title></head><body>{content}</body></html>' > template.html"
        echo ""
        echo "  (If the 2026-02 file is gone, check dumps.wikimedia.org for the current date.)"
        echo ""
        echo "  Then run:  $0 urls"
        return 0
    fi
}

# ─── Phase 3: Generate urls.txt from the ZIM ────────────────────────────────
phase_urls() {
    step "Checking ZIM is present on server..."
    if ! ssh_cmd "test -f ${REMOTE_BASE}/wikidata/wikipedia_en_all_maxi.zim"; then
        warn "ZIM file not found — download it first (see 'copy' phase output)"
        return 1
    fi
    ok "ZIM present"

    step "Generating urls.txt with ${NUM_PAGES} random articles..."
    ssh_cmd "bash -lc '
        source ${REMOTE_BASE}/toolsenv/bin/activate
        python3 ${REMOTE_BASE}/generate-urls.py \
            --zim ${REMOTE_BASE}/wikidata/wikipedia_en_all_maxi.zim \
            --num-pages ${NUM_PAGES} \
            --output ${REMOTE_BASE}/urls.txt
    '"
    ok "Server: ${REMOTE_BASE}/urls.txt generated"

    step "Pulling urls.txt back to laptop..."
    mkdir -p "${REPO_ROOT}/src/simulation/generated"
    scp "${SSH_HOST}:${REMOTE_BASE}/urls.txt" "${REPO_ROOT}/src/simulation/generated/urls.txt"
    ok "Local: src/simulation/generated/urls.txt"
}

# ─── Dispatch ───────────────────────────────────────────────────────────────
case "$PHASE" in
    build) phase_build ;;
    copy)  phase_copy ;;
    urls)  phase_urls ;;
    all)   phase_build && phase_copy ;;
    *)     echo "Usage: $0 [build|copy|urls [N]|all]" >&2; exit 1 ;;
esac

echo ""
echo "Done. Next: run the full simulation workflow:"
echo "   python3 src/simulation/shadowctl.py run <name>"
