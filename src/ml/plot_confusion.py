#!/usr/bin/env python3
"""
plot_confusion.py — Generate confusion matrix heatmaps from trained WFlib models.

Creates:
  1. Single confusion matrix for one experiment
  2. Side-by-side comparison of two experiments (e.g., padding OFF vs ON)
  3. Difference matrix showing what changed

Usage:
    # Single experiment:
    python3 plot_confusion.py --dataset ExpBaseline20 --output confusion_baseline20.pdf

    # Side-by-side comparison:
    python3 plot_confusion.py --dataset ExpBaseline20 ExpPadding20 \
        --labels "Padding OFF" "Padding ON" --output confusion_comparison.pdf

    # With difference matrix:
    python3 plot_confusion.py --dataset ExpBaseline20 ExpPadding20 \
        --labels "Padding OFF" "Padding ON" --diff --output confusion_diff.pdf

Run from src/ml/wflib/ (same directory as train.py / test.py).
"""

import argparse
import json
import os
import sys

import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")  # no GUI needed
import matplotlib.pyplot as plt

# Add wflib to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WFLIB_DIR = os.path.join(SCRIPT_DIR, "wflib")
sys.path.insert(0, WFLIB_DIR)

from WFlib import models
from WFlib.tools import data_processor
from sklearn.metrics import confusion_matrix

SIM_DIR = os.path.join(SCRIPT_DIR, "..", "simulation")


