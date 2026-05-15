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
#   bash src/simulation/setup-wf-server.sh wfdef        # install Go + build WFDefProxy (obfs4proxy w/ tamaraw)
#   bash src/simulation/setup-wf-server.sh wfdef-cert   # one-time: pre-generate bridge pt_state + cert

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

# ─── Phase 2: Install kiwix-tools + libzim + copy helper scripts ────────────
phase_copy() {
    # libzim is needed locally by generate-urls.py (samples articles from the
    # ZIM). It lives in the toolsenv venv alongside tornettools.
    step "Installing libzim in toolsenv (for generate-urls.py)..."
    ssh_cmd "bash -lc 'source ${REMOTE_BASE}/toolsenv/bin/activate && pip install --quiet libzim'"
    ok "libzim installed"

    # kiwix-serve replaces the older zimply library, which doesn't handle
    # modern namespace-free ZIM files (v6+).
    step "Copying helper scripts..."
    scp "${SCRIPT_DIR}/newnym.py"        "${SSH_HOST}:${REMOTE_BASE}/newnym.py"
    scp "${SCRIPT_DIR}/zimsrv.py"        "${SSH_HOST}:${REMOTE_BASE}/zimsrv.py"
    scp "${SCRIPT_DIR}/generate-urls.py" "${SSH_HOST}:${REMOTE_BASE}/generate-urls.py"
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

# ─── Phase 4: Build WFDefProxy (Tamaraw pluggable transport) ────────────────
#
# WFDefProxy implements Tamaraw (constant-rate link padding) as a Tor pluggable
# transport. It is a fork of obfs4proxy written in Go. The binary lands at
# ~/obfs4proxy_tamaraw on the server; tor.bridge.torrc and the client torrc
# reference that absolute path.
#
# wfdef commit pin (record this for reproducibility):
#   github.com/websitefingerprinting/wfdef, branch v2
#   pinned via WFDEF_COMMIT below.
WFDEF_REPO="https://github.com/websitefingerprinting/wfdef.git"
WFDEF_BRANCH="v2"
WFDEF_COMMIT=""   # leave empty to track branch tip; set to a SHA to pin
GO_VERSION="1.21.5"
GO_TARBALL_URL="https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz"

phase_wfdef() {
    step "Building WFDefProxy (obfs4proxy with Tamaraw transport)..."

    if ssh_cmd "test -x ${REMOTE_BASE}/obfs4proxy_tamaraw" 2>/dev/null; then
        ok "obfs4proxy_tamaraw already exists at ${REMOTE_BASE}/obfs4proxy_tamaraw"
        return 0
    fi

    if ! ssh_cmd "bash -c '
        set -e
        cd ${REMOTE_BASE}

        # Install Go ${GO_VERSION} locally (apt may have an older version).
        if [ ! -x ${REMOTE_BASE}/.local/go/bin/go ]; then
            echo \"Installing Go ${GO_VERSION} to ~/.local/go ...\"
            mkdir -p ${REMOTE_BASE}/.local
            wget -q -O /tmp/go.tar.gz ${GO_TARBALL_URL}
            tar -C ${REMOTE_BASE}/.local -xzf /tmp/go.tar.gz
            rm -f /tmp/go.tar.gz
        fi
        export PATH=${REMOTE_BASE}/.local/go/bin:\$PATH

        # Clone wfdef.
        if [ ! -d wfdef-src ]; then
            git clone -b ${WFDEF_BRANCH} ${WFDEF_REPO} wfdef-src
        fi
        cd wfdef-src
        if [ -n \"${WFDEF_COMMIT}\" ]; then
            git checkout ${WFDEF_COMMIT}
        fi

        # Build obfs4proxy (contains all transports).
        go build -o obfs4proxy/obfs4proxy ./obfs4proxy

        # Stage the binary at a stable path.
        cp obfs4proxy/obfs4proxy ${REMOTE_BASE}/obfs4proxy_tamaraw
        chmod +x ${REMOTE_BASE}/obfs4proxy_tamaraw
    '"; then
        echo ""
        echo "  BUILD FAILED. Common causes:" >&2
        echo "    - no network access from the server to go.dev / github.com" >&2
        echo "    - Go failed to fetch modules (try wfdef-cert again after a retry)" >&2
        exit 1
    fi
    ok "obfs4proxy_tamaraw built at ${REMOTE_BASE}/obfs4proxy_tamaraw"
}

# ─── Phase 5: Pre-generate bridge pt_state and extract cert ─────────────────
#
# WFDefProxy's tamaraw transport derives a per-bridge cert from a persistent
# keypair stored in pt_state/tamaraw_state.json. Shadow boots all hosts in
# parallel, but the monitor torrcs must reference the bridge cert *before* the
# bridge boots — so we materialise the keypair once here and bake the cert
# into the repo at src/simulation/conf/tamaraw_cert.txt.
#
# The pt_state/ dir itself is staged at ~/tamaraw-state-template/pt_state/ on
# the server. shadowctl.py copies it into each run's
# shadow.data.template/hosts/wfbridge0/pt_state/ before simulation start.
phase_wfdef_cert() {
    step "Generating bridge pt_state + cert (one-time)..."

    if ! ssh_cmd "test -x ${REMOTE_BASE}/obfs4proxy_tamaraw"; then
        echo "  ERROR: obfs4proxy_tamaraw not found. Run '$0 wfdef' first." >&2
        exit 1
    fi

    if ssh_cmd "test -f ${REMOTE_BASE}/tamaraw-state-template/cert.txt" 2>/dev/null; then
        ok "Bridge cert already exists at ${REMOTE_BASE}/tamaraw-state-template/cert.txt"
        # Re-pull anyway so the local copy stays in sync.
    else
        # Boot obfs4proxy once in a throwaway tor-config that mimics the real
        # bridge torrc. obfs4proxy writes pt_state/tamaraw_bridgeline.txt with
        # the cert string, then we kill it.
        if ! ssh_cmd "bash -c '
            set -e
            STAGE=${REMOTE_BASE}/tamaraw-state-template
            rm -rf \$STAGE
            mkdir -p \$STAGE/tor-config/pt_state

            # Minimal bridge torrc — same ServerTransportOptions as the real run,
            # so the resulting cert is the one the real bridge would have used.
            cat > \$STAGE/tor-config/torrc <<EOF
DataDirectory \$STAGE/tor-config
ORPort 9001 IPv4Only
SocksPort 0
DirPort 0
BridgeRelay 1
AssumeReachable 1
PublishServerDescriptor 0
ExitPolicy reject *:*
ExtORPort auto
ServerTransportListenAddr tamaraw 0.0.0.0:34001
ServerTransportPlugin tamaraw exec ${REMOTE_BASE}/obfs4proxy_tamaraw
ServerTransportOptions tamaraw rho-client=12 rho-server=4 nseg=200
Log notice stdout
EOF

            # Run real tor briefly so it spawns obfs4proxy as a managed PT.
            # obfs4proxy writes pt_state/tamaraw_bridgeline.txt on first boot.
            export PATH=\$PATH:${REMOTE_BASE}/tor/src/core/or:${REMOTE_BASE}/tor/src/app:${REMOTE_BASE}/tor/src/tools
            cd \$STAGE/tor-config

            timeout 20 ~/.local/bin/tor -f torrc > tor.log 2>&1 || true

            # WFDefProxy v2 names the bridgeline file after its internal
            # \"defconn\" abstraction, shared across all five defenses (FRONT,
            # Tamaraw, etc.). The transport name in torrc is still \"tamaraw\".
            BRIDGELINE=\$(ls pt_state/*_bridgeline.txt 2>/dev/null | head -1)
            if [ -z \"\$BRIDGELINE\" ]; then
                echo \"ERROR: no *_bridgeline.txt generated in pt_state/. Tor log tail:\" >&2
                tail -40 tor.log >&2
                ls -la pt_state/ >&2 || true
                exit 1
            fi

            # Extract cert (the token after cert= in the bridge line).
            CERT=\$(grep -oP \"cert=\\K[^[:space:]]+\" \"\$BRIDGELINE\" | head -1)
            if [ -z \"\$CERT\" ]; then
                echo \"ERROR: could not parse cert from \$BRIDGELINE:\" >&2
                cat \"\$BRIDGELINE\" >&2
                exit 1
            fi
            echo \"\$CERT\" > \$STAGE/cert.txt

            # Move pt_state up to a stable location and drop tor-config noise.
            mv pt_state \$STAGE/pt_state
            rm -rf \$STAGE/tor-config

            echo \"Bridge cert: \$CERT\"
        '"; then
            echo "  ERROR: cert generation failed." >&2
            exit 1
        fi
    fi

    step "Pulling cert back to laptop..."
    LOCAL_CERT="${REPO_ROOT}/src/simulation/conf/tamaraw_cert.txt"
    mkdir -p "$(dirname "${LOCAL_CERT}")"
    scp "${SSH_HOST}:${REMOTE_BASE}/tamaraw-state-template/cert.txt" "${LOCAL_CERT}"
    ok "Local: ${LOCAL_CERT} ($(wc -c < "${LOCAL_CERT}") bytes)"
    echo "  Cert: $(cat "${LOCAL_CERT}")"
}

# ─── Dispatch ───────────────────────────────────────────────────────────────
case "$PHASE" in
    build)      phase_build ;;
    copy)       phase_copy ;;
    urls)       phase_urls ;;
    wfdef)      phase_wfdef ;;
    wfdef-cert) phase_wfdef_cert ;;
    all)        phase_build && phase_copy ;;
    *)          echo "Usage: $0 [build|copy|urls [N]|wfdef|wfdef-cert|all]" >&2; exit 1 ;;
esac

echo ""
echo "Done. Next: run the full simulation workflow:"
echo "   python3 src/simulation/shadowctl.py run <name>"
