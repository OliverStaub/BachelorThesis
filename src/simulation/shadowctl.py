#!/usr/bin/env python3
"""
shadowctl.py — Remote control script for Shadow/Tor simulations
Runs from your laptop, manages simulations on shadowsrv-001 via SSH.

Usage:
    ./shadowctl.py download-data [--month 2025-01]
    ./shadowctl.py stage [--month 2025-01]
    ./shadowctl.py generate --scale 0.01 [--month 2025-01] [--name myexp]
    ./shadowctl.py pull-config --name myexp
    ./shadowctl.py push-config --name myexp
    ./shadowctl.py simulate --name myexp [--stop-time 15m]
    ./shadowctl.py status [--name myexp]
    ./shadowctl.py pull-results --name myexp [--dest ./results]
    ./shadowctl.py logs --name myexp [--tail 50]
    ./shadowctl.py list
"""

import argparse
import subprocess
import sys
import os
import shlex
from pathlib import Path
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────

SSH_HOST = "projectadmin@shadowsrv-001.prod.projects.ls.eee.intern"
REMOTE_BASE = "/home/projectadmin/tornettools"
REMOTE_TOOLS_VENV = "/home/projectadmin/toolsenv/bin/activate"
LOCAL_WORKSPACE = Path.cwd()

# Tor metrics data URLs (template with {month} and {last_day})
DATA_URLS = {
    "consensuses": "https://collector.torproject.org/archive/relay-descriptors/consensuses/consensuses-{month}.tar.xz",
    "server_descriptors": "https://collector.torproject.org/archive/relay-descriptors/server-descriptors/server-descriptors-{month}.tar.xz",
    "userstats": "https://metrics.torproject.org/userstats-relay-country.csv",
    "onionperf": "https://collector.torproject.org/archive/onionperf/onionperf-{month}.tar.xz",
    "bandwidth": "https://metrics.torproject.org/bandwidth.csv?start={month}-01&end={month}-{last_day}",
}

TMODEL_REPO = "https://github.com/tmodel-ccs2018/tmodel-ccs2018.github.io.git"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def ssh_cmd(cmd, capture=False, check=True, stream=False):
    """Run a command on the remote server via SSH."""
    full = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", SSH_HOST, cmd]
    if stream:
        proc = subprocess.Popen(full, stdout=sys.stdout, stderr=sys.stderr)
        proc.wait()
        return proc
    elif capture:
        return subprocess.run(full, capture_output=True, text=True, check=check)
    else:
        return subprocess.run(full, check=check)


def scp_to_remote(local_path, remote_path):
    """Copy a file/dir from local to remote."""
    subprocess.run(
        ["scp", "-r", str(local_path), f"{SSH_HOST}:{remote_path}"],
        check=True,
    )


def scp_from_remote(remote_path, local_path):
    """Copy a file/dir from remote to local."""
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["scp", "-r", f"{SSH_HOST}:{remote_path}", str(local_path)],
        check=True,
    )


def rsync_from_remote(remote_path, local_path, excludes=None):
    """Rsync from remote to local (more efficient for large dirs)."""
    Path(local_path).mkdir(parents=True, exist_ok=True)
    cmd = ["rsync", "-avz", "--progress"]
    if excludes:
        for ex in excludes:
            cmd.extend(["--exclude", ex])
    cmd.extend([f"{SSH_HOST}:{remote_path}/", str(local_path) + "/"])
    subprocess.run(cmd, check=True)


def remote_activate_and_run(commands):
    """Build a bash command that activates the venv, adds tor to PATH, and runs commands."""
    inner = " && ".join(commands)
    return (
        f"bash -lc '"
        f"source {REMOTE_TOOLS_VENV} && "
        f"export PATH=$PATH:{REMOTE_BASE}/tor/src/core/or:{REMOTE_BASE}/tor/src/app:{REMOTE_BASE}/tor/src/tools && "
        f"{inner}'"
    )


