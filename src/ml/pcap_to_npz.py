#!/usr/bin/env python3
"""
Convert Shadow pcap files to WFlib .npz format for Website Fingerprinting.

Uses the schedule.json produced by generate-wf-config.py to know exactly
which page was fetched at which time on which monitor. Each monitor fetches
one page at a time, so each time window in the pcap = one labeled sample.

The output .npz can be used for BOTH training and testing — WFlib's
dataset_split.py handles the train/valid/test split.

Usage:
    python3 pcap_to_npz.py \\
        --schedule shadow.config.schedule.json \\
        --shadow-data shadow.data/ \\
        --output datasets/my_experiment.npz

    # Then in WFlib:
    python3 exp/dataset_process/dataset_split.py --dataset my_experiment

Dependencies:
    pip install dpkt  (recommended, faster)
    or: pip install scapy
"""

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

try:
    import dpkt
    HAS_DPKT = True
except ImportError:
    HAS_DPKT = False

try:
    from scapy.all import rdpcap, IP, TCP
    HAS_SCAPY = True
except ImportError:
    HAS_SCAPY = False


def read_pcap(pcap_path):
    """Read pcap, return list of {ts, src_ip, dst_ip, length} dicts."""
    packets = []

    if HAS_DPKT:
        with open(pcap_path, "rb") as f:
            reader = dpkt.pcap.Reader(f)
            linktype = reader.datalink()
            for ts, buf in reader:
                try:
                    # Shadow writes raw IP (link type 101), not Ethernet.
                    # dpkt.pcap.DLT_RAW is 12, but the actual value is 101.
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
                        "length": len(buf),
                    })
                except Exception:
                    continue
    elif HAS_SCAPY:
        for pkt in rdpcap(str(pcap_path)):
            if IP in pkt and TCP in pkt:
                packets.append({
                    "ts": float(pkt.time),
                    "src_ip": pkt[IP].src,
                    "dst_ip": pkt[IP].dst,
                    "length": len(pkt),
                })
    else:
        logging.error("Install dpkt or scapy: pip install dpkt")
        sys.exit(1)

    packets.sort(key=lambda p: p["ts"])
    logging.info(f"Read {len(packets)} TCP packets from {pcap_path}")
    return packets


def detect_client_ip(packets):
    """Client IP = most frequent source."""
    counts = defaultdict(int)
    for p in packets:
        counts[p["src_ip"]] += 1
    client_ip = max(counts, key=counts.get)
    logging.info(f"Client IP: {client_ip}")
    return client_ip


def extract_directions(packets, client_ip, start_ts, end_ts, seq_len=5000):
    """
    Extract packet direction sequence for a time window.
    +1 = outgoing (client -> network), -1 = incoming (network -> client).
    """
    dirs = []
    for p in packets:
        if p["ts"] < start_ts:
            continue
        if p["ts"] >= end_ts:
            break
        dirs.append(1.0 if p["src_ip"] == client_ip else -1.0)

    seq = np.zeros(seq_len, dtype=np.float32)
    n = min(len(dirs), seq_len)
    seq[:n] = dirs[:n]
    return seq, len(dirs)


