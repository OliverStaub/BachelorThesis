#!/usr/bin/env python3
"""
Stand-alone server performance logger for shadowsrv-001.

Samples CPU, RAM and disk usage from /proc and writes one CSV row per
interval. No external dependencies (pure stdlib). Designed to be copied
to the server by hand and started under nohup, then left running so the
student can pull the CSV logs occasionally.

Usage on server (manual deploy + start):

  scp src/simulation/perfmon.py projectadmin@shadowsrv-001...:~/
  ssh projectadmin@shadowsrv-001...
  nohup python3 ~/perfmon.py --interval 5 --log-dir ~/perfmon-logs \\
        > ~/perfmon.stderr 2>&1 &
  echo $! > ~/perfmon.pid

Pull logs back to laptop:

  rsync -av projectadmin@shadowsrv-001...:~/perfmon-logs/ ./perfmon-logs/

Stop on server:

  ssh projectadmin@shadowsrv-001... "kill \\$(cat ~/perfmon.pid)"

CSV columns:
  iso_timestamp, unix_ts, cpu_pct, mem_used_gb, mem_total_gb, mem_pct,
  disk_used_gb, disk_total_gb, disk_pct, load_1m, load_5m, load_15m

Daily rotation: a new file perfmon-YYYY-MM-DD.csv is opened when the UTC
date changes.
"""

import argparse
import csv
import datetime as dt
import os
import signal
import sys
import time
from pathlib import Path

GIB = 1024 ** 3
COLUMNS = [
    "iso_timestamp", "unix_ts",
    "cpu_pct",
    "mem_used_gb", "mem_total_gb", "mem_pct",
    "disk_used_gb", "disk_total_gb", "disk_pct",
    "load_1m", "load_5m", "load_15m",
]

_stop = False


def _handle_signal(signum, _frame):
    global _stop
    _stop = True


def read_cpu_totals():
    """Return (idle_ticks, total_ticks) from /proc/stat first 'cpu ' line."""
    with open("/proc/stat") as f:
        parts = f.readline().split()
    # parts = ['cpu', user, nice, system, idle, iowait, irq, softirq, steal, ...]
    nums = [int(x) for x in parts[1:]]
    idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
    total = sum(nums)
    return idle, total


def read_mem():
    """Return (used_gb, total_gb, pct) using MemAvailable when present."""
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, _, rest = line.partition(":")
            info[key.strip()] = int(rest.strip().split()[0])  # kB
    total_kb = info["MemTotal"]
    avail_kb = info.get("MemAvailable", info["MemFree"] + info.get("Cached", 0) + info.get("Buffers", 0))
    used_kb = total_kb - avail_kb
    total_gb = total_kb * 1024 / GIB
    used_gb = used_kb * 1024 / GIB
    pct = 100.0 * used_kb / total_kb if total_kb else 0.0
    return used_gb, total_gb, pct


def read_disk(mount):
    s = os.statvfs(mount)
    total = s.f_blocks * s.f_frsize
    free = s.f_bavail * s.f_frsize
    used = total - free
    pct = 100.0 * used / total if total else 0.0
    return used / GIB, total / GIB, pct


def read_load():
    with open("/proc/loadavg") as f:
        a, b, c, *_ = f.readline().split()
    return float(a), float(b), float(c)


def open_log_for(today, log_dir):
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"perfmon-{today.isoformat()}.csv"
    new_file = not path.exists()
    handle = open(path, "a", newline="", buffering=1)  # line-buffered
    writer = csv.writer(handle)
    if new_file:
        writer.writerow(COLUMNS)
    return handle, writer, path


def sample(prev_cpu, mount):
    idle, total = read_cpu_totals()
    if prev_cpu is None:
        cpu_pct = None
    else:
        d_idle = idle - prev_cpu[0]
        d_total = total - prev_cpu[1]
        cpu_pct = 100.0 * (1.0 - d_idle / d_total) if d_total > 0 else 0.0
    mem_used, mem_total, mem_pct = read_mem()
    disk_used, disk_total, disk_pct = read_disk(mount)
    load_1, load_5, load_15 = read_load()
    now = dt.datetime.now(dt.timezone.utc)
    row = None
    if cpu_pct is not None:
        row = [
            now.isoformat(timespec="seconds"),
            f"{now.timestamp():.3f}",
            f"{cpu_pct:.2f}",
            f"{mem_used:.3f}", f"{mem_total:.3f}", f"{mem_pct:.2f}",
            f"{disk_used:.3f}", f"{disk_total:.3f}", f"{disk_pct:.2f}",
            f"{load_1:.2f}", f"{load_5:.2f}", f"{load_15:.2f}",
        ]
    return row, (idle, total), now


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--interval", type=float, default=5.0,
                        help="Sampling interval in seconds (default: 5)")
    parser.add_argument("--log-dir", default="./perfmon-logs",
                        help="Directory for daily CSV files (default: ./perfmon-logs)")
    parser.add_argument("--mount", default="/",
                        help="Filesystem mountpoint for disk stats (default: /)")
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    log_dir = Path(args.log_dir)
    today = dt.datetime.now(dt.timezone.utc).date()
    handle, writer, path = open_log_for(today, log_dir)
    print(f"perfmon: writing to {path} every {args.interval}s", file=sys.stderr, flush=True)

    prev_cpu = None
    try:
        while not _stop:
            row, prev_cpu, now = sample(prev_cpu, args.mount)
            if row is not None:
                if now.date() != today:
                    handle.close()
                    today = now.date()
                    handle, writer, path = open_log_for(today, log_dir)
                    print(f"perfmon: rotated to {path}", file=sys.stderr, flush=True)
                writer.writerow(row)
            # Sleep in small slices so SIGTERM is responsive.
            slept = 0.0
            while slept < args.interval and not _stop:
                step = min(0.5, args.interval - slept)
                time.sleep(step)
                slept += step
    finally:
        handle.close()
        print("perfmon: stopped cleanly", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
