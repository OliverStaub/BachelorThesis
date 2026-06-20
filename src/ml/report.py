#!/usr/bin/env python3
"""
report.py — Generate a CSV report row for a completed experiment.

Reads metadata from the various output files produced by the pipeline
and prints one CSV row with all tracked values. Can also print a header
row or a markdown table.

Usage:
    # Print CSV header + one row for exp8:
    python3 report.py --experiment exp8 --header

    # Append another experiment:
    python3 report.py --experiment exp9

    # Write a full report for all experiments:
    python3 report.py --all --header > experiments.csv

    # Markdown table (for the thesis):
    python3 report.py --all --markdown
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

# Paths relative to this script's location (src/ml/)
SCRIPT_DIR = Path(__file__).resolve().parent
SIM_DIR = SCRIPT_DIR.parent / "simulation"
WFLIB_DIR = SCRIPT_DIR / "wflib"


COLUMNS = [
    "Experiment",
    "Network Scale",
    "Relays",
    "Directory Authorities",
    "Nodes Total",
    "Monitors (WF Clients)",
    "Pages (classes)",
    "Visits per page",
    "Visit Interval (s)",
    "Circuit Padding",
    "Tor version",
    "Seed",
    "ZIM file",
    "Sim stop_time (s)",
    "Wall-clock time",
    "Total samples",
    "Samples per class",
    "Failed fetches",
    "Failed fetches %",
    "Skipped (too few packets)",
    "Mean packets per sample",
    "Train samples",
    "Valid samples",
    "Test samples",
    "Accuracy",
    "Precision",
    "Recall",
    "F1-score",
    "Training epochs",
    "Best epoch",
    "Random baseline",
    "Notes",
]


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def count_hosts(yaml_path):
    """Count relays, authorities, and total hosts from shadow.config.yaml (simple grep)."""
    relays = 0
    authorities = 0
    total = 0
    try:
        with open(yaml_path) as f:
            for line in f:
                stripped = line.strip()
                # Host entries are top-level keys under hosts: with specific naming
                if stripped.endswith(":") and not stripped.startswith("#"):
                    name = stripped[:-1].strip()
                    if name.startswith("relay"):
                        relays += 1
                        total += 1
                    elif name.startswith("4uthority") or name.startswith("authority"):
                        authorities += 1
                        total += 1
                    elif name.startswith(("markov", "perf", "server", "monitor", "zimserver")):
                        total += 1
    except Exception:
        pass
    return relays, authorities, total


def parse_sim_log(log_path):
    """Extract wall-clock time and failed process count from sim.log."""
    wall_clock = ""
    failed = 0
    try:
        with open(log_path) as f:
            for line in f:
                # Last "Progress:" line has the final failed count
                m = re.search(r"realtime: ([\d:]+).*processes failed: (\d+)", line)
                if m:
                    wall_clock = m.group(1)
                    failed = int(m.group(2))
    except Exception:
        pass
    return wall_clock, failed


def read_padding_setting(conf_dir):
    """Check the torrc files for CircuitPadding and ReducedCircuitPadding.

    tor.wf.torrc is read LAST: shadowctl.py writes the --padding setting there
    and %includes it last in every monitor's torrc-defaults, so its value wins
    (Tor last-value-wins). Reading only the client/common torrcs mislabelled
    --padding off/on/reduced runs as "ON (default)".
    """
    padding_on = None
    reduced = False
    for name in ["tor.client.torrc", "tor.common.torrc", "tor.wf.torrc"]:
        path = conf_dir / name
        try:
            with open(path) as f:
                for line in f:
                    stripped = line.strip().lower()
                    if stripped.startswith("circuitpadding "):
                        val = stripped.split()[-1]
                        padding_on = (val != "0")
                    elif stripped.startswith("reducedcircuitpadding "):
                        val = stripped.split()[-1]
                        reduced = (val == "1")
        except Exception:
            pass
    if padding_on is None:
        return "ON (default)"
    if not padding_on:
        return "OFF"
    if reduced:
        return "Reduced"
    return "ON"


def read_npz_stats(npz_path):
    """Read sample counts from the npz dataset."""
    try:
        import numpy as np
        d = np.load(npz_path)
        X, y = d["X"], d["y"]
        n_classes = len(set(y))
        counts = [int((y == c).sum()) for c in range(n_classes)]
        mean_pkts = int(np.mean([np.count_nonzero(row) for row in X]))
        return {
            "total": len(y),
            "per_class": min(counts),
            "mean_pkts": mean_pkts,
            "n_classes": n_classes,
        }
    except Exception:
        return {}


def read_split_counts(dataset_dir):
    """Read train/valid/test sample counts."""
    counts = {}
    for name in ["train", "valid", "test"]:
        try:
            import numpy as np
            d = np.load(dataset_dir / f"{name}.npz")
            counts[name] = len(d["y"])
        except Exception:
            counts[name] = ""
    return counts


def collect_experiment(name, dataset_override=None):
    """Collect all data for one experiment into a dict."""
    # The experiment directory could be directly under SIM_DIR
    exp_dir = SIM_DIR / name

    # Schedule from config generation
    schedule = read_json(exp_dir / "shadow.config.schedule.json")

    # Shadow config
    config_path = exp_dir / "shadow.config.yaml"
    if not config_path.exists():
        config_path = exp_dir / "results" / "shadow.config.yaml"
    relays, authorities, total_hosts = count_hosts(config_path)

    # Sim log
    sim_log = exp_dir / "results" / "sim.log"
    if not sim_log.exists():
        sim_log = exp_dir / "sim.log"
    wall_clock, failed = parse_sim_log(sim_log)

    # Circuit padding
    conf_dir = exp_dir / "conf"
    padding = read_padding_setting(conf_dir)

    # Dataset stats — WFlib dataset name may differ from experiment name.
    # Try several conventions; --dataset flag overrides all guessing.
    if dataset_override:
        dataset_name = dataset_override
    else:
        # Try: ExpBaseline, Exp-baseline, exp-baseline, expbaseline
        candidates = [
            name,
            name.replace("-", "").capitalize(),
            "".join(w.capitalize() for w in name.split("-")),
            name.capitalize(),
            name.replace("-", ""),
        ]
        dataset_name = name
        for c in candidates:
            if (WFLIB_DIR / "datasets" / f"{c}.npz").exists():
                dataset_name = c
                break
            if (WFLIB_DIR / "logs" / c / "DF" / "result.json").exists():
                dataset_name = c
                break

    npz_path = WFLIB_DIR / "datasets" / f"{dataset_name}.npz"
    npz_stats = read_npz_stats(npz_path)

    # Split counts
    split_dir = WFLIB_DIR / "datasets" / dataset_name
    splits = read_split_counts(split_dir)

    # DF results
    result = read_json(WFLIB_DIR / "logs" / dataset_name / "DF" / "result.json")

    # Number of pages / visits from schedule
    num_pages = schedule.get("num_pages", "")
    visits = schedule.get("visits_per_page", "")
    interval = schedule.get("visit_interval", "")
    n_monitors = len(schedule.get("monitors", {}))

    # Scale — try to infer from host count
    # 0.01 scale ≈ 280 relays, 0.05 ≈ 1400, etc.
    scale = ""
    if relays > 0:
        scale = f"{relays / 7900:.3f}"  # rough estimate

    n_classes = npz_stats.get("n_classes", num_pages or "")
    random_baseline = f"{100 / n_classes:.1f}%" if isinstance(n_classes, int) and n_classes > 0 else ""

    total_samples = npz_stats.get("total", "")
    failed_pct = f"{failed / total_samples * 100:.1f}%" if total_samples and failed else ""

    return {
        "Experiment": name,
        "Network Scale": scale,
        "Relays": relays or "",
        "Directory Authorities": authorities or "",
        "Nodes Total": total_hosts or "",
        "Monitors (WF Clients)": n_monitors or "",
        "Pages (classes)": num_pages,
        "Visits per page": visits,
        "Visit Interval (s)": interval,
        "Circuit Padding": padding,
        "Tor version": "",
        "Seed": 1,
        "ZIM file": "simple_en_maxi_2026-02",
        "Sim stop_time (s)": "",
        "Wall-clock time": wall_clock,
        "Total samples": total_samples,
        "Samples per class": npz_stats.get("per_class", ""),
        "Failed fetches": failed or "",
        "Failed fetches %": failed_pct,
        "Skipped (too few packets)": "",
        "Mean packets per sample": npz_stats.get("mean_pkts", ""),
        "Train samples": splits.get("train", ""),
        "Valid samples": splits.get("valid", ""),
        "Test samples": splits.get("test", ""),
        "Accuracy": f"{result['Accuracy']:.1%}" if "Accuracy" in result else "",
        "Precision": f"{result['Precision']:.1%}" if "Precision" in result else "",
        "Recall": f"{result['Recall']:.1%}" if "Recall" in result else "",
        "F1-score": f"{result['F1-score']:.1%}" if "F1-score" in result else "",
        "Training epochs": 30,
        "Best epoch": "",
        "Random baseline": random_baseline,
        "Notes": "",
    }


def find_experiments():
    """Find all experiment directories that have a schedule.json."""
    experiments = []
    for d in sorted(SIM_DIR.iterdir()):
        if d.is_dir() and (d / "shadow.config.schedule.json").exists():
            experiments.append(d.name)
    return experiments


def print_csv(rows, header=False, file=sys.stdout):
    writer = csv.DictWriter(file, fieldnames=COLUMNS)
    if header:
        writer.writeheader()
    for row in rows:
        writer.writerow(row)


def print_markdown(rows, file=sys.stdout):
    print("| " + " | ".join(COLUMNS) + " |", file=file)
    print("| " + " | ".join("---" for _ in COLUMNS) + " |", file=file)
    for row in rows:
        vals = [str(row.get(c, "")) for c in COLUMNS]
        print("| " + " | ".join(vals) + " |", file=file)


def main():
    parser = argparse.ArgumentParser(description="Generate experiment report")
    parser.add_argument("--experiment", "-e", help="Experiment name (e.g. exp8)")
    parser.add_argument("--dataset", "-d", default=None,
                        help="WFlib dataset name if it differs from experiment name "
                             "(e.g. ExpBaseline for experiment exp-baseline)")
    parser.add_argument("--all", action="store_true", help="Report all experiments")
    parser.add_argument("--header", action="store_true", help="Print CSV header")
    parser.add_argument("--markdown", action="store_true", help="Output as markdown table")
    args = parser.parse_args()

    if args.all:
        names = find_experiments()
        if not names:
            print("No experiments found in", SIM_DIR, file=sys.stderr)
            sys.exit(1)
    elif args.experiment:
        names = [args.experiment]
    else:
        parser.error("Provide --experiment NAME or --all")

    rows = []
    for name in names:
        ds = args.dataset if (args.experiment and args.dataset) else None
        row = collect_experiment(name, dataset_override=ds)
        rows.append(row)

    if args.markdown:
        print_markdown(rows)
    else:
        print_csv(rows, header=args.header)


if __name__ == "__main__":
    main()
