#!/usr/bin/env python3
"""
correlation.py — Pcap-based end-to-end traffic correlation attack for Shadow Tor simulations.

Adversary model: controls/observes both an entry guard AND an exit relay.
Correlates packet timing between the encrypted entry-side traffic (monitor pcaps)
and the cleartext exit-side traffic (exit relay pcaps) to confirm that two flows
belong to the same Tor circuit.

This is a simplified approach that avoids patching Tor:
- Entry side: monitor pcaps (client <-> guard, encrypted)
- Exit side: exit relay pcaps (exit <-> zimserver, cleartext HTTP)
- Ground truth: schedule.json tells us which monitor fetched which page when

Usage:
    python3 correlation.py \\
        --schedule ../simulation/exp-corr/shadow.config.schedule.json \\
        --shadow-data ../simulation/exp-corr/results/shadow.data/ \\
        --output results/correlation/

Dependencies: numpy, scipy, matplotlib, dpkt
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np

try:
    import dpkt
    HAS_DPKT = True
except ImportError:
    HAS_DPKT = False

from scipy import stats, signal, spatial
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ─── Data structures ─────────────────────────────────────────────────────────

@dataclass
class Flow:
    """A traffic flow extracted from a pcap for a specific time window."""
    source: str        # monitor name or relay name
    window_start: float
    window_end: float
    port: int          # destination port (page identifier)
    packets: list      # [{ts, src_ip, dst_ip, length}, ...]
    bins: Optional[np.ndarray] = None  # binned packet counts

@dataclass
class Pair:
    """An entry-exit flow pair for correlation analysis."""
    entry: Flow
    exit_flow: Flow
    is_true: bool      # ground truth: same circuit?
    scores: dict = field(default_factory=dict)


# ─── Pcap reading (standalone copy, does not import from pcap_to_npz.py) ─────

def read_pcap(pcap_path):
    """Read pcap file, return list of {ts, src_ip, dst_ip, length} dicts."""
    if not HAS_DPKT:
        logging.error("dpkt not installed: pip install dpkt")
        return []

    packets = []
    with open(pcap_path, "rb") as f:
        reader = dpkt.pcap.Reader(f)
        linktype = reader.datalink()
        for ts, buf in reader:
            try:
                if linktype in (101, dpkt.pcap.DLT_RAW):
                    ip = dpkt.ip.IP(buf)
                elif linktype == dpkt.pcap.DLT_EN10MB:
                    eth = dpkt.ethernet.Ethernet(buf)
                    if not isinstance(eth.data, dpkt.ip.IP):
                        continue
                    ip = eth.data
                else:
                    continue

                if not isinstance(ip.data, dpkt.tcp.TCP):
                    continue
                packets.append({
                    "ts": ts,
                    "src_ip": ".".join(str(b) for b in ip.src),
                    "dst_ip": ".".join(str(b) for b in ip.dst),
                    "src_port": ip.data.sport,
                    "dst_port": ip.data.dport,
                    "length": len(buf),
                })
            except Exception:
                continue

    packets.sort(key=lambda p: p["ts"])
    return packets


# ─── Pcap discovery ──────────────────────────────────────────────────────────

def find_monitor_pcaps(shadow_data_dir):
    """Find eth0.pcap for each monitor host (for WF-style entry side)."""
    result = {}
    hosts_dir = Path(shadow_data_dir) / "hosts"
    if not hosts_dir.exists():
        return result
    for d in sorted(hosts_dir.iterdir()):
        if d.name.startswith("monitor") and d.is_dir():
            pcap = d / "eth0.pcap"
            if pcap.exists():
                result[d.name] = pcap
    return result


def find_guard_pcaps(shadow_data_dir, guard_relay_names=None):
    """Find eth0.pcap for guard relay hosts (entry side of correlation attack).

    The adversary controls a guard relay and sees all encrypted traffic from
    clients passing through it — this is the realistic entry-side view.
    """
    result = {}
    hosts_dir = Path(shadow_data_dir) / "hosts"
    if not hosts_dir.exists():
        return result
    for d in sorted(hosts_dir.iterdir()):
        if not d.is_dir():
            continue
        if guard_relay_names:
            if d.name in guard_relay_names:
                pcap = d / "eth0.pcap"
                if pcap.exists():
                    result[d.name] = pcap
        elif "guard" in d.name.lower() and d.name.startswith("relay") and "exit" not in d.name.lower():
            pcap = d / "eth0.pcap"
            if pcap.exists():
                result[d.name] = pcap
    return result


def find_exit_pcaps(shadow_data_dir, exit_relay_names=None):
    """Find eth0.pcap for exit relay hosts."""
    result = {}
    hosts_dir = Path(shadow_data_dir) / "hosts"
    if not hosts_dir.exists():
        return result
    for d in sorted(hosts_dir.iterdir()):
        if not d.is_dir():
            continue
        # Match by explicit list, or by naming convention
        if exit_relay_names:
            if d.name in exit_relay_names:
                pcap = d / "eth0.pcap"
                if pcap.exists():
                    result[d.name] = pcap
        elif "exit" in d.name.lower() and d.name.startswith("relay"):
            pcap = d / "eth0.pcap"
            if pcap.exists():
                result[d.name] = pcap
    return result


# ─── Binning ─────────────────────────────────────────────────────────────────

def bin_packets(packets, start_ts, end_ts, bin_size=0.1):
    """Count packets per time bin within [start_ts, end_ts).

    Returns a 1D numpy array of packet counts per bin.
    """
    duration = end_ts - start_ts
    n_bins = max(1, int(duration / bin_size))
    bins = np.zeros(n_bins, dtype=np.float64)

    for pkt in packets:
        t = pkt["ts"]
        if t < start_ts or t >= end_ts:
            continue
        idx = min(int((t - start_ts) / bin_size), n_bins - 1)
        bins[idx] += 1.0

    return bins


# ─── Flow segmentation ──────────────────────────────────────────────────────

def segment_entry_flows_from_monitors(monitor_pcaps, schedule, visit_interval):
    """Segment monitor pcaps into per-visit entry flows (WF-style, uses schedule)."""
    flows = []
    monitors = schedule.get("monitors", {})

    for monitor_name, pcap_path in monitor_pcaps.items():
        if monitor_name not in monitors:
            continue

        logging.info(f"Reading entry pcap (monitor): {monitor_name}")
        packets = read_pcap(str(pcap_path))
        if not packets:
            logging.warning(f"Empty pcap for {monitor_name}")
            continue

        visits = monitors[monitor_name]
        for visit in visits:
            start = visit["start_time"]
            end = start + visit_interval
            port = visit["port"]

            window_pkts = [p for p in packets if start <= p["ts"] < end]
            if len(window_pkts) < 10:
                continue

            flows.append(Flow(
                source=monitor_name,
                window_start=start,
                window_end=end,
                port=port,
                packets=window_pkts,
            ))

    logging.info(f"Segmented {len(flows)} entry flows (from monitors)")
    return flows


def segment_entry_flows_from_guards(guard_pcaps, schedule, visit_interval):
    """Segment guard relay pcaps into per-client, per-window entry flows.

    The adversary controls a guard relay and sees encrypted traffic from all
    clients. They can distinguish clients by source IP. For each client IP
    that matches a known monitor IP, extract traffic in each time window.

    We use the schedule to know the time windows (the adversary wouldn't know
    these in practice, but for our evaluation we need ground truth to build
    true/false pairs). In a real attack, the adversary would use sliding
    windows or traffic burst detection.
    """
    # Collect all monitor IPs from the schedule — these are the clients we
    # want to track. We detect them from the guard pcap by looking at which
    # IPs send traffic on port 9001 (Tor OR port).
    all_windows = []
    for monitor_name, visits in schedule.get("monitors", {}).items():
        for visit in visits:
            all_windows.append({
                "monitor": monitor_name,
                "start_time": visit["start_time"],
                "port": visit["port"],
            })

    flows = []
    for guard_name, pcap_path in guard_pcaps.items():
        logging.info(f"Reading entry pcap (guard): {guard_name}")
        packets = read_pcap(str(pcap_path))
        if not packets:
            logging.warning(f"Empty pcap for {guard_name}")
            continue

        logging.info(f"  {guard_name}: {len(packets)} packets total")

        # Group packets by source/dest IP that are NOT the guard itself.
        # The guard's own IP is the most common dst_ip (clients connect TO it).
        ip_counts = defaultdict(int)
        for p in packets:
            ip_counts[p["dst_ip"]] += 1
        guard_ip = max(ip_counts, key=ip_counts.get) if ip_counts else None

        if not guard_ip:
            continue

        # Find client IPs: sources that send TO the guard IP
        client_ips = set()
        for p in packets:
            if p["dst_ip"] == guard_ip:
                client_ips.add(p["src_ip"])

        logging.info(f"  {guard_name}: guard IP={guard_ip}, "
                     f"{len(client_ips)} client IPs detected")

        # For each time window, extract per-client traffic
        for window in all_windows:
            start = window["start_time"]
            end = start + visit_interval
            port = window["port"]

            for client_ip in client_ips:
                # All packets between this client and the guard in this window
                window_pkts = [
                    p for p in packets
                    if start <= p["ts"] < end
                    and (p["src_ip"] == client_ip or p["dst_ip"] == client_ip)
                ]

                if len(window_pkts) < 10:
                    continue

                flows.append(Flow(
                    source=f"{guard_name}:{client_ip}",
                    window_start=start,
                    window_end=end,
                    port=port,
                    packets=window_pkts,
                ))

    logging.info(f"Segmented {len(flows)} entry flows (from guards)")
    return flows


def segment_exit_flows(exit_pcaps, zimserver_ip, schedule, visit_interval):
    """Segment exit relay pcaps into per-window flows filtered by zimserver traffic.

    For each time window in the schedule, extract exit-relay packets that go
    to/from the zimserver IP on the relevant port.
    """
    # Collect all unique (start_time, port) windows across all monitors
    all_windows = set()
    for monitor_name, visits in schedule.get("monitors", {}).items():
        for visit in visits:
            all_windows.add((visit["start_time"], visit["port"]))

    # Read all exit relay pcaps
    exit_packets_by_relay = {}
    for relay_name, pcap_path in exit_pcaps.items():
        logging.info(f"Reading exit pcap: {relay_name}")
        packets = read_pcap(str(pcap_path))
        # Pre-filter: only packets involving the zimserver IP
        zim_packets = [p for p in packets
                       if p["src_ip"] == zimserver_ip or p["dst_ip"] == zimserver_ip]
        exit_packets_by_relay[relay_name] = zim_packets
        logging.info(f"  {relay_name}: {len(zim_packets)} zimserver packets "
                     f"(of {len(packets)} total)")

    # For each window, find exit flows on each relay
    flows = []
    for start_time, port in sorted(all_windows):
        end_time = start_time + visit_interval

        for relay_name, packets in exit_packets_by_relay.items():
            # Filter by time window AND destination port
            window_pkts = [
                p for p in packets
                if start_time <= p["ts"] < end_time
                and (p["dst_port"] == port or p["src_port"] == port)
            ]

            if len(window_pkts) < 5:
                continue

            flows.append(Flow(
                source=relay_name,
                window_start=start_time,
                window_end=end_time,
                port=port,
                packets=window_pkts,
            ))

    logging.info(f"Segmented {len(flows)} exit flows")
    return flows


# ─── Pair construction ───────────────────────────────────────────────────────

def build_pairs(entry_flows, exit_flows, false_ratio=10, seed=42):
    """Build true and false pairs for correlation evaluation.

    True pair: entry flow and exit flow with the same time window + port.
    False pair: entry flow paired with a random exit flow from a different
    window or different port.
    """
    rng = np.random.RandomState(seed)

    # Index exit flows by (window_start, port)
    exit_index = defaultdict(list)
    for ef in exit_flows:
        exit_index[(ef.window_start, ef.port)].append(ef)

    true_pairs = []
    for entry in entry_flows:
        key = (entry.window_start, entry.port)
        matching_exits = exit_index.get(key, [])
        for exit_f in matching_exits:
            true_pairs.append(Pair(entry=entry, exit_flow=exit_f, is_true=True))

    logging.info(f"True pairs: {len(true_pairs)}")

    # Build false pairs: for each true pair's entry flow, sample random exits
    false_pairs = []
    all_exit_keys = list(exit_index.keys())
    for pair in true_pairs:
        n_false = min(false_ratio, len(all_exit_keys) - 1)
        for _ in range(n_false):
            # Pick a random exit flow from a different window/port
            while True:
                rand_key = all_exit_keys[rng.randint(len(all_exit_keys))]
                if rand_key != (pair.entry.window_start, pair.entry.port):
                    break
            rand_exits = exit_index[rand_key]
            rand_exit = rand_exits[rng.randint(len(rand_exits))]
            false_pairs.append(Pair(entry=pair.entry, exit_flow=rand_exit, is_true=False))

    logging.info(f"False pairs: {len(false_pairs)}")
    return true_pairs + false_pairs


# ─── Correlation metrics ─────────────────────────────────────────────────────

def compute_pearson(a, b):
    """Pearson correlation coefficient between two bin vectors."""
    if np.std(a) == 0 or np.std(b) == 0:
        return 0.0
    r, _ = stats.pearsonr(a, b)
    return float(r)


def compute_cosine(a, b):
    """Cosine similarity between two bin vectors."""
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(1.0 - spatial.distance.cosine(a, b))


def compute_xcorr(a, b, max_lag_bins=100):
    """Maximum normalized cross-correlation across a range of lags.

    Returns (max_correlation, best_lag_in_bins).
    """
    if np.std(a) == 0 or np.std(b) == 0:
        return 0.0, 0

    # Normalize
    a_norm = (a - np.mean(a)) / (np.std(a) * len(a))
    b_norm = (b - np.mean(b)) / np.std(b)

    # Full cross-correlation
    xcorr = signal.correlate(a_norm, b_norm, mode="full")
    mid = len(a) - 1  # zero-lag index

    # Restrict to [-max_lag_bins, +max_lag_bins]
    lo = max(0, mid - max_lag_bins)
    hi = min(len(xcorr), mid + max_lag_bins + 1)
    xcorr_window = xcorr[lo:hi]

    best_idx = np.argmax(xcorr_window)
    best_lag = best_idx - (mid - lo)
    best_val = float(xcorr_window[best_idx])

    return best_val, int(best_lag)


# ─── Evaluation ──────────────────────────────────────────────────────────────

def evaluate_pairs(pairs, bin_size=0.1):
    """Compute correlation scores for all pairs."""
    for pair in pairs:
        entry_bins = bin_packets(pair.entry.packets,
                                pair.entry.window_start, pair.entry.window_end,
                                bin_size)
        exit_bins = bin_packets(pair.exit_flow.packets,
                                pair.exit_flow.window_start, pair.exit_flow.window_end,
                                bin_size)

        pair.scores["pearson"] = compute_pearson(entry_bins, exit_bins)
        pair.scores["cosine"] = compute_cosine(entry_bins, exit_bins)
        xcorr_val, xcorr_lag = compute_xcorr(entry_bins, exit_bins)
        pair.scores["xcorr"] = xcorr_val
        pair.scores["xcorr_lag"] = xcorr_lag

    return pairs


def compute_roc(pairs, metric_name):
    """Compute ROC curve for a given metric."""
    labels = np.array([1 if p.is_true else 0 for p in pairs])
    scores = np.array([p.scores[metric_name] for p in pairs])

    # Sort by score descending
    order = np.argsort(-scores)
    labels = labels[order]
    scores = scores[order]

    n_pos = labels.sum()
    n_neg = len(labels) - n_pos

    if n_pos == 0 or n_neg == 0:
        return {"fpr": [0, 1], "tpr": [0, 1], "auc": 0.5,
                "tpr_at_fpr_001": 0.0, "tpr_at_fpr_0001": 0.0}

    # Manual ROC computation
    tpr_list = [0.0]
    fpr_list = [0.0]
    tp = 0
    fp = 0

    for label in labels:
        if label == 1:
            tp += 1
        else:
            fp += 1
        tpr_list.append(tp / n_pos)
        fpr_list.append(fp / n_neg)

    tpr_arr = np.array(tpr_list)
    fpr_arr = np.array(fpr_list)

    # AUC via trapezoidal rule
    auc = float(np.trapz(tpr_arr, fpr_arr))

    # TPR at specific FPR thresholds
    def tpr_at_fpr(threshold):
        idx = np.searchsorted(fpr_arr, threshold)
        if idx >= len(tpr_arr):
            return float(tpr_arr[-1])
        return float(tpr_arr[idx])

    return {
        "fpr": fpr_arr.tolist(),
        "tpr": tpr_arr.tolist(),
        "auc": auc,
        "tpr_at_fpr_001": tpr_at_fpr(0.01),
        "tpr_at_fpr_0001": tpr_at_fpr(0.001),
    }


# ─── Plotting ────────────────────────────────────────────────────────────────

def plot_roc_curves(roc_results, output_path):
    """Plot ROC curves for all metrics on one figure."""
    fig, ax = plt.subplots(figsize=(8, 6))

    for metric_name, roc in roc_results.items():
        if metric_name == "xcorr_lag":
            continue
        ax.plot(roc["fpr"], roc["tpr"],
                label=f'{metric_name} (AUC={roc["auc"]:.3f})')

    ax.plot([0, 1], [0, 1], "k--", alpha=0.3, label="Random")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("Traffic Correlation Attack — ROC Curves")
    ax.legend()
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)

    plt.tight_layout()
    for ext in [".pdf", ".svg", ".png"]:
        plt.savefig(str(output_path).replace(".pdf", ext), dpi=300, bbox_inches="tight")
    logging.info(f"Saved ROC plot: {output_path}")


def plot_score_distributions(pairs, output_path):
    """Plot histograms of correlation scores for true vs false pairs."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for ax, metric in zip(axes, ["pearson", "cosine", "xcorr"]):
        true_scores = [p.scores[metric] for p in pairs if p.is_true]
        false_scores = [p.scores[metric] for p in pairs if not p.is_true]

        ax.hist(false_scores, bins=50, alpha=0.6, label="False pairs", color="salmon", density=True)
        ax.hist(true_scores, bins=50, alpha=0.6, label="True pairs", color="steelblue", density=True)
        ax.set_xlabel(f"{metric} score")
        ax.set_ylabel("Density")
        ax.set_title(metric.capitalize())
        ax.legend()

    plt.suptitle("Score Distributions: True vs False Pairs", fontsize=14)
    plt.tight_layout()
    for ext in [".pdf", ".svg", ".png"]:
        plt.savefig(str(output_path).replace(".pdf", ext), dpi=300, bbox_inches="tight")
    logging.info(f"Saved score distributions: {output_path}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Pcap-based traffic correlation attack analysis"
    )
    parser.add_argument("--schedule", required=True,
                        help="schedule.json from generate-wf-config.py")
    parser.add_argument("--shadow-data", required=True,
                        help="Path to shadow.data/ directory")
    parser.add_argument("--output", required=True,
                        help="Output directory for results")
    parser.add_argument("--bin-size", type=float, default=0.1,
                        help="Bin size in seconds (default: 0.1 = 100ms)")
    parser.add_argument("--false-ratio", type=int, default=10,
                        help="False pairs per true pair (default: 10)")
    parser.add_argument("--zimserver-ip", default=None,
                        help="Zimserver IP (auto-detected from schedule.json)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    # Load schedule
    with open(args.schedule) as f:
        schedule = json.load(f)

    visit_interval = schedule["visit_interval"]
    zimserver_ip = args.zimserver_ip or schedule.get("zimserver_ip", "129.114.108.192")
    exit_relay_names = schedule.get("exit_pcap_relays")
    guard_relay_names = schedule.get("guard_pcap_relays")

    logging.info(f"Visit interval: {visit_interval}s")
    logging.info(f"Zimserver IP: {zimserver_ip}")
    logging.info(f"Exit relay names: {exit_relay_names}")
    logging.info(f"Guard relay names: {guard_relay_names}")

    # Find pcaps — entry side: prefer guard relays, fall back to monitors
    guard_pcaps = find_guard_pcaps(args.shadow_data, guard_relay_names)
    monitor_pcaps = find_monitor_pcaps(args.shadow_data)
    exit_pcaps = find_exit_pcaps(args.shadow_data, exit_relay_names)

    logging.info(f"Found {len(guard_pcaps)} guard relay pcaps")
    logging.info(f"Found {len(monitor_pcaps)} monitor pcaps")
    logging.info(f"Found {len(exit_pcaps)} exit relay pcaps")

    if not exit_pcaps:
        logging.error("No exit relay pcaps found! "
                      "Did you run the simulation with --correlation?")
        sys.exit(1)

    # Segment entry flows — use guard pcaps (realistic adversary) if available,
    # otherwise fall back to monitor pcaps (WF-style, less realistic)
    if guard_pcaps:
        logging.info("Using guard relay pcaps for entry side (realistic adversary model)")
        entry_flows = segment_entry_flows_from_guards(
            guard_pcaps, schedule, visit_interval)
    elif monitor_pcaps:
        logging.info("Using monitor pcaps for entry side (fallback, less realistic)")
        entry_flows = segment_entry_flows_from_monitors(
            monitor_pcaps, schedule, visit_interval)
    else:
        logging.error("No entry-side pcaps found (need guard or monitor pcaps)!")
        sys.exit(1)

    # Segment exit flows
    exit_flows = segment_exit_flows(exit_pcaps, zimserver_ip, schedule, visit_interval)

    if not entry_flows:
        logging.error("No entry flows extracted!")
        sys.exit(1)
    if not exit_flows:
        logging.error("No exit flows extracted! Check zimserver IP and exit relay pcaps.")
        sys.exit(1)

    # Build pairs
    pairs = build_pairs(entry_flows, exit_flows,
                        false_ratio=args.false_ratio, seed=args.seed)

    true_count = sum(1 for p in pairs if p.is_true)
    false_count = sum(1 for p in pairs if not p.is_true)
    logging.info(f"Total pairs: {len(pairs)} ({true_count} true, {false_count} false)")

    if true_count == 0:
        logging.error("No true pairs found! Entry and exit flows don't match. "
                      "Check zimserver IP and schedule alignment.")
        sys.exit(1)

    # Evaluate
    logging.info(f"Computing correlation scores (bin_size={args.bin_size}s)...")
    evaluate_pairs(pairs, bin_size=args.bin_size)

    # Compute ROC curves
    roc_results = {}
    for metric in ["pearson", "cosine", "xcorr"]:
        roc_results[metric] = compute_roc(pairs, metric)
        logging.info(f"  {metric}: AUC={roc_results[metric]['auc']:.4f}, "
                     f"TPR@FPR=0.01={roc_results[metric]['tpr_at_fpr_001']:.4f}, "
                     f"TPR@FPR=0.001={roc_results[metric]['tpr_at_fpr_0001']:.4f}")

    # Save results
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # JSON summary
    summary = {
        "bin_size": args.bin_size,
        "false_ratio": args.false_ratio,
        "n_entry_flows": len(entry_flows),
        "n_exit_flows": len(exit_flows),
        "n_true_pairs": true_count,
        "n_false_pairs": false_count,
        "metrics": {
            metric: {
                "auc": roc["auc"],
                "tpr_at_fpr_001": roc["tpr_at_fpr_001"],
                "tpr_at_fpr_0001": roc["tpr_at_fpr_0001"],
            }
            for metric, roc in roc_results.items()
        },
    }
    with open(out_dir / "correlation_results.json", "w") as f:
        json.dump(summary, f, indent=2)

    # ROC data CSV
    with open(out_dir / "roc_data.csv", "w") as f:
        f.write("metric,fpr,tpr\n")
        for metric, roc in roc_results.items():
            for fpr, tpr in zip(roc["fpr"], roc["tpr"]):
                f.write(f"{metric},{fpr:.6f},{tpr:.6f}\n")

    # Plots
    plot_roc_curves(roc_results, out_dir / "roc_curves.pdf")
    plot_score_distributions(pairs, out_dir / "score_distributions.pdf")

    # Print summary
    print("\n" + "=" * 60)
    print("  Traffic Correlation Attack Results")
    print("=" * 60)
    print(f"  Entry flows:  {len(entry_flows)}")
    print(f"  Exit flows:   {len(exit_flows)}")
    print(f"  True pairs:   {true_count}")
    print(f"  False pairs:  {false_count}")
    print()
    print(f"  {'Metric':<12s}  {'AUC':>8s}  {'TPR@FPR=1%':>12s}  {'TPR@FPR=0.1%':>14s}")
    print(f"  {'─'*50}")
    for metric in ["pearson", "cosine", "xcorr"]:
        r = roc_results[metric]
        print(f"  {metric:<12s}  {r['auc']:>8.4f}  {r['tpr_at_fpr_001']:>12.4f}  "
              f"{r['tpr_at_fpr_0001']:>14.4f}")
    print()
    print(f"  Results saved to {out_dir}/")


if __name__ == "__main__":
    main()
