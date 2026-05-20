#!/usr/bin/env python3
"""
plot_perfmon.py — Visualize server resource usage from perfmon CSV / dstat logs.

Reads:
  * perfmon-YYYY-MM-DD.csv files produced by src/simulation/perfmon.py
  * dstat.log produced inline by tornettools simulate wrappers
    (used when perfmon was offline, e.g. after disk full)

For each experiment with a known UTC time window, writes a three-line
time-series plot (CPU %, RAM %, Disk %) to images/results/.

Usage:
    python3 plot_perfmon.py --logs ../../src/simulation/perfmon-logs --output ../../images/results
"""

import argparse
import csv
import datetime as dt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


# Experiment time windows (UTC). End is exclusive; samples are filtered by [t_start, t_end].
EXPERIMENTS = [
    {
        "name": "exp-tamaraw-80",
        "title": "Tamaraw, 80 Klassen",
        "t_start": dt.datetime(2026, 5, 16, 10, 15, 16, tzinfo=dt.timezone.utc),
        "t_end":   dt.datetime(2026, 5, 17,  3,  3, 27, tzinfo=dt.timezone.utc),
        "source":  "perfmon",
        "output":  "perfmon_tamaraw80",
    },
    {
        "name": "exp-tamaraw-openworld",
        "title": "Tamaraw, Open-World",
        "t_start": dt.datetime(2026, 5, 17, 10, 17, 43, tzinfo=dt.timezone.utc),
        "t_end":   dt.datetime(2026, 5, 18,  2, 30,  0, tzinfo=dt.timezone.utc),
        "source":  "perfmon",
        "output":  "perfmon_openworld",
        "note":    "Disk full",
    },
    {
        "name": "exp-tamaraw-20v2",
        "title": "Tamaraw, 20 Klassen (zweiter Lauf)",
        "t_start": dt.datetime(2026, 5, 19, 20, 24, 26, tzinfo=dt.timezone.utc),
        "t_end":   dt.datetime(2026, 5, 20,  4, 34, 21, tzinfo=dt.timezone.utc),
        "source":  "dstat",
        "source_file": "dstat-tamaraw-20v2.log",
        "output":  "perfmon_tamaraw20v2",
    },
]


# Constants used to translate dstat / perfmon raw fields.
DISK_TOTAL_GB = 155.643      # from perfmon: /dev/mapper/ubuntu--vg-ubuntu--lv
MEM_TOTAL_GB  = 125.789      # from perfmon: matches /proc/meminfo MemTotal


def load_perfmon(log_dir: Path):
    """Return rows from all perfmon-*.csv files sorted by timestamp."""
    rows = []
    for csv_path in sorted(log_dir.glob("perfmon-*.csv")):
        with open(csv_path) as f:
            for row in csv.DictReader(f):
                try:
                    rows.append({
                        "t":    dt.datetime.fromisoformat(row["iso_timestamp"]),
                        "cpu":  float(row["cpu_pct"]),
                        "mem":  float(row["mem_pct"]),
                        "disk": float(row["disk_pct"]),
                        "mem_gb":  float(row["mem_used_gb"]),
                        "disk_gb": float(row["disk_used_gb"]),
                        "load":    float(row["load_1m"]),
                    })
                except (KeyError, ValueError):
                    continue
    rows.sort(key=lambda r: r["t"])
    return rows


def load_dstat(path: Path):
    """Parse dstat.log produced with `dstat -cmstTy --fs --output dstat.log`.

    Column layout (after the metadata header pcp-dstat writes):
      usr, sys, idl, wai, stl,            -- CPU (%)
      used, free, buf, cach,              -- memory (KB)
      total:used, total:free,             -- swap (KB)  (irrelevant)
      time, epoch, int, csw, files, inodes
    Disk usage isn't recorded by this dstat config, so the caller has to fall
    back to a single static estimate or stitch it in from the perfmon snapshot.
    """
    rows = []
    with open(path) as f:
        reader = csv.reader(f)
        in_data = False
        for parts in reader:
            if not parts:
                continue
            # Skip pcp-dstat header lines until we hit numeric CPU values.
            if not in_data:
                try:
                    float(parts[0])
                except ValueError:
                    continue
                in_data = True
            if len(parts) < 13:
                continue
            try:
                usr, sys_, idl, wai, stl = (float(x) for x in parts[0:5])
                used_kb, free_kb, buf_kb, cach_kb = (float(x) for x in parts[5:9])
                epoch = float(parts[12])
            except ValueError:
                continue
            cpu_pct = 100.0 - idl
            mem_gb = (used_kb + buf_kb + cach_kb) / (1024 * 1024)
            mem_pct = 100.0 * mem_gb / MEM_TOTAL_GB
            rows.append({
                "t":   dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc),
                "cpu": cpu_pct,
                "mem": mem_pct,
                "mem_gb": mem_gb,
                "load": 0.0,
            })
    return rows


def mark_disk_missing(dstat_rows):
    """Mark dstat rows as having no disk telemetry (perfmon stopped after OOM)."""
    for r in dstat_rows:
        r["disk_gb"] = float("nan")
        r["disk"] = float("nan")


def filter_window(rows, t_start, t_end):
    return [r for r in rows if t_start <= r["t"] <= t_end]