def load_class_names(dataset):
    """Load human-readable class names from labels.json + urls.txt.

    Returns a list of short article names indexed by class label,
    e.g. ['Eurovision...', 'Andhra Pr.', ...].
    """
    labels_path = os.path.join(WFLIB_DIR, "datasets", f"{dataset}.labels.json")
    urls_path = os.path.join(SIM_DIR, "generated", "urls.txt")

    if not os.path.exists(labels_path) or not os.path.exists(urls_path):
        return None

    with open(labels_path) as f:
        labels_data = json.load(f)

    # Build port -> article name from urls.txt
    port_to_name = {}
    with open(urls_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 3:
                port = int(parts[1])
                name = parts[2].split("/")[-1].replace("_", " ")
                port_to_name[port] = name

    # Build label -> short name
    label_to_port = labels_data.get("label_to_port", {})
    num_classes = labels_data.get("num_classes", 0)
    names = []
    for i in range(num_classes):
        port = label_to_port.get(str(i))
        if port and port in port_to_name:
            full_name = port_to_name[port]
            # Shorten long names: keep first 18 chars
            if len(full_name) > 18:
                short = full_name[:16] + ".."
            else:
                short = full_name
            names.append(short)
        else:
            names.append(str(i))

    return names


def get_predictions(dataset, model_name="DF", feature="DIR", seq_len=5000,
                    load_name="max_f1", device="cpu"):
    """Load model + test data, return (y_true, y_pred)."""
    in_path = os.path.join(WFLIB_DIR, "datasets", dataset)
    ckp_path = os.path.join(WFLIB_DIR, "checkpoints", dataset, model_name)

    # Load test data
    test_X, test_y = data_processor.load_data(
        os.path.join(in_path, "test.npz"), feature, seq_len, 1
    )
    num_classes = len(np.unique(test_y))

    # Load model
    model = eval(f"models.{model_name}")(num_classes)
    checkpoint = torch.load(
        os.path.join(ckp_path, f"{load_name}.pth"),
        map_location=device, weights_only=True,
    )
    model.load_state_dict(checkpoint)
    model.eval()

    # Run inference
    dev = torch.device(device)
    model.to(dev)
    all_preds = []
    all_true = []

    test_iter = data_processor.load_iter(test_X, test_y, 256, False, 0)
    with torch.no_grad():
        for X_batch, y_batch in test_iter:
            X_batch = X_batch.to(dev)
            output = model(X_batch)
            preds = output.argmax(dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_true.extend(y_batch.numpy())

    return np.array(all_true), np.array(all_preds), num_classes


def plot_single(cm_norm, title, ax, num_classes, class_names=None, show_numbers=True):
    """Plot a single confusion matrix on the given axes."""
    im = ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1, aspect="equal")

    if show_numbers and num_classes <= 25:
        for i in range(num_classes):
            for j in range(num_classes):
                val = cm_norm[i, j]
                if val > 0.01:
                    ax.text(j, i, f"{val:.2f}",
                            ha="center", va="center",
                            color="white" if val > 0.5 else "black",
                            fontsize=max(4, 8 - num_classes // 5))

    # Use article names as tick labels if available
    if class_names and num_classes <= 40:
        ax.set_xticks(range(num_classes))
        ax.set_yticks(range(num_classes))
        fontsize = max(5, 9 - num_classes // 5)
        ax.set_xticklabels(class_names, rotation=90, fontsize=fontsize)
        ax.set_yticklabels(class_names, fontsize=fontsize)
        ax.set_xlabel("")
        ax.set_ylabel("")
    else:
        ax.set_xlabel("Predicted class")
        ax.set_ylabel("True class")

    ax.set_title(title)
    return im


def main():
    parser = argparse.ArgumentParser(description="Plot confusion matrices")
    parser.add_argument("--dataset", nargs="+", required=True,
                        help="One or two dataset names (e.g., ExpBaseline20 ExpPadding20)")
    parser.add_argument("--labels", nargs="+", default=None,
                        help="Display labels for each dataset (e.g., 'Padding OFF' 'Padding ON')")
    parser.add_argument("--diff", action="store_true",
                        help="Also show difference matrix (requires 2 datasets)")
    parser.add_argument("--output", default="confusion_matrix.pdf",
                        help="Output file (PDF or PNG)")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    datasets = args.dataset
    labels = args.labels or datasets

    print(f"Loading predictions for {len(datasets)} dataset(s)...", file=sys.stderr)

    results = []
    class_names = None
    for ds in datasets:
        print(f"  {ds}...", file=sys.stderr)
        y_true, y_pred, n_classes = get_predictions(ds, device=args.device)
        cm = confusion_matrix(y_true, y_pred)
        # Normalize by row (each row sums to 1 = recall per class)
        cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)
        results.append((cm, cm_norm, n_classes))
        # Load class names from the first dataset (same URLs for all)
        if class_names is None:
            class_names = load_class_names(ds)
            if class_names:
                print(f"  Loaded {len(class_names)} class names", file=sys.stderr)

    show_numbers = results[0][2] <= 25

    if len(datasets) == 1:
        # Single matrix
        fig, ax = plt.subplots(figsize=(12, 10), constrained_layout=True)
        im = plot_single(results[0][1], labels[0], ax, results[0][2],
                         class_names, show_numbers)
        fig.colorbar(im, ax=ax, label="Recall", shrink=0.8)

    elif len(datasets) == 2 and not args.diff:
        # Side-by-side comparison
        fig, axes = plt.subplots(1, 2, figsize=(22, 10), constrained_layout=True)
        for i, (ax, label) in enumerate(zip(axes, labels)):
            im = plot_single(results[i][1], label, ax, results[i][2],
                             class_names, show_numbers)
        fig.colorbar(im, ax=axes, label="Recall", shrink=0.8, location="right")

    elif len(datasets) == 2 and args.diff:
        # Side-by-side + difference
        fig, axes = plt.subplots(1, 3, figsize=(30, 9), constrained_layout=True)
        for i, (ax, label) in enumerate(zip(axes[:2], labels)):
            im = plot_single(results[i][1], label, ax, results[i][2],
                             class_names, show_numbers)

        # Difference matrix
        diff = results[1][1] - results[0][1]
        n = results[0][2]
        im_diff = axes[2].imshow(diff, cmap="RdBu_r", vmin=-0.3, vmax=0.3, aspect="equal")

        if class_names and n <= 40:
            axes[2].set_xticks(range(n))
            axes[2].set_yticks(range(n))
            fontsize = max(5, 9 - n // 5)
            axes[2].set_xticklabels(class_names, rotation=90, fontsize=fontsize)
            axes[2].set_yticklabels(class_names, fontsize=fontsize)
        else:
            axes[2].set_xlabel("Predicted class")
            axes[2].set_ylabel("True class")

        axes[2].set_title(f"Difference ({labels[1]} − {labels[0]})")

        if show_numbers:
            for i in range(n):
                for j in range(n):
                    val = diff[i, j]
                    if abs(val) > 0.03:
                        axes[2].text(j, i, f"{val:+.2f}",
                                     ha="center", va="center",
                                     color="white" if abs(val) > 0.15 else "black",
                                     fontsize=max(4, 8 - n // 5))

        fig.colorbar(im, ax=axes[:2], label="Recall", shrink=0.8, location="right")
        fig.colorbar(im_diff, ax=axes[2], label="Δ Recall", shrink=0.8)

    else:
        print("Provide 1 or 2 datasets", file=sys.stderr)
        sys.exit(1)

    plt.savefig(args.output, dpi=300, bbox_inches="tight")
    print(f"Saved {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