def get_last_day(month_str):
    """Get the last day of a month given YYYY-MM string."""
    import calendar
    year, month = map(int, month_str.split("-"))
    return str(calendar.monthrange(year, month)[1])


def get_sim_dir(name):
    return f"{REMOTE_BASE}/{name}"


def get_data_dir(month):
    # Data files live directly in REMOTE_BASE (flat layout matching existing setup)
    return REMOTE_BASE


def get_staging_dir():
    # Staging output goes directly into REMOTE_BASE
    return REMOTE_BASE


def print_header(msg):
    print(f"\n{'═' * 60}")
    print(f"  {msg}")
    print(f"{'═' * 60}\n")


def print_step(msg):
    print(f"  → {msg}")


def print_ok(msg):
    print(f"  ✓ {msg}")


def print_err(msg):
    print(f"  ✗ {msg}", file=sys.stderr)

# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_download_data(args):
    """Download Tor metrics data on the remote server."""
    month = args.month
    last_day = get_last_day(month)
    data_dir = get_data_dir(month)

    print_header(f"Downloading Tor metrics data for {month}")

    # Create data directory
    ssh_cmd(f"mkdir -p {data_dir}")

    # Check what's already downloaded
    result = ssh_cmd(f"ls {data_dir}/", capture=True, check=False)
    existing = result.stdout.strip() if result.returncode == 0 else ""

    downloads = []

    if f"consensuses-{month}" not in existing:
        url = DATA_URLS["consensuses"].format(month=month)
        downloads.append(f"cd {data_dir} && wget -q --show-progress -O - '{url}' | tar xJ")
        print_step(f"Will download consensuses for {month}")
    else:
        print_ok(f"Consensuses for {month} already present")

    if f"server-descriptors-{month}" not in existing:
        url = DATA_URLS["server_descriptors"].format(month=month)
        downloads.append(f"cd {data_dir} && wget -q --show-progress -O - '{url}' | tar xJ")
        print_step(f"Will download server descriptors for {month}")
    else:
        print_ok(f"Server descriptors for {month} already present")

    if "userstats-relay-country.csv" not in existing:
        url = DATA_URLS["userstats"]
        downloads.append(f"cd {data_dir} && wget -q --show-progress '{url}'")
        print_step("Will download userstats")
    else:
        print_ok("Userstats already present")

    if f"onionperf-{month}" not in existing:
        url = DATA_URLS["onionperf"].format(month=month)
        downloads.append(f"cd {data_dir} && wget -q --show-progress -O - '{url}' | tar xJ")
        print_step(f"Will download onionperf for {month}")
    else:
        print_ok(f"OnionPerf for {month} already present")

    if f"bandwidth-{month}.csv" not in existing:
        url = DATA_URLS["bandwidth"].format(month=month, last_day=last_day)
        downloads.append(f"cd {data_dir} && wget -q --show-progress -O 'bandwidth-{month}.csv' '{url}'")
        print_step(f"Will download bandwidth data for {month}")
    else:
        print_ok(f"Bandwidth data for {month} already present")

    # Clone tmodel if not present
    tmodel_dir = f"{REMOTE_BASE}/tmodel-ccs2018.github.io"
    result = ssh_cmd(f"test -d {tmodel_dir}", capture=True, check=False)
    if result.returncode != 0:
        downloads.append(f"cd {REMOTE_BASE} && git clone {TMODEL_REPO}")
        print_step("Will clone tmodel repo")
    else:
        print_ok("tmodel repo already present")

    if downloads:
        print(f"\n  Running {len(downloads)} download(s)... this may take a while.\n")
        for dl in downloads:
            print_step(f"Running: {dl[:80]}...")
            ssh_cmd(dl, stream=True)
        print_ok("All downloads complete")
    else:
        print_ok("Nothing to download")


