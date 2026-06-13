#!/usr/bin/env python3
"""
shadowctl.py — Remote control script for Shadow/Tor simulations
Runs from your laptop, manages simulations on shadowsrv-001 via SSH.

Usage:
    ./shadowctl.py run <name>                      # full workflow: generate + WF + push + simulate
    ./shadowctl.py download-data [--month 2025-01]
    ./shadowctl.py stage [--month 2025-01]
    ./shadowctl.py generate --scale 0.01 [--month 2025-01] [--name myexp]
    ./shadowctl.py pull-config --name myexp
    ./shadowctl.py push-config --name myexp
    ./shadowctl.py simulate --name myexp [--stop-time 15m]
    ./shadowctl.py status --name myexp [--tail 20]
    ./shadowctl.py pull-results --name myexp [--dest ./results]
    ./shadowctl.py logs --name myexp [--tail 50]
    ./shadowctl.py list
"""

import argparse
import shutil
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


def rsync_to_remote(local_path, remote_path, delete=False):
    """Rsync from local to remote — copies *contents* of local_path into
    remote_path. Trailing slashes on both ends are critical, otherwise scp/rsync
    nests the source directory inside the destination on each call.
    """
    cmd = ["rsync", "-az"]
    if delete:
        cmd.append("--delete")
    cmd.extend([str(local_path) + "/", f"{SSH_HOST}:{remote_path}/"])
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

    # Also pull the torrc files for reference.
    # CRITICAL: wipe local_conf first. `scp -r server:src dest` NESTS the
    # source into the destination when dest already exists as a directory
    # (creates dest/conf/conf/...). On re-runs this leaves a stale outer
    # conf/ from prior pulls that push-config then ships back to the server,
    # silently overwriting freshly-patched torrcs (e.g. Step 1b's authority
    # fingerprint rewrite). Wiping first guarantees scp creates conf/ at the
    # right level every time.
    conf_dir = f"{sim_dir}/conf"
    local_conf = local_dir / "conf"
    if local_conf.exists():
        shutil.rmtree(local_conf)
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

    # Push conf/ if it exists locally (in case torrc files were edited).
    # `scp -r src dst` nests `src` inside `dst` when `dst` already exists,
    # which on repeated pushes piles up conf/conf/conf/. So we wipe the remote
    # conf/ first; scp then recreates it cleanly at the right level.
    local_conf = local_dir / "conf"
    if local_conf.exists():
        print_step("Uploading conf/ directory...")
        ssh_cmd(f"rm -rf {sim_dir}/conf", check=False)
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
    # IMPORTANT: no `set -e` here. We want to capture the exit code of
    # tornettools and always run the cleanup block (write sim.exitcode,
    # remove sim.pid). With `set -e`, a tornettools failure kills the
    # shell before cleanup, leaving stale PID files and a misleading
    # "still running" status.
    wrapper = f"""#!/bin/bash
source {REMOTE_TOOLS_VENV}
export PATH=$PATH:{REMOTE_BASE}/tor/src/core/or:{REMOTE_BASE}/tor/src/app:{REMOTE_BASE}/tor/src/tools:$HOME/.local/bin
cd {sim_dir}

echo "=== Simulation started at $(date -u) ===" > sim.log
echo "PID: $$" >> sim.log
echo $$ > sim.pid

# Cleanup runs even if we're killed (SIGINT/SIGTERM).
cleanup() {{
    RC=${{RC:-1}}
    echo "=== Simulation finished at $(date -u) with exit code $RC ===" >> sim.log
    echo $RC > sim.exitcode
    rm -f sim.pid
}}
trap cleanup EXIT INT TERM

# Run tornettools simulate
tornettools simulate \\
    --args "--parallelism={nproc} --seed={args.sim_seed} --template-directory=shadow.data.template --progress=true" \\
    {sim_dir} >> sim.log 2>&1
RC=$?

# Auto-parse if simulation succeeded
if [ $RC -eq 0 ]; then
    echo "=== Starting parse at $(date -u) ===" >> sim.log
    tornettools parse {sim_dir} >> sim.log 2>&1
    echo "=== Parse finished at $(date -u) ===" >> sim.log
fi

exit $RC
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
    """Show simulation status + the last lines of sim.log."""
    name = args.name
    if not name:
        print_err("Please specify --name")
        sys.exit(1)

    sim_dir = get_sim_dir(name)

    # Is the wrapper process alive?
    result = ssh_cmd(
        f"test -f {sim_dir}/sim.pid && kill -0 $(cat {sim_dir}/sim.pid) 2>/dev/null && echo running || echo not_running",
        capture=True, check=False
    )
    is_running = "running" in result.stdout.strip().split("\n")[0]

    # Exit code (if it finished)
    result = ssh_cmd(f"cat {sim_dir}/sim.exitcode 2>/dev/null", capture=True, check=False)
    exitcode = result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None

    # Start time from sim.log first line
    result = ssh_cmd(
        f"head -1 {sim_dir}/sim.log 2>/dev/null",
        capture=True, check=False
    )
    first_line = result.stdout.strip() if result.returncode == 0 else ""

    # Status label
    if is_running:
        status = "RUNNING"
    elif exitcode == "0":
        status = "COMPLETED"
    elif exitcode is not None:
        status = f"FAILED (exit {exitcode})"
    else:
        # No pid, no exit code — check if config exists
        r = ssh_cmd(f"test -f {sim_dir}/shadow.config.yaml", capture=True, check=False)
        status = "READY (not started)" if r.returncode == 0 else "UNKNOWN"

    print_header(f"Simulation status: {name}")
    print(f"  Status:     {status}")
    if first_line:
        print(f"  Started:    {first_line}")

    # Tail sim.log so the user can see what's actually happening
    tail_n = args.tail
    print(f"\n  Last {tail_n} lines of sim.log:")
    print(f"  {'─' * 60}")
    ssh_cmd(f"tail -n {tail_n} {sim_dir}/sim.log 2>/dev/null | sed 's/^/  /'", stream=True)


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

    # Pull whatever standard outputs exist (skip missing ones gracefully).
    for remote_name, local_name in [
        ("shadow.config.yaml", "shadow.config.yaml"),
        ("sim.log", "sim.log"),
    ]:
        result = ssh_cmd(f"test -f {sim_dir}/{remote_name}", capture=True, check=False)
        if result.returncode == 0:
            print_step(f"Pulling {remote_name}...")
            scp_from_remote(f"{sim_dir}/{remote_name}", str(local_dir / local_name))

    # tornet.plot.data/ only exists after a successful tornettools parse
    result = ssh_cmd(f"test -d {sim_dir}/tornet.plot.data", capture=True, check=False)
    if result.returncode == 0:
        print_step("Pulling tornet.plot.data/...")
        scp_from_remote(f"{sim_dir}/tornet.plot.data", str(local_dir / "tornet.plot.data"))
    else:
        print("  (tornet.plot.data/ not found — skipping, parse may not have run)")

    # Pull pcap files preserving the shadow.data/hosts/<name>/ structure
    # so pcap_to_npz.py can find them by host name.
    result = ssh_cmd(
        f"find {sim_dir}/shadow.data -name '*.pcap' 2>/dev/null",
        capture=True, check=False,
    )
    pcaps = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
    if pcaps:
        print_step(f"Found {len(pcaps)} pcap file(s), pulling...")
        for pcap_path in pcaps:
            # Keep the path from "shadow.data/..." onward so the converter
            # can find files at shadow.data/hosts/<name>/*.pcap.
            parts = pcap_path.split("/")
            try:
                sd_idx = parts.index("shadow.data")
                rel_path = Path(*parts[sd_idx:])
            except ValueError:
                rel_path = Path("pcaps") / Path(pcap_path).name
            dest = local_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            scp_from_remote(pcap_path, str(dest))
        print_ok(f"Pcaps saved under {local_dir / 'shadow.data' / 'hosts'}/")
    else:
        print(f"  (No pcap files found on server — was pcap_enabled set?)")

    # Pull compressed analysis files
    for pattern in ["tgen.analysis.json*", "oniontrace.analysis.json*"]:
        result = ssh_cmd(f"ls {sim_dir}/{pattern} 2>/dev/null", capture=True, check=False)
        for f in result.stdout.strip().split("\n"):
            if f:
                print_step(f"Pulling {Path(f).name}...")
                scp_from_remote(f, str(local_dir / Path(f).name))

    print_ok(f"Results saved to {local_dir}")


# ─── Helper used by cmd_run ──────────────────────────────────────────────────

SIM_DIR_LOCAL = Path(__file__).resolve().parent            # src/simulation/
REPO_ROOT     = SIM_DIR_LOCAL.parent.parent                # repo root
WF_CONFIG_GEN = SIM_DIR_LOCAL / "generate-wf-config.py"
DEFAULT_URLS_FILE = SIM_DIR_LOCAL / "generated" / "urls.txt"


def _namespace(**kwargs):
    """Build a lightweight argparse-like namespace for passing to cmd_* functions."""
    class NS:
        pass
    ns = NS()
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def cmd_run(args):
    """
    Full workflow: generate base config → add WF nodes → push → simulate → status.

    Uses sensible defaults everywhere; override via flags if needed.
    """
    name = args.name
    # Match the path convention used by pull-config / push-config (CWD/<name>/),
    # so all three commands read and write the same file.
    local_exp_dir = LOCAL_WORKSPACE / name
    local_config = local_exp_dir / "shadow.config.yaml"

    print_header(f"Running full experiment workflow: {name}")
    print(f"  Scale:            {args.scale}")
    print(f"  Month:            {args.month}")
    print(f"  Monitors:         {args.monitors}")
    print(f"  Pages:            {args.pages}")
    print(f"  Visits per page:  {args.visits}")
    print(f"  Visit interval:   {args.visit_interval}s")
    print(f"  Circuit Padding:  {args.padding or 'Tor default (on)'}")
    print(f"  Defense (PT):     {args.defense}")
    if args.correlation_only:
        corr_str = f"ONLY (exit pcaps on {args.exit_pcap_relays} relays, no monitor pcaps)"
    elif args.correlation:
        corr_str = f"YES (exit pcaps on {args.exit_pcap_relays} relays + monitor pcaps)"
    else:
        corr_str = "no"
    print(f"  Correlation:      {corr_str}")
    print(f"  URLs file:        {args.urls}")

    urls_path = Path(args.urls)
    if not urls_path.exists():
        print_err(f"URLs file not found: {urls_path}")
        print("  Run:  bash src/simulation/scripts/setup-wf-server.sh urls <N>")
        sys.exit(1)

    # ── Step 1: Generate base config (tornettools) ─────────────────────
    # Wipe any prior server-side sim_dir first. tornettools generate
    # overwrites conf/ but does NOT touch shadow.data.template/hosts/<auth>/keys/.
    # Re-running over an existing dir leaves stale authority keypairs paired
    # with fresh fingerprints in tor.common.torrc, and every relay then fails
    # its TLS handshake with "Unexpected identity in router certificate".
    print_step("Step 1/5: Wipe remote sim dir + generate base tornettools config")
    sim_dir = get_sim_dir(name)
    ssh_cmd(f"rm -rf {sim_dir}", check=False)
    cmd_generate(_namespace(
        scale=args.scale, month=args.month, name=name, seed=None,
    ))

    # ── Step 1b: Fix authority fingerprints in tor.common.torrc ────────
    # tornettools generate writes DirServer lines whose RSA fingerprints
    # AND v3ident= tokens both DON'T match the keypairs it pre-stages in
    # shadow.data.template/hosts/4uthorityN/keys/. Background clients
    # tolerate this (they pick relays from the consensus, not from torrc),
    # but a pluggable-transport bridge bootstraps by connecting directly
    # to an authority's OR port — which fails the TLS handshake with
    # "Unexpected identity in router certificate" on RSA-fp mismatch,
    # and would later reject the consensus signature on v3ident mismatch.
    # Patch BOTH from the on-disk template files.
    print_step("Step 1b/5: Patch authority fingerprints in tor.common.torrc")
    torrc_path = f"{sim_dir}/conf/tor.common.torrc"
    for auth in ("4uthority1", "4uthority2", "4uthority3"):
        # RSA OR identity — from the `fingerprint` file (nick + 40 hex).
        fp_path = f"{sim_dir}/shadow.data.template/hosts/{auth}/fingerprint"
        result = ssh_cmd(f"awk '{{print $2}}' {fp_path}", capture=True)
        actual_fp = result.stdout.strip()
        if len(actual_fp) != 40:
            print_err(f"Bad RSA fingerprint for {auth}: {actual_fp!r}")
            sys.exit(1)

        # v3 authority identity — first line of `authority_certificate`
        # is "dir-key-certificate-version 3", and a few lines down there's
        # "fingerprint <40 hex>" naming the v3 identity key's hash.
        cert_path = f"{sim_dir}/shadow.data.template/hosts/{auth}/keys/authority_certificate"
        result = ssh_cmd(
            f"grep '^fingerprint' {cert_path} | awk '{{print $2}}'",
            capture=True,
        )
        actual_v3 = result.stdout.strip()
        if len(actual_v3) != 40:
            print_err(f"Bad v3ident for {auth}: {actual_v3!r}")
            sys.exit(1)

        # Tor accepts the trailing fp either as 40 unbroken hex or as 10
        # space-separated 4-char chunks. Use the spaced form (tornettools'
        # native format) so the rewritten line is visually consistent.
        spaced = " ".join(actual_fp[i:i+4] for i in range(0, 40, 4))

        # Single awk pass that rewrites BOTH:
        #   - v3ident=<...> token (field 3) → v3ident=<actual_v3>
        #   - trailing 10-field RSA fingerprint → spaced actual_fp
        # Everything in between (orport=..., ip:dirport) is preserved.
        awk_prog = (
            f'$1=="DirServer" && $2=="{auth}" {{ '
            f'  $3="v3ident={actual_v3}"; '
            f'  for(i=1;i<=NF-10;i++) printf "%s ", $i; '
            f'  print "{spaced}"; next '
            f'}} {{ print }}'
        )
        cmd = (
            f"awk '{awk_prog}' {torrc_path} > {torrc_path}.tmp && "
            f"mv {torrc_path}.tmp {torrc_path}"
        )
        ssh_cmd(cmd)
    # Print the patched lines for visibility.
    result = ssh_cmd(f"grep '^DirServer' {torrc_path}", capture=True)
    for line in result.stdout.strip().splitlines():
        print(f"    {line}")
    print_ok("Authority RSA fingerprints + v3idents aligned with template keys")

    # ── Step 2: Pull config to laptop ──────────────────────────────────
    print_step("Step 2/5: Pull config to laptop")
    cmd_pull_config(_namespace(name=name))

    if not local_config.exists():
        print_err(f"Expected {local_config} after pull-config but it's missing")
        sys.exit(1)

    # ── Step 2a: Wash tor.client.torrc of any prior WF appends ────────
    # Older versions of this script appended directly to tor.client.torrc,
    # which compounded across re-runs and ended up duplicating `UseBridges`
    # / `CircuitPadding` lines (Tor warns, last-wins). Since perfclients
    # and markov clients also %include tor.client.torrc, the stale
    # `UseBridges 1` would crash them with
    # "Setting UseBridges requires also setting UseEntryGuards".
    # Strip everything from the first `# WF experiment:` marker onwards.
    client_torrc = local_exp_dir / "conf" / "tor.client.torrc"
    if client_torrc.exists():
        text = client_torrc.read_text()
        marker = "# WF experiment:"
        if marker in text:
            cleaned = text.split(marker, 1)[0].rstrip() + "\n"
            client_torrc.write_text(cleaned)
            print_ok(f"Stripped stale WF appends from {client_torrc.relative_to(LOCAL_WORKSPACE)}")

    # ── Step 2b/2c: Write WF settings to a fresh conf/tor.wf.torrc ─────
    #
    # We do NOT touch tor.client.torrc — repeated runs would otherwise
    # accumulate duplicate `CircuitPadding` / `UseBridges` lines, and Tor's
    # last-value-wins semantics with a `UseEntryGuards 0` baseline would
    # break --defense tamaraw (UseBridges 1 requires UseEntryGuards 1).
    # Instead we emit a separate tor.wf.torrc file, %include'd LAST in
    # every monitor's torrc-defaults so it overrides earlier settings.
    wf_lines = []

    if args.padding is not None:
        if args.padding == "off":
            wf_lines += ["# WF experiment: padding disabled", "CircuitPadding 0"]
            print_ok("Circuit Padding: OFF (CircuitPadding 0)")
        elif args.padding == "on":
            wf_lines += ["# WF experiment: padding explicitly enabled", "CircuitPadding 1"]
            print_ok("Circuit Padding: ON (CircuitPadding 1)")
        elif args.padding == "reduced":
            wf_lines += ["# WF experiment: reduced padding",
                         "CircuitPadding 1", "ReducedCircuitPadding 1"]
            print_ok("Circuit Padding: REDUCED (ReducedCircuitPadding 1)")
    else:
        print("  (Circuit Padding: using Tor default = ON)")

    if args.defense == "tamaraw":
        cert_path = SIM_DIR_LOCAL / "conf" / "tamaraw_cert.txt"
        if not cert_path.exists():
            print_err(f"Tamaraw cert file missing: {cert_path}")
            print("  Run:  bash src/simulation/setup-wf-server.sh wfdef-cert")
            sys.exit(1)
        cert = cert_path.read_text().strip()
        if not cert or cert.startswith("PLACEHOLDER"):
            print_err(f"Tamaraw cert at {cert_path} is a placeholder.")
            print("  Run:  bash src/simulation/setup-wf-server.sh wfdef-cert")
            sys.exit(1)

        if args.padding is not None:
            print(f"  WARNING: --padding {args.padding} ignored on the link: "
                  f"Tamaraw's constant-rate scheduler dominates the on-wire pattern. "
                  f"CircuitPadding stays configured at the Tor layer.")

        wf_lines += [
            "",
            "# WF experiment: Tamaraw via WFDefProxy bridge",
            # Tor refuses UseBridges 1 without UseEntryGuards 1; overrides
            # the `UseEntryGuards 0` baseline from tor.client.torrc.
            "UseEntryGuards 1",
            "UseBridges 1",
            "ClientTransportPlugin tamaraw exec /home/projectadmin/obfs4proxy_tamaraw",
            (f"Bridge tamaraw {args.tamaraw_bridge_ip}:{args.tamaraw_bridge_port} "
             f"cert={cert} "
             f"rho-client={args.tamaraw_rho_client} "
             f"rho-server={args.tamaraw_rho_server} "
             f"nseg={args.tamaraw_nseg}"),
        ]
        print_ok(
            f"Defense: Tamaraw (bridge {args.tamaraw_bridge_ip}:{args.tamaraw_bridge_port}, "
            f"rho_c={args.tamaraw_rho_client}ms, rho_s={args.tamaraw_rho_server}ms, "
            f"nseg={args.tamaraw_nseg})"
        )

        # Copy the bridge torrc into the experiment's conf/ so push-config
        # ships it alongside tor.common.torrc / tor.client.torrc.
        src_bridge_torrc = SIM_DIR_LOCAL / "conf" / "tor.bridge.torrc"
        dst_bridge_torrc = local_exp_dir / "conf" / "tor.bridge.torrc"
        shutil.copy(src_bridge_torrc, dst_bridge_torrc)
        print_ok(f"Copied tor.bridge.torrc into {dst_bridge_torrc.relative_to(LOCAL_WORKSPACE)}")

    # Write the WF torrc (overwrite — always fresh per run).
    wf_torrc_path = local_exp_dir / "conf" / "tor.wf.torrc"
    wf_torrc_path.parent.mkdir(parents=True, exist_ok=True)
    wf_torrc_path.write_text(("\n".join(wf_lines) + "\n") if wf_lines else "")
    print_ok(f"Wrote {wf_torrc_path.relative_to(LOCAL_WORKSPACE)} ({len(wf_lines)} lines)")

    # ── Step 3: Add WF monitor/zimserver nodes ─────────────────────────
    print_step("Step 3/5: Add WF nodes to config")
    wf_cmd = [
        sys.executable, str(WF_CONFIG_GEN),
        "--base-config", str(local_config),
        "--urls",        str(urls_path),
        "--output",      str(local_config),
        "--num-monitors",    str(args.monitors),
        "--num-pages",       str(args.pages),
        "--visits-per-page", str(args.visits),
        "--visit-interval",  str(args.visit_interval),
    ]
    if args.open_world:
        wf_cmd += [
            "--open-world",
            "--monitored-pages",    str(args.monitored_pages),
            "--unmonitored-visits", str(args.unmonitored_visits),
        ]
    if args.correlation or args.correlation_only:
        wf_cmd += [
            "--enable-exit-pcap",
            "--exit-pcap-relays", str(args.exit_pcap_relays),
            "--guard-pcap-relays", str(args.guard_pcap_relays),
        ]
    if args.correlation_only:
        wf_cmd += ["--no-monitor-pcap"]
    if args.defense != "none":
        wf_cmd += [
            "--defense", args.defense,
            "--tamaraw-rho-client", str(args.tamaraw_rho_client),
            "--tamaraw-rho-server", str(args.tamaraw_rho_server),
            "--tamaraw-nseg",       str(args.tamaraw_nseg),
            "--tamaraw-bridge-port", str(args.tamaraw_bridge_port),
            "--tamaraw-bridge-ip",   args.tamaraw_bridge_ip,
        ]
    rc = subprocess.call(wf_cmd)
    if rc != 0:
        print_err("generate-wf-config.py failed")
        sys.exit(rc)

    # ── Step 4: Push + simulate ────────────────────────────────────────
    print_step("Step 4/5: Push config to server")
    cmd_push_config(_namespace(name=name))

    # Provision shadow.data.template/hosts/monitorN/ with torrc files.
    # tornettools only creates template dirs for the hosts IT generated,
    # so our WF nodes need their own torrc files or Tor fails to start.
    print_step("Step 4/5: Provision monitor template dirs")
    sim_dir = get_sim_dir(name)
    monitor_names = " ".join(f"monitor{i}" for i in range(args.monitors))
    provision_cmd = f"""bash -c '
        cd {sim_dir}/shadow.data.template/hosts
        for H in {monitor_names}; do
            mkdir -p "$H"
            cat > "$H/torrc" <<TORRC_EOF
