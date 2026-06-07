#!/usr/bin/env python3
"""
export_perfmon_csv.py — Downsample perfmon / dstat telemetry to small CSVs
for inclusion in the thesis via pgfplots.

Reads the same logs and time windows as plot_perfmon.py, then writes one
CSV per Tamaraw run to src/thesis/data/. Each row holds the elapsed time
since the experiment start (hours) and the CPU/RAM/Disk percentages.

Usage:
    python3 export_perfmon_csv.py \
        --logs ../simulation/perfmon-logs \
        --output ../thesis/data \
        --samples 200
"""

import argparse
import csv
import datetime as dt
from pathlib import Path

from plot_perfmon import EXPERIMENTS, load_perfmon, load_dstat, mark_disk_missing, filter_window


def downsample(rows, n):
    if len(rows) <= n:
        return rows
    step = len(rows) / n
    return [rows[int(i * step)] for i in range(n)]


def write_csv(path: Path, rows, t0, has_disk):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["hours", "cpu", "mem"] + (["disk"] if has_disk else [])
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for r in rows:
            hours = (r["t"] - t0).total_seconds() / 3600.0
            row = [f"{hours:.4f}", f"{r['cpu']:.2f}", f"{r['mem']:.2f}"]
            if has_disk:
                row.append(f"{r['disk']:.2f}")
            w.writerow(row)


SHORT_NAME = {
    "exp-tamaraw-80":        "tamaraw80",
    "exp-tamaraw-openworld": "openworld",
    "exp-tamaraw-20v2":      "tamaraw20v2",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--logs", default="../simulation/perfmon-logs", type=Path)
    p.add_argument("--output", default="../thesis/data", type=Path)
    p.add_argument("--samples", default=200, type=int,
                   help="approximate number of points per experiment")
    args = p.parse_args()

    perfmon_rows = load_perfmon(args.logs)
    print(f"loaded {len(perfmon_rows)} perfmon samples")

    for exp in EXPERIMENTS:
        if exp["source"] == "perfmon":
            rows = filter_window(perfmon_rows, exp["t_start"], exp["t_end"])
            has_disk = True
        else:
            dstat_rows = load_dstat(args.logs / exp["source_file"])
            mark_disk_missing(dstat_rows)
            rows = filter_window(dstat_rows, exp["t_start"], exp["t_end"])
            has_disk = False
        if not rows:
            print(f"  [skip] {exp['name']}: no samples in window")
            continue
        ds = downsample(rows, args.samples)
        out = args.output / f"perfmon_{SHORT_NAME[exp['name']]}.csv"
        write_csv(out, ds, rows[0]["t"], has_disk)
        print(f"  {exp['name']} → {out} ({len(ds)} rows, disk={'yes' if has_disk else 'no'})")


if __name__ == "__main__":
    main()
