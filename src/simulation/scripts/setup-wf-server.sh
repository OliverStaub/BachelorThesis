#!/bin/bash
# setup-wf-server.sh — Set up WF experiment dependencies on shadowsrv-001.
#
# Builds wget2 with SOCKS patch, installs zimply, copies helper scripts.
#
# Run from your laptop:
#   bash src/simulation/scripts/setup-wf-server.sh

set -euo pipefail

SSH_HOST="projectadmin@shadowsrv-001.prod.projects.ls.eee.intern"
REMOTE_BASE="/home/projectadmin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

step() { echo ">>> $1"; }
ok()   { echo "  OK: $1"; }

ssh_cmd() { ssh -o BatchMode=yes -o ConnectTimeout=10 "$SSH_HOST" "$1"; }

# ── 1. Build wget2 with SOCKS patch ─────────────────────────────────────────
step "Building wget2 with SOCKS patch..."

scp "${REPO_ROOT}/explainwf-popets2023/wget2/socks.patch" "${SSH_HOST}:${REMOTE_BASE}/socks.patch"

if ssh_cmd "test -f ${REMOTE_BASE}/wget2_noinstall" 2>/dev/null; then
    ok "wget2_noinstall already exists"
else
    ssh_cmd "bash -c '
        cd ${REMOTE_BASE}
        sudo apt-get update -qq
        sudo apt-get install -y -qq git autoconf automake libtool pkg-config \
            libgnutls28-dev libpcre2-dev flex texinfo gettext autopoint \
            libnghttp2-dev libbrotli-dev libzstd-dev 2>/dev/null || true
        if [ ! -d wget2-src ]; then
            git clone https://gitlab.com/gnuwget/wget2.git wget2-src
            cd wget2-src && git checkout edfd08 && git am ../socks.patch
        else
            cd wget2-src
        fi
        ./bootstrap && ./configure && make -j\$(nproc)
        cp src/wget2_noinstall ${REMOTE_BASE}/wget2_noinstall
        chmod +x ${REMOTE_BASE}/wget2_noinstall
    '" 2>&1
    ok "wget2_noinstall built"
fi

# ── 2. Install zimply ───────────────────────────────────────────────────────
step "Installing zimply..."
ssh_cmd "bash -c 'source ${REMOTE_BASE}/toolsenv/bin/activate && pip install zimply'" 2>&1
ok "zimply installed"

# ── 3. Copy helper scripts ──────────────────────────────────────────────────
step "Copying newnym.py and zimsrv.py..."
scp "${SCRIPT_DIR}/newnym.py"  "${SSH_HOST}:${REMOTE_BASE}/newnym.py"

# zimsrv.py needs to be on the server for the zimserver Shadow host
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
ok "Scripts copied"

# ── 4. Copy URL list ────────────────────────────────────────────────────────
step "Copying urls.txt..."
scp "${REPO_ROOT}/explainwf-popets2023/data/urls.txt" "${SSH_HOST}:${REMOTE_BASE}/urls.txt"
ok "urls.txt copied"

# ── 5. Check Wikipedia ZIM ──────────────────────────────────────────────────
step "Checking Wikipedia ZIM data..."
if ssh_cmd "test -f ${REMOTE_BASE}/wikidata/wikipedia_en_all_maxi.zim" 2>/dev/null; then
    ok "Wikipedia ZIM present"
else
    echo ""
    echo "  ZIM file not found. SSH in and download it:"
    echo "    mkdir -p ${REMOTE_BASE}/wikidata && cd ${REMOTE_BASE}/wikidata"
    echo "    wget https://dumps.wikimedia.org/other/kiwix/zim/wikipedia/wikipedia_en_all_maxi_2023-10.zim"
    echo "    mv wikipedia_en_all_maxi_2023-10.zim wikipedia_en_all_maxi.zim"
    echo "    echo '<html><head><title>{title}</title></head><body>{content}</body></html>' > template.html"
    echo ""
fi

echo ""
echo "Done. Next: generate a WF config with generate-wf-config.py"