def plot_experiment(exp, rows, output_dir: Path):
    if not rows:
        print(f"  [skip] {exp['name']}: no samples in window")
        return

    t   = [r["t"] for r in rows]
    cpu = [r["cpu"] for r in rows]
    mem = [r["mem"] for r in rows]
    disk = [r["disk"] for r in rows]
    disk_has_data = any(d == d for d in disk)  # NaN != NaN

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(t, cpu,  label="CPU",  color="#d62728", linewidth=1.0)
    ax.plot(t, mem,  label="RAM",  color="#1f77b4", linewidth=1.0)
    if disk_has_data:
        ax.plot(t, disk, label="Disk", color="#2ca02c", linewidth=1.0)
    else:
        ax.plot([], [], label="Disk (keine Telemetrie)", color="#cccccc", linewidth=1.0)

    ax.set_ylim(0, 105)
    ax.set_ylabel("Auslastung [%]")
    ax.set_xlabel("Zeit (UTC)")
    ax.grid(True, alpha=0.3)

    span = t[-1] - t[0]
    if span > dt.timedelta(hours=8):
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m %H:%M"))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig.autofmt_xdate()

    ax.legend(loc="lower right", frameon=True)

    title = (
        f"{exp['title']}  "
        f"({t[0].strftime('%Y-%m-%d %H:%M')}–{t[-1].strftime('%H:%M')} UTC, "
        f"{span.total_seconds()/3600:.1f} h, {len(rows)} Samples)"
    )
    ax.set_title(title, fontsize=10)

    if exp.get("note") and disk_has_data:
        # Annotate the point where disk first crosses 99 %.
        for ts, d in zip(t, disk):
            if d >= 99.0:
                ax.annotate(
                    exp["note"],
                    xy=(ts, d),
                    xytext=(-120, -40), textcoords="offset points",
                    fontsize=9, color="#555",
                    arrowprops={"arrowstyle": "->", "color": "#555", "lw": 0.8},
                )
                break
    if not disk_has_data:
        ax.text(0.02, 0.97,
                "Disk-Telemetrie offline\n(perfmon stoppte nach OOM)",
                transform=ax.transAxes, fontsize=9, color="#555",
                va="top", ha="left",
                bbox={"facecolor": "white", "edgecolor": "#bbb", "boxstyle": "round,pad=0.3"})

    out_pdf = output_dir / f"{exp['output']}.pdf"
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(output_dir / f"{exp['output']}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    def stats(name, vals):
        clean = [v for v in vals if v == v]
        if not clean:
            return f"{name}: no data"
        return f"{name}: mean={sum(clean)/len(clean):.1f}, min={min(clean):.1f}, max={max(clean):.1f}"
    print(f"  {exp['name']} → {out_pdf.name}")
    print(f"    span={span}, samples={len(rows)}")
    print(f"    {stats('cpu',  cpu)}")
    print(f"    {stats('mem',  mem)}")
    print(f"    {stats('disk', disk)}")
    disk_gbs = [r["disk_gb"] for r in rows if r["disk_gb"] == r["disk_gb"]]
    print(f"    mem_gb max={max(r['mem_gb'] for r in rows):.1f}"
          + (f", disk_gb max={max(disk_gbs):.1f}" if disk_gbs else ""))


def plot_summary(experiments_rows, output_dir: Path):
    """Three vertically stacked panels (CPU / RAM / Disk), one line per experiment.

    Each experiment is plotted on a shared elapsed-time x-axis (hours since
    experiment start) so the runs can be compared even though they happened on
    different days.
    """
    colors = {"exp-tamaraw-80": "#d62728",
              "exp-tamaraw-openworld": "#1f77b4",
              "exp-tamaraw-20v2": "#2ca02c"}
    labels = {"exp-tamaraw-80": "Tamaraw 80 Klassen",
              "exp-tamaraw-openworld": "Tamaraw Open-World",
              "exp-tamaraw-20v2": "Tamaraw 20 Klassen (v2)"}

    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    for name, rows in experiments_rows.items():
        if not rows:
            continue
        t0 = rows[0]["t"]
        hours = [(r["t"] - t0).total_seconds() / 3600 for r in rows]
        axes[0].plot(hours, [r["cpu"]  for r in rows], color=colors[name], linewidth=0.9, label=labels[name])
        axes[1].plot(hours, [r["mem"]  for r in rows], color=colors[name], linewidth=0.9, label=labels[name])
        disk_vals = [r["disk"] for r in rows]
        if any(d == d for d in disk_vals):
            axes[2].plot(hours, disk_vals, color=colors[name], linewidth=0.9, label=labels[name])

    for ax, title in zip(axes, ["CPU", "Arbeitsspeicher", "Disk"]):
        ax.set_ylabel(f"{title} [%]")
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 105)
    axes[0].legend(loc="lower right", frameon=True, fontsize=9)
    axes[2].set_xlabel("Laufzeit seit Experimentstart [h]")
    axes[0].set_title("Serverauslastung im Vergleich der Tamaraw-Experimente", fontsize=11)

    out = output_dir / "perfmon_comparison"
    fig.tight_layout()
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(out.with_suffix(".png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  summary → {out.name}.pdf")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--logs", default="../simulation/perfmon-logs", type=Path)
    p.add_argument("--output", default="../../images/results", type=Path)
    args = p.parse_args()

    perfmon_rows = load_perfmon(args.logs)
    print(f"loaded {len(perfmon_rows)} perfmon samples from {args.logs}")

    experiments_rows = {}
    for exp in EXPERIMENTS:
        if exp["source"] == "perfmon":
            rows = filter_window(perfmon_rows, exp["t_start"], exp["t_end"])
        elif exp["source"] == "dstat":
            dstat_rows = load_dstat(args.logs / exp["source_file"])
            mark_disk_missing(dstat_rows)
            rows = filter_window(dstat_rows, exp["t_start"], exp["t_end"])
        else:
            raise ValueError(exp["source"])
        experiments_rows[exp["name"]] = rows
        plot_experiment(exp, rows, args.output)

    plot_summary(experiments_rows, args.output)


if __name__ == "__main__":
    main()