def cmd_stage(args):
    """Run tornettools stage on the remote server."""
    month = args.month
    data_dir = get_data_dir(month)
    staging_dir = get_staging_dir()

    print_header(f"Staging Tor network data for {month}")

    ssh_cmd(f"mkdir -p {staging_dir}")

    # Check if staging files already exist for this month
    result = ssh_cmd(f"ls {staging_dir}/relayinfo_staging_*{month}* 2>/dev/null", capture=True, check=False)
    if result.returncode == 0 and result.stdout.strip():
        print_ok(f"Staging files for {month} already exist")
        if not args.force:
            print("  Use --force to re-stage")
            return
        print_step("Force re-staging requested")

    # Find geoip path (check common locations including local tor build)
    geoip_check = ssh_cmd(
        f"test -f {REMOTE_BASE}/tor/src/config/geoip && echo {REMOTE_BASE}/tor/src/config/geoip || "
        "(test -f ~/.local/share/tor/geoip && echo ~/.local/share/tor/geoip || "
        "(test -f /usr/share/tor/geoip && echo /usr/share/tor/geoip || echo ''))",
        capture=True
    )
    geoip_path = geoip_check.stdout.strip()
    geoip_arg = f"--geoip_path {geoip_path}" if geoip_path else ""

    tmodel_dir = f"{REMOTE_BASE}/tmodel-ccs2018.github.io"

    stage_cmd = (
        f"cd {staging_dir} && tornettools stage "
        f"{data_dir}/consensuses-{month} "
        f"{data_dir}/server-descriptors-{month} "
        f"{data_dir}/userstats-relay-country.csv "
        f"{tmodel_dir} "
        f"--onionperf_data_path {data_dir}/onionperf-{month} "
        f"--bandwidth_data_path {data_dir}/bandwidth-{month}.csv "
        f"{geoip_arg}"
    )

    print_step("Running tornettools stage (this takes several minutes)...")
    cmd = remote_activate_and_run([stage_cmd])
    ssh_cmd(cmd, stream=True)
    print_ok("Staging complete")


def cmd_generate(args):
    """Run tornettools generate on the remote server."""
    month = args.month
    name = args.name or f"tornet-{args.scale}-{month}"
    staging_dir = get_staging_dir()
    sim_dir = get_sim_dir(name)
    tmodel_dir = f"{REMOTE_BASE}/tmodel-ccs2018.github.io"

    print_header(f"Generating network: {name} (scale={args.scale})")

    # Find staging files
    result = ssh_cmd(f"ls {staging_dir}/relayinfo_staging_*{month}*.json 2>/dev/null | head -1", capture=True, check=False)
    relay_info = result.stdout.strip()
    if not relay_info:
        print_err(f"No staging files found for {month}. Run 'stage' first.")
        sys.exit(1)

    result = ssh_cmd(f"ls {staging_dir}/userinfo_staging_*{month}*.json 2>/dev/null | head -1", capture=True, check=False)
    user_info = result.stdout.strip()

    result = ssh_cmd(f"ls {staging_dir}/networkinfo_staging.gml 2>/dev/null | head -1", capture=True, check=False)
    network_info = result.stdout.strip()

    if not all([relay_info, user_info, network_info]):
        print_err("Missing staging files. Run 'stage' first.")
        sys.exit(1)

    # Build generate command
    seed_arg = f"--seed {args.seed}" if args.seed else ""
    gen_cmd = (
        f"tornettools {seed_arg} generate "
        f"{relay_info} "
        f"{user_info} "
        f"{network_info} "
        f"{tmodel_dir} "
        f"--network_scale {args.scale} "
        f"--prefix {sim_dir}"
    )

    print_step(f"Generating to {sim_dir}...")
    cmd = remote_activate_and_run([gen_cmd])
    ssh_cmd(cmd, stream=True)
    print_ok(f"Network generated: {name}")
    print(f"\n  To edit the shadow config before simulation:")
    print(f"    ./shadowctl.py pull-config --name {name}")
    print(f"    # edit the config locally")
    print(f"    ./shadowctl.py push-config --name {name}")
    print(f"    ./shadowctl.py simulate --name {name}")


