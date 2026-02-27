#!/usr/bin/env bash
set -euo pipefail

echo "=== Installing Shadow dependencies ==="
sudo apt-get update
sudo apt-get install -y \
    cmake \
    findutils \
    libclang-dev \
    libc-dbg \
    libglib2.0-0 \
    libglib2.0-dev \
    make \
    netbase \
    python3 \
    python3-networkx \
    xz-utils \
    util-linux \
    gcc \
    g++ \
    curl \
    git

echo "=== Installing Rust ==="
if command -v rustc &>/dev/null; then
    echo "Rust already installed: $(rustc --version)"
else
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

echo "=== Configuring system limits ==="
sudo sysctl -w fs.nr_open=10485760
sudo sysctl -w fs.file-max=10485760
sudo sysctl -w vm.max_map_count=1073741824
sudo sysctl -w kernel.pid_max=4194304
sudo sysctl -w kernel.threads-max=4194304

# Persist across reboots
grep -q "fs.nr_open" /etc/sysctl.conf || echo "fs.nr_open = 10485760" | sudo tee -a /etc/sysctl.conf
grep -q "fs.file-max" /etc/sysctl.conf || echo "fs.file-max = 10485760" | sudo tee -a /etc/sysctl.conf
grep -q "vm.max_map_count" /etc/sysctl.conf || echo "vm.max_map_count = 1073741824" | sudo tee -a /etc/sysctl.conf
grep -q "kernel.pid_max" /etc/sysctl.conf || echo "kernel.pid_max = 4194304" | sudo tee -a /etc/sysctl.conf
grep -q "kernel.threads-max" /etc/sysctl.conf || echo "kernel.threads-max = 4194304" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Raise user limits
grep -q "soft nofile" /etc/security/limits.conf || {
    echo "* soft nofile 10485760" | sudo tee -a /etc/security/limits.conf
    echo "* hard nofile 10485760" | sudo tee -a /etc/security/limits.conf
    echo "* soft nproc unlimited" | sudo tee -a /etc/security/limits.conf
    echo "* hard nproc unlimited" | sudo tee -a /etc/security/limits.conf
}

echo "=== Cloning and building Shadow ==="
SHADOW_DIR="$HOME/shadow"
if [ -d "$SHADOW_DIR" ]; then
    echo "Shadow directory already exists, pulling latest..."
    cd "$SHADOW_DIR" && git pull
else
    git clone https://github.com/shadow/shadow.git "$SHADOW_DIR"
    cd "$SHADOW_DIR"
fi

./setup build --clean --test
./setup test
./setup install

# Ensure ~/.local/bin is in PATH
grep -q '.local/bin' "$HOME/.bashrc" || {
    echo 'export PATH="${PATH}:${HOME}/.local/bin"' >> "$HOME/.bashrc"
}

echo ""
echo "=== Done! ==="
echo "Run 'source ~/.bashrc' or open a new shell, then: shadow --help"