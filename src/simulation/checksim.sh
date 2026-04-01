#!/usr/bin/env bash
set -euo pipefail

# Configuration
SERVER="projectadmin@shadowsrv-001.prod.projects.ls.eee.intern"
REMOTE_DIR="/home/projectadmin"

echo "=== Checking if Shadow is running ==="
if ssh "$SERVER" "pgrep -x shadow > /dev/null 2>&1"; then
    echo "Status: RUNNING"
    echo ""
    echo "Process info:"
    ssh "$SERVER" "ps aux | grep '[s]hadow'" || true
else
    echo "Status: NOT RUNNING"
fi

echo ""
echo "=== Last 20 lines of shadow.log ==="
ssh "$SERVER" "tail -20 $REMOTE_DIR/shadow.log 2>/dev/null" || echo "(no log file found)"

echo ""
echo "=== shadow.data size ==="
ssh "$SERVER" "du -sh $REMOTE_DIR/shadow.data 2>/dev/null" || echo "(no data directory found)"