def cmd_pull_config(args):
    """Pull the shadow config file to local machine for editing."""
    name = args.name
    sim_dir = get_sim_dir(name)
    local_dir = LOCAL_WORKSPACE / name

    print_header(f"Pulling config for: {name}")

    local_dir.mkdir(parents=True, exist_ok=True)

    # Pull shadow config
    config_file = f"{sim_dir}/shadow.config.yaml"
    local_config = local_dir / "shadow.config.yaml"

    print_step(f"Downloading shadow.config.yaml → {local_config}")
    scp_from_remote(config_file, str(local_config))

    # Also pull the torrc files for reference
    conf_dir = f"{sim_dir}/conf"
    local_conf = local_dir / "conf"
    print_step(f"Downloading conf/ → {local_conf}")
    scp_from_remote(conf_dir, str(local_conf))

    print_ok(f"Config files saved to {local_dir}")
    print(f"\n  Edit {local_config}")
    print(f"  Then run: ./shadowctl.py push-config --name {name}")


def cmd_push_config(args):
    """Push the edited shadow config back to the server."""
    name = args.name
    sim_dir = get_sim_dir(name)
    local_dir = LOCAL_WORKSPACE / name
    local_config = local_dir / "shadow.config.yaml"

    print_header(f"Pushing config for: {name}")

    if not local_config.exists():
        print_err(f"Config file not found: {local_config}")
        print_err(f"Run 'pull-config --name {name}' first.")
        sys.exit(1)

    # Backup remote config
    print_step("Backing up remote config...")
    ssh_cmd(f"cp {sim_dir}/shadow.config.yaml {sim_dir}/shadow.config.yaml.bak", check=False)

    # Push config
    print_step(f"Uploading {local_config}...")
    scp_to_remote(str(local_config), f"{sim_dir}/shadow.config.yaml")

    # Push conf/ if it exists locally (in case torrc files were edited)
    local_conf = local_dir / "conf"
    if local_conf.exists():
        print_step("Uploading conf/ directory...")
        scp_to_remote(str(local_conf), f"{sim_dir}/conf")

    print_ok("Config pushed to server")


def cmd_simulate(args):
    """Start a Shadow simulation in the background (fire-and-forget)."""
    name = args.name
    sim_dir = get_sim_dir(name)

    print_header(f"Starting simulation: {name}")

    # Optionally patch stop_time
    if args.stop_time:
        print_step(f"Setting stop_time to {args.stop_time}")
        ssh_cmd(f"sed -i 's/stop_time:.*/stop_time: \"{args.stop_time}\"/' {sim_dir}/shadow.config.yaml")

    # Check if simulation is already running
    result = ssh_cmd(f"test -f {sim_dir}/sim.pid && kill -0 $(cat {sim_dir}/sim.pid) 2>/dev/null && echo running", capture=True, check=False)
    if "running" in result.stdout:
        print_err("A simulation is already running for this experiment!")
        print(f"  Check status with: ./shadowctl.py status --name {name}")
        sys.exit(1)

    # Build the simulation wrapper script that runs in background
    nproc = args.nproc or "$(nproc)"
    wrapper = f"""#!/bin/bash
set -euo pipefail
source {REMOTE_TOOLS_VENV}
export PATH=$PATH:{REMOTE_BASE}/tor/src/core/or:{REMOTE_BASE}/tor/src/app:{REMOTE_BASE}/tor/src/tools:$HOME/.local/bin
cd {sim_dir}

echo "=== Simulation started at $(date -u) ===" > sim.log
echo "PID: $$" >> sim.log
echo $$ > sim.pid

# Run tornettools simulate
tornettools simulate \\
    --args "--parallelism={nproc} --seed={args.sim_seed} --template-directory=shadow.data.template --progress=true" \\
    {sim_dir} >> sim.log 2>&1

RC=$?
echo "=== Simulation finished at $(date -u) with exit code $RC ===" >> sim.log
echo $RC > sim.exitcode
rm -f sim.pid

# Auto-parse if simulation succeeded
if [ $RC -eq 0 ]; then
    echo "=== Starting parse at $(date -u) ===" >> sim.log
    tornettools parse {sim_dir} >> sim.log 2>&1
    echo "=== Parse finished at $(date -u) ===" >> sim.log
fi
"""

    # Write wrapper script to remote
    escaped = wrapper.replace("'", "'\\''")
    ssh_cmd(f"cat > {sim_dir}/run_sim.sh << 'SIMEOF'\n{wrapper}\nSIMEOF")
    ssh_cmd(f"chmod +x {sim_dir}/run_sim.sh")

    # Launch in background with nohup
    print_step("Launching simulation in background...")
    ssh_cmd(f"nohup bash {sim_dir}/run_sim.sh > /dev/null 2>&1 &")

    # Wait a moment and verify it started
    import time
    time.sleep(2)
    result = ssh_cmd(f"test -f {sim_dir}/sim.pid && cat {sim_dir}/sim.pid", capture=True, check=False)
    if result.returncode == 0 and result.stdout.strip():
        pid = result.stdout.strip()
        print_ok(f"Simulation running with PID {pid}")
    else:
        print_ok("Simulation launched (checking startup...)")

    print(f"\n  Monitor with: ./shadowctl.py status --name {name}")
    print(f"  View logs:    ./shadowctl.py logs --name {name}")
    print(f"  Pull results: ./shadowctl.py pull-results --name {name}")


