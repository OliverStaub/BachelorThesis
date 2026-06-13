#!/usr/bin/env python3
"""
Measure per-visit traffic overhead from Shadow monitor pcaps.

Reads schedule.json + each monitor's pcap and reports bytes / packets sent
and received during every visit window. Aggregates per-page and per-experiment.
Optionally compares one experiment against a baseline experiment to compute
the overhead introduced by a defense (Circuit Padding, Tamaraw, ...).

Usage:
    # Single experiment summary.
    python3 pcap_overhead.py \\
        --schedule ../simulation/exp-tamaraw-20/shadow.config.schedule.json \\
        --shadow-data ../simulation/exp-tamaraw-20/results/shadow.data/

    # Compare a defended run against a baseline run.
    python3 pcap_overhead.py \\
        --schedule ../simulation/exp-tamaraw-20/shadow.config.schedule.json \\
        --shadow-data ../simulation/exp-tamaraw-20/results/shadow.data/ \\
        --baseline-schedule ../simulation/exp-baseline-20/shadow.config.schedule.json \\
        --baseline-shadow-data ../simulation/exp-baseline-20/results/shadow.data/

    # Emit per-visit CSV for plotting.
    python3 pcap_overhead.py --schedule ... --shadow-data ... --csv overhead.csv
"""

import argparse
import csv
import json
import logging
import statistics
import sys
from pathlib import Path

# Reuse the pcap reader and helpers from pcap_to_npz.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pcap_to_npz import read_pcap, detect_client_ip, find_pcap


def measure_experiment(schedule_path, shadow_data_dir):
    """Return a list of per-visit records for one experiment.

    Each record: {monitor, port, start_time, bytes_up, bytes_down,
                  pkts_up, pkts_down, total_bytes, total_pkts}.
    """
    with open(schedule_path) as f:
        meta = json.load(f)
    visit_interval = meta["visit_interval"]
    monitors = meta["monitors"]

    records = []
    for monitor_name, visits in monitors.items():
        pcap_path = find_pcap(shadow_data_dir, monitor_name)
        if pcap_path is None:
            logging.warning(f"No pcap for {monitor_name}")
            continue

        packets = read_pcap(pcap_path)
        if not packets:
            continue
        client_ip = detect_client_ip(packets)

        for visit in visits:
            start = visit["start_time"]
            end = start + visit_interval
            bytes_up = bytes_down = 0
            pkts_up = pkts_down = 0
            for p in packets:
                if p["ts"] < start:
                    continue
                if p["ts"] >= end:
                    break
                if p["src_ip"] == client_ip:
                    bytes_up += p["length"]
                    pkts_up += 1
                else:
                    bytes_down += p["length"]
                    pkts_down += 1
            records.append({
                "monitor": monitor_name,
                "port": visit["port"],
                "start_time": start,
                "bytes_up": bytes_up,
                "bytes_down": bytes_down,
                "pkts_up": pkts_up,
                "pkts_down": pkts_down,
                "total_bytes": bytes_up + bytes_down,
                "total_pkts": pkts_up + pkts_down,
            })

    return records, meta


def summarise(records, label):
    """Print mean / median / max per-visit stats."""
    if not records:
        print(f"\n[{label}] no records")
        return None

    def stats(values):
        return {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "max": max(values),
            "min": min(values),
        }

    fields = ["bytes_up", "bytes_down", "total_bytes",
              "pkts_up", "pkts_down", "total_pkts"]
    agg = {f: stats([r[f] for r in records]) for f in fields}

    print(f"\n[{label}]  n_visits = {len(records)}")
    print(f"  {'field':<14}{'mean':>14}{'median':>14}{'min':>12}{'max':>14}")
    for f in fields:
        a = agg[f]
        print(f"  {f:<14}{a['mean']:>14,.0f}{a['median']:>14,.0f}"
              f"{a['min']:>12,.0f}{a['max']:>14,.0f}")
    return agg


def compare(defended_agg, baseline_agg):
    """Print overhead pct of defended vs baseline (means)."""
    if not defended_agg or not baseline_agg:
        return
    print(f"\n[overhead: defended vs baseline, mean per visit]")
    print(f"  {'field':<14}{'baseline':>14}{'defended':>14}{'overhead':>14}")
    for f in ["bytes_up", "bytes_down", "total_bytes",
              "pkts_up", "pkts_down", "total_pkts"]:
        b = baseline_agg[f]["mean"]
        d = defended_agg[f]["mean"]
        if b == 0:
            pct = "n/a"
        else:
            pct = f"{((d - b) / b) * 100:+.1f}%"
        print(f"  {f:<14}{b:>14,.0f}{d:>14,.0f}{pct:>14}")


def write_csv(records, csv_path):
    if not records:
        return
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        w.writeheader()
        w.writerows(records)
    print(f"\nWrote {csv_path} ({len(records)} rows)")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--schedule", required=True,
                        help="schedule.json for the experiment under test")
    parser.add_argument("--shadow-data", required=True,
                        help="Path to that experiment's shadow.data/ dir")
    parser.add_argument("--baseline-schedule", default=None,
                        help="Optional baseline schedule.json for overhead comparison")
    parser.add_argument("--baseline-shadow-data", default=None,
                        help="Optional baseline shadow.data/ dir")
    parser.add_argument("--csv", default=None,
                        help="Optional path to write per-visit records as CSV")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    records, meta = measure_experiment(args.schedule, args.shadow_data)
    label = meta.get("defense", {}).get("mode") or "experiment"
    defended_agg = summarise(records, label)

    if args.csv:
        write_csv(records, args.csv)

    if args.baseline_schedule and args.baseline_shadow_data:
        baseline_records, _ = measure_experiment(
            args.baseline_schedule, args.baseline_shadow_data)
        baseline_agg = summarise(baseline_records, "baseline")
        compare(defended_agg, baseline_agg)


if __name__ == "__main__":
    main()