# WF monitor torrc (host-specific overrides, if any)
TORRC_EOF
            cat > "$H/torrc-defaults" <<TORRC_EOF
%include ../../../conf/tor.common.torrc
%include ../../../conf/tor.client.torrc
%include ../../../conf/tor.wf.torrc
TORRC_EOF
        done
    '"""
    ssh_cmd(provision_cmd)
    print_ok(f"Provisioned template dirs for: {monitor_names}")

    if args.defense == "tamaraw":
        print_step("Step 4/5: Provision wfbridge0 template dir + pt_state")
        bridge_provision = f"""bash -c '
            set -e
            cd {sim_dir}/shadow.data.template/hosts
            mkdir -p wfbridge0
            cat > wfbridge0/torrc <<TORRC_EOF
# WF bridge torrc (host-specific overrides, if any)
TORRC_EOF
            cat > wfbridge0/torrc-defaults <<TORRC_EOF
%include ../../../conf/tor.common.torrc
%include ../../../conf/tor.bridge.torrc
TORRC_EOF
            # Copy pre-generated bridge state (keypair + cert) so the bridge
            # boots with the cert that monitor torrcs already reference.
            if [ ! -d /home/projectadmin/tamaraw-state-template/pt_state ]; then
                echo "ERROR: pre-staged pt_state missing on server." >&2
                echo "  Run on laptop: bash src/simulation/setup-wf-server.sh wfdef-cert" >&2
                exit 1
            fi
            rm -rf wfbridge0/pt_state
            cp -r /home/projectadmin/tamaraw-state-template/pt_state wfbridge0/pt_state
        '"""
        ssh_cmd(bridge_provision)
        print_ok("Provisioned wfbridge0 template dir + pt_state")

    print_step("Step 4/5: Start simulation")
    cmd_simulate(_namespace(
        name=name,
        stop_time=None,
        nproc=None,
        sim_seed=1,
    ))

    # ── Step 5: Initial status ─────────────────────────────────────────
    print_step("Step 5/5: Initial status")
    cmd_status(_namespace(name=name, tail=20))

    print(f"\n  Simulation running. Check progress with:")
    print(f"    ./shadowctl.py status --name {name}")
    print(f"    ./shadowctl.py logs   --name {name} -f")