def cmd_status(args):
    """Check simulation status."""
    if args.name:
        names = [args.name]
    else:
        # List all experiments
        result = ssh_cmd(f"ls -d {REMOTE_BASE}/experiments/*/ 2>/dev/null | xargs -I{{}} basename {{}}", capture=True, check=False)
        names = [n for n in result.stdout.strip().split("\n") if n]
        if not names:
            print("No experiments found.")
            return

    print_header("Simulation Status")
    fmt = "  {:<30s} {:<12s} {:<20s} {}"
    print(fmt.format("EXPERIMENT", "STATUS", "RUNTIME", "DETAILS"))
    print(f"  {'─' * 80}")

    for name in names:
        sim_dir = get_sim_dir(name)

        # Check if running
        result = ssh_cmd(
            f"test -f {sim_dir}/sim.pid && kill -0 $(cat {sim_dir}/sim.pid) 2>/dev/null && echo running || echo not_running",
            capture=True, check=False
        )
        is_running = "running" in result.stdout.strip().split("\n")[0]

        # Check exit code
        result = ssh_cmd(f"cat {sim_dir}/sim.exitcode 2>/dev/null", capture=True, check=False)
        exitcode = result.stdout.strip() if result.returncode == 0 else None

        # Check shadow progress
        result = ssh_cmd(
            f"grep -o 'progress.*' {sim_dir}/sim.log 2>/dev/null | tail -1",
            capture=True, check=False
        )
        progress = result.stdout.strip() if result.returncode == 0 else ""

        # Also check shadow.log for progress
        if not progress:
            result = ssh_cmd(
                f"tail -5 {sim_dir}/shadow.log 2>/dev/null | grep -o '[0-9]\\+\\.[0-9]\\+%' | tail -1",
                capture=True, check=False
            )
            progress = result.stdout.strip() if result.returncode == 0 else ""

        # Get runtime from sim.log
        result = ssh_cmd(
            f"head -1 {sim_dir}/sim.log 2>/dev/null | grep -o 'at .*' | sed 's/at //' | sed 's/ ===//'",
            capture=True, check=False
        )
        start_time = result.stdout.strip() if result.returncode == 0 else ""

        if is_running:
            status = "RUNNING"
            details = progress or "started"
        elif exitcode == "0":
            status = "COMPLETED"
            details = "success"
        elif exitcode:
            status = "FAILED"
            details = f"exit code {exitcode}"
        else:
            # Check if config exists but sim never ran
            result = ssh_cmd(f"test -f {sim_dir}/shadow.config.yaml", capture=True, check=False)
            if result.returncode == 0:
                status = "READY"
                details = "not yet started"
            else:
                status = "UNKNOWN"
                details = ""

        print(fmt.format(name, status, start_time[:20] if start_time else "", details))


