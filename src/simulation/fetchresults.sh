#!/usr/bin/env bash
set -euo pipefail

# Configuration
SERVER="projectadmin@shadowsrv-001.prod.projects.ls.eee.intern"
REMOTE_DIR="/home/projectadmin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create timestamp directory
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
RESULTS_DIR="$SCRIPT_DIR/$TIMESTAMP"

echo "=== Creating results directory: $RESULTS_DIR ==="
mkdir -p "$RESULTS_DIR"

echo "=== Downloading shadow.yaml ==="
scp "$SERVER:$REMOTE_DIR/shadow.yaml" "$RESULTS_DIR/shadow.yaml" || echo "Warning: shadow.yaml not found"

echo "=== Downloading shadow.log ==="
scp "$SERVER:$REMOTE_DIR/shadow.log" "$RESULTS_DIR/shadow.log" || echo "Warning: shadow.log not found"

echo "=== Downloading shadow.data/ (this may take a while) ==="
scp -r "$SERVER:$REMOTE_DIR/shadow.data" "$RESULTS_DIR/shadow.data" || echo "Warning: shadow.data not found"

echo ""
echo "=== Done! ==="
echo "Results saved to: $RESULTS_DIR"
ls -la "$RESULTS_DIR"
