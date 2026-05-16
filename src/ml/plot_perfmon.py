#!/usr/bin/env python3
"""
plot_perfmon.py — Visualize server resource usage from perfmon CSV logs.

Reads one or more perfmon-YYYY-MM-DD.csv files produced by
src/simulation/perfmon.py and renders a stacked time-series plot
(CPU %, RAM %, Disk %) to PDF.

Usage:
    python3 plot_perfmon.py --logs ../../perfmon-logs/ --output ../../images/results/perfmon.pdf
"""

import argparse
import csv
import datetime as dt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


COLS = ("iso_timestamp", "cpu_pct", "mem_pct", "disk_pct", "mem_used_gb", "load_1m")


def load(log_dir: Path):
    rows = []
    for csv_path in sorted(log_dir.glob("perfmon-*.csv")):
        with open(csv_path) as f:
            for row in csv.DictReader(f):
                try:
                    rows.append({
                        "t": dt.datetime.fromisoformat(row["iso_timestamp"]),
                        "cpu": float(row["cpu_pct"]),
                        "mem": float(row["mem_pct"]),
                        "disk": float(row["disk_pct"]),
                        "mem_gb": float(row["mem_used_gb"]),
                        "load": float(row["load_1m"]),
                    })
                except (KeyError, ValueError):
                    continue
    rows.sort(key=lambda r: r["t"])
    return rows


def plot(rows, output: Path):
    if not rows:
        raise SystemExit("no data")
    t = [r["t"] for r in rows]
    cpu = [r["cpu"] for r in rows]
    mem = [r["mem"] for r in rows]
    disk = [r["disk"] for r in rows]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(t, cpu, label="CPU", color="#d62728", linewidth=1.2)
    ax.plot(t, mem, label="RAM", color="#1f77b4", linewidth=1.2)
    ax.plot(t, disk, label="Disk", color="#2ca02c", linewidth=1.2)

    ax.set_ylim(0, 105)
    ax.set_ylabel("Auslastung [%]")
    ax.set_xlabel("Zeit (UTC)")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.legend(loc="lower right", frameon=True)

    span = t[-1] - t[0]
    title = (
        f"Server-Auslastung shadowsrv-001  "
        f"({t[0].strftime('%Y-%m-%d %H:%M')}–{t[-1].strftime('%H:%M')} UTC, "
        f"{span.total_seconds()/60:.0f} min, {len(rows)} Samples)"
    )
    ax.set_title(title, fontsize=10)

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    print(f"wrote {output}")

    # Print summary the thesis text can quote.
    def stats(name, vals):
        return f"{name}: mean={sum(vals)/len(vals):.1f}, min={min(vals):.1f}, max={max(vals):.1f}"
    print(stats("cpu_pct",  cpu))
    print(stats("mem_pct",  mem))
    print(stats("disk_pct", disk))
    print(f"mem_used_gb max = {max(r['mem_gb'] for r in rows):.1f}")
    print(f"load_1m mean = {sum(r['load'] for r in rows)/len(rows):.1f}, "
          f"max = {max(r['load'] for r in rows):.1f}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--logs", default="../../perfmon-logs", type=Path)
    p.add_argument("--output", default="../../images/results/perfmon.pdf", type=Path)
    args = p.parse_args()
    plot(load(args.logs), args.output)


if __name__ == "__main__":
    main()