def cmd_logs(args):
    """View simulation logs."""
    name = args.name
    sim_dir = get_sim_dir(name)

    print_header(f"Logs for: {name}")

    if args.follow:
        print_step("Following sim.log (Ctrl+C to stop)...")
        try:
            ssh_cmd(f"tail -f {sim_dir}/sim.log", stream=True)
        except KeyboardInterrupt:
            print()
    else:
        n = args.tail
        print_step(f"Last {n} lines of sim.log:")
        ssh_cmd(f"tail -n {n} {sim_dir}/sim.log 2>/dev/null || echo 'No sim.log found'", stream=True)
        print()
        print_step(f"Last {n} lines of shadow.log:")
        ssh_cmd(f"tail -n {n} {sim_dir}/shadow.log 2>/dev/null || echo 'No shadow.log found'", stream=True)


def cmd_pull_results(args):
    """Pull simulation results back to local machine."""
    name = args.name
    sim_dir = get_sim_dir(name)
    local_dir = Path(args.dest) / name if args.dest else LOCAL_WORKSPACE / name / "results"

    print_header(f"Pulling results for: {name}")

    local_dir.mkdir(parents=True, exist_ok=True)

    # Pull plot data
    print_step("Pulling tornet.plot.data/...")
    scp_from_remote(f"{sim_dir}/tornet.plot.data", str(local_dir / "tornet.plot.data"))

    # Pull tor metrics json
    print_step("Pulling tor_metrics*.json...")
    result = ssh_cmd(f"ls {sim_dir}/tor_metrics_*.json 2>/dev/null", capture=True, check=False)
    for f in result.stdout.strip().split("\n"):
        if f:
            scp_from_remote(f, str(local_dir / Path(f).name))

    # Pull shadow config for reference
    print_step("Pulling shadow.config.yaml...")
    scp_from_remote(f"{sim_dir}/shadow.config.yaml", str(local_dir / "shadow.config.yaml"))

    # Pull sim log
    print_step("Pulling sim.log...")
    scp_from_remote(f"{sim_dir}/sim.log", str(local_dir / "sim.log"))

    # Pull any pcap files if they exist
    result = ssh_cmd(f"find {sim_dir}/shadow.data -name '*.pcap' 2>/dev/null | head -5", capture=True, check=False)
    pcaps = result.stdout.strip()
    if pcaps:
        pcap_dir = local_dir / "pcaps"
        pcap_dir.mkdir(exist_ok=True)
        print_step(f"Found pcap files, pulling to {pcap_dir}...")
        for pcap_path in pcaps.split("\n"):
            if pcap_path.strip():
                fname = Path(pcap_path).name
                # Preserve the host directory name
                parts = pcap_path.split("/")
                host_idx = next((i for i, p in enumerate(parts) if p == "hosts"), None)
                if host_idx and host_idx + 1 < len(parts):
                    host_name = parts[host_idx + 1]
                    dest = pcap_dir / f"{host_name}_{fname}"
                else:
                    dest = pcap_dir / fname
                scp_from_remote(pcap_path, str(dest))

    # Pull compressed analysis files
    for pattern in ["tgen.analysis.json*", "oniontrace.analysis.json*"]:
        result = ssh_cmd(f"ls {sim_dir}/{pattern} 2>/dev/null", capture=True, check=False)
        for f in result.stdout.strip().split("\n"):
            if f:
                print_step(f"Pulling {Path(f).name}...")
                scp_from_remote(f, str(local_dir / Path(f).name))

    print_ok(f"Results saved to {local_dir}")