def cmd_stop(args):
    """Kill a running simulation on the server (whole process tree)."""
    name = args.name
    sim_dir = get_sim_dir(name)

    print_header(f"Stopping simulation: {name}")

    result = ssh_cmd(f"test -f {sim_dir}/sim.pid && cat {sim_dir}/sim.pid",
                     capture=True, check=False)
    pid = result.stdout.strip() if result.returncode == 0 else ""
    if not pid:
        print_ok("No sim.pid file — nothing running for this experiment")
        return

    print_step(f"Killing process tree rooted at PID {pid}...")
    # We kill the entire process GROUP — Shadow's cmdline doesn't contain
    # the experiment name, so we can't target it by pattern. The PGID is
    # inherited from the wrapper bash, so `kill -- -$PGID` hits everything.
    ssh_cmd(f"""bash -c '
        PID={pid}
        PGID=$(ps -o pgid= -p $PID 2>/dev/null | tr -d " ")
        if [ -n "$PGID" ]; then
            kill -9 -- -"$PGID" 2>/dev/null
        fi
        # Belt-and-braces: also directly kill the wrapper + tornettools + shadow
        kill -9 $PID 2>/dev/null
        for child in $(pgrep -P $PID 2>/dev/null); do
            kill -9 $child 2>/dev/null
            for grandchild in $(pgrep -P $child 2>/dev/null); do
                kill -9 $grandchild 2>/dev/null
            done
        done
        rm -f {sim_dir}/sim.pid
        sleep 1
    '""", check=False)

    # Verify nothing is left
    result = ssh_cmd(
        "ps -ef | grep -E 'shadow |tornettools|\\.local/bin/tor' | grep projectadmin | grep -v grep | wc -l",
        capture=True, check=False,
    )
    remaining = result.stdout.strip()
    if remaining == "0":
        print_ok(f"Simulation '{name}' stopped (no remaining processes)")
    else:
        print_err(f"Still {remaining} simulation-related processes running — check manually:")
        print(f"  ssh {SSH_HOST} 'ps -ef | grep -E \"shadow|tornettools|\\.local/bin/tor\" | grep -v grep'")


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
    p.add_argument("--name", required=True, help="Experiment name")
    p.add_argument("--tail", type=int, default=20,
                   help="Number of sim.log lines to show (default: 20)")
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

    # stop
    p = sub.add_parser("stop", help="Kill a running simulation on the server")
    p.add_argument("--name", required=True, help="Experiment name")
    p.set_defaults(func=cmd_stop)

    # run (full workflow)
    p = sub.add_parser("run", help="Full workflow: generate + WF + push + simulate + status")
    p.add_argument("name", help="Experiment name (e.g. exp2)")
    p.add_argument("--scale",          type=float, default=0.01, help="Network scale (default: 0.01)")
    p.add_argument("--month",          default="2025-01", help="Tor data month (default: 2025-01)")
    p.add_argument("--monitors",       type=int, default=20, help="Number of WF monitor nodes (default: 20)")
    p.add_argument("--pages",          type=int, default=5,  help="Number of pages to fetch (default: 5)")
    p.add_argument("--visits",         type=int, default=50, help="Visits per page (default: 50)")
    p.add_argument("--visit-interval", type=int, default=30, help="Seconds per visit window (default: 30)")
    p.add_argument("--urls", default=str(DEFAULT_URLS_FILE),
                   help="URL list file (default: src/simulation/generated/urls.txt)")
    p.add_argument("--padding", choices=["on", "off", "reduced"],
                   default=None,
                   help="Circuit padding: on (Tor default), off, or reduced. "
                        "If omitted, Tor's built-in default is used (on).")
    # WF defense (orthogonal to --padding; selects a pluggable-transport bridge).
    p.add_argument("--defense", choices=["none", "tamaraw"], default="none",
                   help="Defense applied via PT bridge (default: none). "
                        "'tamaraw' adds a wfbridge0 host running WFDefProxy.")
    p.add_argument("--tamaraw-rho-client", type=int, default=12,
                   help="Tamaraw upstream packet interval in ms (default: 12)")
    p.add_argument("--tamaraw-rho-server", type=int, default=4,
                   help="Tamaraw downstream packet interval in ms (default: 4)")
    p.add_argument("--tamaraw-nseg", type=int, default=200,
                   help="Tamaraw trace-length padding segment (default: 200)")
    p.add_argument("--tamaraw-bridge-port", type=int, default=34000,
                   help="Bridge listen port for tamaraw transport (default: 34000)")
    p.add_argument("--tamaraw-bridge-ip", default="100.0.0.50",
                   help="Fixed IP for wfbridge0 (default: 100.0.0.50)")
    # Open-world options
    p.add_argument("--open-world", action="store_true",
                   help="Open-world: first --monitored-pages get full visits, "
                        "rest get --unmonitored-visits")
    p.add_argument("--monitored-pages", type=int, default=80,
                   help="Number of monitored pages in open-world (default: 80)")
    p.add_argument("--unmonitored-visits", type=int, default=10,
                   help="Visits per unmonitored page in open-world (default: 10)")
    # Correlation attack options
    p.add_argument("--correlation", action="store_true",
                   help="Enable exit relay pcaps (+ monitor pcaps for both WF and correlation)")
    p.add_argument("--correlation-only", action="store_true",
                   help="Exit relay pcaps only, NO monitor pcaps (correlation without WF, saves disk)")
    p.add_argument("--exit-pcap-relays", type=int, default=5,
                   help="Number of exit relays to capture pcaps on (default: 5)")
    p.add_argument("--guard-pcap-relays", type=int, default=5,
                   help="Number of guard relays to capture pcaps on (default: 5)")
    p.set_defaults(func=cmd_run)

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