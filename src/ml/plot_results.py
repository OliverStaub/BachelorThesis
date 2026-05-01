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
    print(f"All plots saved to {out}/")


if __name__ == "__main__":
    main()
