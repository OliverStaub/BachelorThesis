#!/usr/bin/env python3
"""
plot_results.py — Generate thesis-quality result visualizations.

Usage:
    python3 plot_results.py --csv ../../ExperimentLogs.csv --output ../../images/
"""

import argparse
import csv
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def parse_pct(s):
    """Parse '92.7%' or '92.7' to float."""
    if not s:
        return None
    s = s.strip().rstrip("%")
    try:
        return float(s)
    except ValueError:
        return None


def load_csv(path):
    """Load ExperimentLogs.csv into a list of dicts."""
    rows = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def plot_padding_comparison(rows, output_dir):
    """Bar chart: Accuracy by padding setting, grouped by page count."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Filter to the main closed-world experiments
    groups = {"20 pages": {}, "80 pages": {}}
    for row in rows:
        pages = row.get("Pages (classes)", "")
        padding = row.get("Circuit Padding", "")
        acc = parse_pct(row.get("Accuracy", ""))
        if acc is None:
            continue

        # Skip early test runs and open-world
        if pages == "5" or pages == "280" or "openworld" in row.get("Experiment", ""):
            continue

        key = f"{pages} pages"
        if key in groups:
            groups[key][padding] = acc

    x = np.arange(len(groups))
    width = 0.22
    padding_types = ["OFF", "ON", "Reduced"]
    colors = ["#2196F3", "#FF9800", "#4CAF50"]

    for i, (ptype, color) in enumerate(zip(padding_types, colors)):
        vals = [groups[g].get(ptype, 0) for g in groups]
        bars = ax.bar(x + i * width, vals, width, label=f"Padding {ptype}",
                      color=color, edgecolor="white", linewidth=0.5)
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f"{val:.1f}%", ha="center", va="bottom", fontsize=9)

    ax.set_xlabel("Experiment Configuration")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Deep Fingerprinting Accuracy vs Circuit Padding")
    ax.set_xticks(x + width)
    ax.set_xticklabels(list(groups.keys()))
    ax.legend()
    ax.set_ylim(0, 105)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    for ext in [".pdf", ".svg", ".png"]:
        plt.savefig(output_dir / f"padding_comparison{ext}", dpi=300, bbox_inches="tight")
    plt.close()
    print("  Saved padding_comparison")


def plot_accuracy_vs_pages(rows, output_dir):
    """Line chart: Accuracy vs number of pages for each padding setting."""
    fig, ax = plt.subplots(figsize=(8, 6))

    # Collect data points
    data = {}  # {padding: [(pages, accuracy), ...]}
    for row in rows:
        pages = row.get("Pages (classes)", "")
        padding = row.get("Circuit Padding", "")
        acc = parse_pct(row.get("Accuracy", ""))
        if acc is None or not pages.isdigit():
            continue
        pages_int = int(pages)
        if pages_int < 10 or "openworld" in row.get("Experiment", ""):
            continue
        if padding not in data:
            data[padding] = []
        data[padding].append((pages_int, acc))

    colors = {"OFF": "#2196F3", "ON": "#FF9800", "Reduced": "#4CAF50"}
    markers = {"OFF": "o", "ON": "s", "Reduced": "^"}

    for padding, points in sorted(data.items()):
        points.sort()
        xs, ys = zip(*points)
        ax.plot(xs, ys, marker=markers.get(padding, "o"), label=f"Padding {padding}",
                color=colors.get(padding, "gray"), linewidth=2, markersize=8)

    # Add random baseline
    pages_range = [20, 80]
    baselines = [100/p for p in pages_range]
    ax.plot(pages_range, baselines, "--", color="gray", alpha=0.5, label="Random baseline")

    ax.set_xlabel("Number of Monitored Pages (Classes)")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("DF Accuracy vs Number of Pages")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.set_ylim(0, 100)

    plt.tight_layout()
    for ext in [".pdf", ".svg", ".png"]:
        plt.savefig(output_dir / f"accuracy_vs_pages{ext}", dpi=300, bbox_inches="tight")
    plt.close()
    print("  Saved accuracy_vs_pages")


def plot_f1_comparison(rows, output_dir):
    """Grouped bar chart: F1-score by experiment."""
    fig, ax = plt.subplots(figsize=(12, 6))

    # Filter to main experiments
    experiments = []
    for row in rows:
        f1 = parse_pct(row.get("F1-score", ""))
        if f1 is None:
            continue
        name = row.get("Experiment", "")
        if name in ("exp7", "exp8", "exp-baseline", "exp-corr"):
            continue
        pages = row.get("Pages (classes)", "")
        padding = row.get("Circuit Padding", "")
        label = f"{pages}p {padding}"
        if "openworld" in name:
            label = "Open World"
        experiments.append((label, f1, padding))

    labels = [e[0] for e in experiments]
    values = [e[1] for e in experiments]
    color_map = {"OFF": "#2196F3", "ON": "#FF9800", "Reduced": "#4CAF50"}
    colors = [color_map.get(e[2], "#9E9E9E") for e in experiments]

    bars = ax.bar(range(len(experiments)), values, color=colors, edgecolor="white", linewidth=0.5)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(range(len(experiments)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("F1-Score (%)")
    ax.set_title("F1-Score Across All Experiments")
    ax.set_ylim(0, 105)
    ax.grid(axis="y", alpha=0.3)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#2196F3", label="Padding OFF"),
        Patch(facecolor="#FF9800", label="Padding ON"),
        Patch(facecolor="#4CAF50", label="Reduced"),
        Patch(facecolor="#9E9E9E", label="Other"),
    ]
    ax.legend(handles=legend_elements, loc="upper right")

    plt.tight_layout()
    for ext in [".pdf", ".svg", ".png"]:
        plt.savefig(output_dir / f"f1_comparison{ext}", dpi=300, bbox_inches="tight")
    plt.close()
    print("  Saved f1_comparison")


def plot_padding_vs_tamaraw(rows, output_dir):
    """Bar chart: Accuracy across OFF / Reduced / ON / Tamaraw for 20 and 80 classes."""
    fig, ax = plt.subplots(figsize=(10, 6))

    groups = {"20": {}, "80": {}}
    for row in rows:
        name = row.get("Experiment", "")
        pages = row.get("Pages (classes)", "")
        padding = row.get("Circuit Padding", "")
        acc = parse_pct(row.get("Accuracy", ""))
        visits = row.get("Visits per page", "")
        if acc is None or pages not in groups:
            continue
        if visits != "150":
            continue
        if "openworld" in name:
            continue
        if "tamaraw" in name:
            mode = "Tamaraw"
        elif padding == "OFF":
            mode = "OFF"
        elif padding == "ON":
            mode = "ON"
        elif padding == "Reduced":
            mode = "Reduced"
        else:
            continue
        groups[pages][mode] = acc

    modes = ["OFF", "Reduced", "ON", "Tamaraw"]
    colors = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0"]

    page_labels = list(groups.keys())
    x = np.arange(len(page_labels))
    width = 0.2

    for i, (mode, color) in enumerate(zip(modes, colors)):
        vals = [groups[p].get(mode, 0) for p in page_labels]
        offset = (i - 1.5) * width
        bars = ax.bar(x + offset, vals, width, label=mode, color=color,
                      edgecolor="white", linewidth=0.5)
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f"{val:.1f}%", ha="center", va="bottom", fontsize=9)

    for i, p in enumerate(page_labels):
        baseline = 100.0 / int(p)
        ax.hlines(baseline, x[i] - 2.2*width, x[i] + 2.2*width,
                  colors="gray", linestyles="--", linewidth=1)
    ax.plot([], [], "--", color="gray", linewidth=1, label="Random baseline")

    ax.set_xlabel("Number of Classes")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("DF Accuracy: Circuit Padding vs Tamaraw")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{p} classes" for p in page_labels])
    ax.legend(loc="upper right")
    ax.set_ylim(0, 105)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    for ext in [".pdf", ".svg", ".png"]:
        plt.savefig(output_dir / f"padding_vs_tamaraw{ext}", dpi=300, bbox_inches="tight")
    plt.close()
    print("  Saved padding_vs_tamaraw")


def plot_defense_tradeoff(rows, output_dir):
    """Scatter: bandwidth overhead vs accuracy drop at 80 classes."""
    fig, ax = plt.subplots(figsize=(8, 6))

    baseline_acc = None
    for row in rows:
        if row.get("Experiment") == "exp-baseline-80":
            baseline_acc = parse_pct(row.get("Accuracy", ""))
            break

    points = {
        "Reduced":  (1.3,    "exp-reduced-80",  "#4CAF50"),
        "ON":       (3.0,    "exp-padding-80",  "#FF9800"),
        "Tamaraw":  (1063.1, "exp-tamaraw-80",  "#9C27B0"),
    }

    for label, (bw, exp_name, color) in points.items():
        acc = None
        for row in rows:
            if row.get("Experiment") == exp_name:
                acc = parse_pct(row.get("Accuracy", ""))
                break
        if acc is None or baseline_acc is None:
            continue
        drop = baseline_acc - acc
        ax.scatter(bw, drop, s=200, color=color, edgecolor="black", linewidth=1, zorder=3,
                   label=f"{label}  ({bw:.1f} %, -{drop:.1f} pp)")
        ax.annotate(label, (bw, drop), xytext=(8, 8), textcoords="offset points",
                    fontsize=11, fontweight="bold")

    ax.set_xscale("symlog", linthresh=10)
    ax.set_xlabel("Bandwidth overhead (%, symlog)")
    ax.set_ylabel("Accuracy drop vs baseline (pp)")
    ax.set_title("Defense tradeoff at 80 classes: cost vs protection")
    ax.grid(alpha=0.3, which="both")
    ax.legend(loc="lower right")
    ax.set_xlim(0.5, 3000)
    ax.set_ylim(0, 60)

    plt.tight_layout()
    for ext in [".pdf", ".svg", ".png"]:
        plt.savefig(output_dir / f"defense_tradeoff{ext}", dpi=300, bbox_inches="tight")
    plt.close()
    print("  Saved defense_tradeoff")


def plot_padding_delta(rows, output_dir):
    """Bar chart showing the accuracy DROP caused by padding."""
    fig, ax = plt.subplots(figsize=(8, 5))

    # Calculate deltas
    baselines = {}
    padded = {}
    reduced = {}
    for row in rows:
        pages = row.get("Pages (classes)", "")
        padding = row.get("Circuit Padding", "")
        acc = parse_pct(row.get("Accuracy", ""))
        if acc is None or not pages.isdigit() or int(pages) < 10:
            continue
        if "openworld" in row.get("Experiment", ""):
            continue
        if padding == "OFF":
            baselines[pages] = acc
        elif padding == "ON":
            padded[pages] = acc
        elif padding == "Reduced":
            reduced[pages] = acc

    labels = []
    delta_on = []
    delta_reduced = []
    for pages in sorted(baselines.keys(), key=int):
        if pages in padded:
            labels.append(f"{pages} pages")
            delta_on.append(baselines[pages] - padded[pages])
            delta_reduced.append(baselines[pages] - reduced.get(pages, baselines[pages]))

    x = np.arange(len(labels))
    width = 0.35

    bars1 = ax.bar(x - width/2, delta_on, width, label="Padding ON",
                   color="#FF9800", edgecolor="white")
    bars2 = ax.bar(x + width/2, delta_reduced, width, label="Padding Reduced",
                   color="#4CAF50", edgecolor="white")

    for bars in [bars1, bars2]:
        for bar in bars:
            val = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    f"-{val:.1f}pp", ha="center", va="bottom", fontsize=10)

    ax.set_xlabel("Experiment")
    ax.set_ylabel("Accuracy Drop (percentage points)")
    ax.set_title("Circuit Padding Effect on DF Accuracy")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    for ext in [".pdf", ".svg", ".png"]:
        plt.savefig(output_dir / f"padding_delta{ext}", dpi=300, bbox_inches="tight")
    plt.close()
    print("  Saved padding_delta")


def main():
    parser = argparse.ArgumentParser(description="Generate result visualizations")
    parser.add_argument("--csv", default="../../ExperimentLogs.csv",
                        help="Path to ExperimentLogs.csv")
    parser.add_argument("--output", default="../../images/results/",
                        help="Output directory for plots")
    args = parser.parse_args()

    rows = load_csv(args.csv)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    print("Generating visualizations...")
    plot_padding_comparison(rows, out)
    plot_accuracy_vs_pages(rows, out)
    plot_f1_comparison(rows, out)
    plot_padding_delta(rows, out)
    plot_padding_vs_tamaraw(rows, out)
    plot_defense_tradeoff(rows, out)
    print(f"All plots saved to {out}/")


if __name__ == "__main__":
    main()