def cmd_list(args):
    """List all experiments on the server."""
    print_header("Experiments on server")

    result = ssh_cmd(
        f"for d in {REMOTE_BASE}/tornet-*/; do "
        f"  [ -d \"$d\" ] || continue; "
        f"  name=$(basename $d); "
        f"  size=$(du -sh $d 2>/dev/null | cut -f1); "
        f"  echo \"$name $size\"; "
        f"done 2>/dev/null",
        capture=True, check=False
    )

    if not result.stdout.strip():
        print("  No experiments found.")
        return

    fmt = "  {:<40s} {:>10s}"
    print(fmt.format("NAME", "SIZE"))
    print(f"  {'─' * 52}")
    for line in result.stdout.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 2:
            print(fmt.format(parts[0], parts[1]))

    # Also show staging files and data archives
    print()
    result = ssh_cmd(
        f"ls -lh {REMOTE_BASE}/relayinfo_staging_*.json {REMOTE_BASE}/userinfo_staging_*.json 2>/dev/null | awk '{{print $NF, $5}}'",
        capture=True, check=False
    )
    if result.stdout.strip():
        print("  Staging files:")
        for line in result.stdout.strip().split("\n"):
            if line:
                print(f"    {line}")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Remote control for Shadow/Tor simulations on shadowsrv-001",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # download-data
    p = sub.add_parser("download-data", help="Download Tor metrics data on server")
    p.add_argument("--month", default="2025-01", help="Month to download (YYYY-MM)")
    p.set_defaults(func=cmd_download_data)

    # stage
    p = sub.add_parser("stage", help="Run tornettools stage on server")
    p.add_argument("--month", default="2025-01", help="Month to stage (YYYY-MM)")
    p.add_argument("--force", action="store_true", help="Re-stage even if files exist")
    p.set_defaults(func=cmd_stage)

    # generate
    p = sub.add_parser("generate", help="Generate a Shadow/Tor network config")
    p.add_argument("--scale", type=float, required=True, help="Network scale (e.g. 0.01, 0.1)")
    p.add_argument("--month", default="2025-01", help="Which staged month to use")
    p.add_argument("--name", default=None, help="Experiment name (default: tornet-{scale}-{month})")
    p.add_argument("--seed", type=int, default=None, help="PRNG seed for tornettools")
    p.set_defaults(func=cmd_generate)

    # pull-config
    p = sub.add_parser("pull-config", help="Pull shadow config to laptop for editing")
    p.add_argument("--name", required=True, help="Experiment name")
    p.set_defaults(func=cmd_pull_config)

    # push-config
    p = sub.add_parser("push-config", help="Push edited config back to server")
    p.add_argument("--name", required=True, help="Experiment name")
    p.set_defaults(func=cmd_push_config)

    # simulate
    p = sub.add_parser("simulate", help="Start simulation in background")
    p.add_argument("--name", required=True, help="Experiment name")
    p.add_argument("--stop-time", default=None, help="Override simulation stop time (e.g. '15m', '1h')")
    p.add_argument("--nproc", default=None, help="Number of parallel threads (default: nproc)")
    p.add_argument("--sim-seed", type=int, default=1, help="Shadow simulation seed")
    p.set_defaults(func=cmd_simulate)

    # status
    p = sub.add_parser("status", help="Check simulation status")
    p.add_argument("--name", default=None, help="Specific experiment (default: show all)")
    p.set_defaults(func=cmd_status)

    # logs
    p = sub.add_parser("logs", help="View simulation logs")
    p.add_argument("--name", required=True, help="Experiment name")
    p.add_argument("--tail", type=int, default=50, help="Number of lines to show")
    p.add_argument("-f", "--follow", action="store_true", help="Follow log output")
    p.set_defaults(func=cmd_logs)

    # pull-results
    p = sub.add_parser("pull-results", help="Pull simulation results to laptop")
    p.add_argument("--name", required=True, help="Experiment name")
    p.add_argument("--dest", default=None, help="Local destination directory")
    p.set_defaults(func=cmd_pull_results)

    # list
    p = sub.add_parser("list", help="List all experiments on server")
    p.set_defaults(func=cmd_list)

    args = parser.parse_args()
    try:
        args.func(args)
    except subprocess.CalledProcessError as e:
        print_err(f"Command failed with exit code {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  Interrupted.")
        sys.exit(130)


if __name__ == "__main__":
    main()