def find_pcap(shadow_data_dir, monitor_name):
    """Find pcap file for a monitor.

    Looks in several possible locations, in order:
      1. <shadow_data>/hosts/<name>/*.pcap   (standard Shadow layout)
      2. <shadow_data>/../pcaps/<name>_*.pcap (flat layout from old pull-results)
      3. <shadow_data>/pcaps/<name>_*.pcap   (same, but pcaps/ inside shadow.data)
    """
    shadow_data = Path(shadow_data_dir)

    # Layout 1: standard Shadow hosts/ tree
    # Prefer eth0.pcap (real network traffic) over lo.pcap (loopback, no Tor).
    host_dir = shadow_data / "hosts" / monitor_name
    if host_dir.exists():
        eth0 = host_dir / "eth0.pcap"
        if eth0.exists():
            return eth0
        pcaps = [p for p in host_dir.glob("*.pcap") if p.name != "lo.pcap"]
        if pcaps:
            return pcaps[0]

    # Layouts 2 & 3: flat pcaps/ directory
    for flat in (shadow_data.parent / "pcaps", shadow_data / "pcaps"):
        if flat.exists():
            hits = list(flat.glob(f"{monitor_name}_*.pcap"))
            if hits:
                return hits[0]

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Convert Shadow monitor pcaps to WFlib .npz"
    )
    parser.add_argument("--schedule", required=True,
                        help="schedule.json from generate-wf-config.py")
    parser.add_argument("--shadow-data", required=True,
                        help="Path to shadow.data/ directory")
    parser.add_argument("--output", required=True, help="Output .npz path")
    parser.add_argument("--seq-len", type=int, default=5000,
                        help="Direction sequence length (default: 5000)")
    parser.add_argument("--min-packets", type=int, default=10,
                        help="Min packets per sample (default: 10)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    # Load schedule
    with open(args.schedule) as f:
        meta = json.load(f)

    visit_interval = meta["visit_interval"]
    monitors = meta["monitors"]

    all_sequences = []
    all_ports = []
    total_skipped = 0

    for monitor_name, visits in monitors.items():
        pcap_path = find_pcap(args.shadow_data, monitor_name)
        if pcap_path is None:
            logging.warning(f"No pcap for {monitor_name}, skipping")
            continue

        logging.info(f"Processing {monitor_name} ({len(visits)} visits)...")
        packets = read_pcap(pcap_path)
        if not packets:
            logging.warning(f"Empty pcap for {monitor_name}")
            continue

        client_ip = detect_client_ip(packets)
        skipped = 0

        for visit in visits:
            start = visit["start_time"]
            end = start + visit_interval

            seq, n_pkts = extract_directions(
                packets, client_ip, start, end, args.seq_len
            )

            if n_pkts < args.min_packets:
                skipped += 1
                continue

            all_sequences.append(seq)
            all_ports.append(visit["port"])

        logging.info(f"  {monitor_name}: {len(visits) - skipped} samples, "
                     f"{skipped} skipped (< {args.min_packets} packets)")
        total_skipped += skipped

    if not all_sequences:
        logging.error("No samples extracted!")
        sys.exit(1)

    X = np.array(all_sequences, dtype=np.float32)
    y_raw = np.array(all_ports, dtype=np.int64)

    # Check if open-world mode: monitored_ports in schedule.json
    monitored_ports = meta.get("monitored_ports")
    is_open_world = meta.get("open_world", False) and monitored_ports

    if is_open_world:
        # Open-world labeling: monitored ports → class 0..M-1,
        # all unmonitored ports → class M ("other").
        monitored_set = set(monitored_ports)
        m = len(monitored_ports)
        monitored_port_to_label = {p: i for i, p in enumerate(sorted(monitored_set))}

        y = np.array([
            monitored_port_to_label[p] if p in monitored_set else m
            for p in y_raw
        ], dtype=np.int64)

        n_monitored = int((y < m).sum())
        n_unmonitored = int((y == m).sum())
        n_classes = m + 1
        logging.info(f"Open-world: {m} monitored classes + 1 'other' class")
        logging.info(f"  Monitored samples: {n_monitored}, Unmonitored: {n_unmonitored}")

        port_to_label = {int(p): int(l) for p, l in monitored_port_to_label.items()}
        port_to_label["other"] = m
    else:
        # Closed-world: remap ports to contiguous labels 0..N-1
        unique_ports = sorted(set(y_raw))
        port_to_label = {port: idx for idx, port in enumerate(unique_ports)}
        y = np.array([port_to_label[p] for p in y_raw], dtype=np.int64)
        n_classes = len(unique_ports)

    logging.info(f"Total samples: {len(X)}")
    logging.info(f"Total skipped: {total_skipped}")
    logging.info(f"Classes: {n_classes}")
    counts = np.bincount(y)
    logging.info(f"Samples/class: min={counts.min()}, max={counts.max()}, "
                 f"mean={counts.mean():.1f}")

    # Save dataset
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.output, X=X, y=y)
    logging.info(f"Saved {args.output} (X: {X.shape}, y: {y.shape})")

    # Save label mapping
    label_path = Path(args.output).with_suffix(".labels.json")
    with open(label_path, "w") as f:
        json.dump({
            "port_to_label": {str(k): int(v) for k, v in port_to_label.items()},
            "num_classes": n_classes,
            "open_world": is_open_world,
            "monitored_ports": monitored_ports if is_open_world else None,
        }, f, indent=2)
    logging.info(f"Saved {label_path}")


if __name__ == "__main__":
    main()
