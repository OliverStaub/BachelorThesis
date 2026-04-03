#!/usr/bin/env bash
set -euo pipefail

# Configuration
SERVER="projectadmin@shadowsrv-001.prod.projects.ls.eee.intern"
REMOTE_DIR="/home/projectadmin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHADOW_YAML="$SCRIPT_DIR/shadow.yaml"
TGEN_CLIENT="$SCRIPT_DIR/tgen.client.graphml.xml"
TGEN_SERVER="$SCRIPT_DIR/tgen.server.graphml.xml"

# Check if required files exist locally
if [[ ! -f "$SHADOW_YAML" ]]; then
    echo "Error: shadow.yaml not found at $SHADOW_YAML"
    exit 1
fi
if [[ ! -f "$TGEN_CLIENT" ]]; then
    echo "Error: tgen.client.graphml.xml not found at $TGEN_CLIENT"
    exit 1
fi
if [[ ! -f "$TGEN_SERVER" ]]; then
    echo "Error: tgen.server.graphml.xml not found at $TGEN_SERVER"
    exit 1
fi

echo "=== Cleaning up previous simulation on server ==="
ssh "$SERVER" "rm -rf $REMOTE_DIR/shadow.data $REMOTE_DIR/shadow.log $REMOTE_DIR/shadow.yaml $REMOTE_DIR/tgen.client.graphml.xml $REMOTE_DIR/tgen.server.graphml.xml"

echo "=== Uploading configuration files to server ==="
scp "$SHADOW_YAML" "$SERVER:$REMOTE_DIR/shadow.yaml"
scp "$TGEN_CLIENT" "$SERVER:$REMOTE_DIR/tgen.client.graphml.xml"
scp "$TGEN_SERVER" "$SERVER:$REMOTE_DIR/tgen.server.graphml.xml"

echo "=== Starting Shadow simulation ==="
ssh "$SERVER" "cd $REMOTE_DIR && nohup ~/.local/bin/shadow shadow.yaml > shadow.log 2>&1 &"

echo ""
echo "=== Simulation started in background ==="
echo "Monitor progress with: ssh $SERVER 'tail -f $REMOTE_DIR/shadow.log'"
echo "Check if running with: ssh $SERVER 'pgrep -a shadow'"
echo ""
echo "When complete, run: ./fetchresults.sh"
