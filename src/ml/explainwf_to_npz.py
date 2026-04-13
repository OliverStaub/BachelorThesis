#!/usr/bin/env python3
"""
Convert explainwf-popets2023 cell trace data (GWF format) to WFlib .npz format.

The GWF format (from Jansen & Wails 2023) has lines like:
    650 GWF {"time_created":..., "port":PORT, "cells":[[time, side, direction, cell_cmd, relay_cmd], ...]}

WFlib expects .npz with:
    X: numpy array (n_samples, seq_len) of direction*timestamp values
    y: numpy array (n_samples,) of integer class labels

For DF with --feature DIR, only the sign of X matters (+1/-1), but we store
direction * timestamp to keep compatibility with other WFlib models (Tik-Tok, etc).

Usage:
    # Convert a single run:
    python3 explainwf_to_npz.py \
        --traces explainwf-popets2023/data/fidelity/tornet-net_0.25-load_2.0/run1/wget2-traces.log.xz \
        --urls explainwf-popets2023/data/urls.txt \
        --output datasets/explainwf_run1.npz

    # Convert all 6 fidelity runs concatenated:
    python3 explainwf_to_npz.py \
        --traces explainwf-popets2023/data/fidelity/tornet-net_0.25-load_2.0/run{1..6}/wget2-traces.log.xz \
        --urls explainwf-popets2023/data/urls.txt \
        --output datasets/explainwf_all.npz

    # Direction-only mode (for DF):
    python3 explainwf_to_npz.py --direction-only ...
"""

import argparse
import json
import lzma
import logging
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np


# Cell tuple indices (from common.py)
IDX_TIME = 0
IDX_SIDE = 1
IDX_DIRECTION = 2
IDX_CELL_CMD = 3
IDX_RELAY_CMD = 4

# Direction constants
DIR_CLIENT_TO_SERVER = 0  # outgoing
DIR_SERVER_TO_CLIENT = 1  # incoming


def read_url_file(filepath):
    """Read urls.txt -> {port: page_name}"""
    port2page = {}
    with open(filepath) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 3:
                port = int(parts[1])
                url = parts[2]
                page = url.split("/")[-1]
                port2page[port] = page
    return port2page


def read_trace_file(filepath):
    """Read a GWF trace file (supports .xz compression). Yields (port, record) tuples."""
    path = Path(filepath)
    if path.suffix == ".xz":
        opener = lzma.open
    else:
        opener = open

    with opener(filepath, "rt") as f:
        for line_num, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                fields = line.split(maxsplit=2)
                if fields[1] != "GWF":
                    continue
                record = json.loads(fields[2])
                yield record["port"], record
            except (IndexError, json.JSONDecodeError, KeyError) as e:
                logging.debug(f"Skipping line {line_num}: {e}")


def extract_direction_sequence(cells, seq_len=5000, direction_only=False):
    """
    Extract a direction sequence from cell data.

    If direction_only: returns +1 (outgoing) / -1 (incoming), zero-padded.
    Otherwise: returns direction * timestamp (WFlib DT format), zero-padded.
    """
    seq = np.zeros(seq_len, dtype=np.float32)
    n = min(len(cells), seq_len)

    for i in range(n):
        cell = cells[i]
        direction = cell[IDX_DIRECTION]
        timestamp = cell[IDX_TIME]

        # Map: 0 (client->server) = +1 (outgoing), 1 (server->client) = -1 (incoming)
        dir_sign = 1.0 if direction == DIR_CLIENT_TO_SERVER else -1.0

        if direction_only:
            seq[i] = dir_sign
        else:
            # Store direction * timestamp (WFlib convention)
            # Use abs(timestamp) to avoid negative zero issues
            seq[i] = dir_sign * abs(timestamp) if timestamp != 0.0 else dir_sign * 0.001

    return seq


def main():
    parser = argparse.ArgumentParser(
        description="Convert explainwf GWF cell traces to WFlib .npz format"
    )
    parser.add_argument(
        "--traces", nargs="+", required=True,
        help="Path(s) to wget2-traces.log[.xz] files"
    )
    parser.add_argument(
        "--urls", required=True,
        help="Path to urls.txt (port-to-URL mapping)"
    )
    parser.add_argument(
        "--output", required=True,
        help="Output .npz file path"
    )
    parser.add_argument(
        "--seq-len", type=int, default=5000,
        help="Sequence length (default: 5000)"
    )
    parser.add_argument(
        "--direction-only", action="store_true",
        help="Store only direction (+1/-1) without timestamps"
    )
    parser.add_argument(
        "--min-cells", type=int, default=10,
        help="Minimum cells per record to include (default: 10)"
    )
    parser.add_argument(
        "--exclude-port", type=int, default=9001,
        help="Port to exclude (default: 9001 = background Tor traffic)"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Verbose logging"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    # Read URL mapping
    port2page = read_url_file(args.urls)
    logging.info(f"Loaded {len(port2page)} page URLs from {args.urls}")

    # Build page -> label mapping (sorted for deterministic labels)
    pages = sorted(set(port2page.values()))
    page2label = {page: idx for idx, page in enumerate(pages)}
    logging.info(f"Created {len(page2label)} class labels")

    # Read all traces
    all_sequences = []
    all_labels = []
    port_counts = defaultdict(int)
    skipped = 0

    for trace_path in args.traces:
        logging.info(f"Reading {trace_path}...")
        for port, record in read_trace_file(trace_path):
            # Skip excluded ports
            if port == args.exclude_port:
                continue

            # Skip unknown ports
            if port not in port2page:
                skipped += 1
                continue

            # Skip short records
            cells = record.get("cells", [])
            if len(cells) < args.min_cells:
                skipped += 1
                continue

            # Check minimum packets in each direction
            directions = [c[IDX_DIRECTION] for c in cells]
            n_out = sum(1 for d in directions if d == DIR_CLIENT_TO_SERVER)
            n_in = sum(1 for d in directions if d == DIR_SERVER_TO_CLIENT)
            if n_out < 3 or n_in < 3:
                skipped += 1
                continue

            page = port2page[port]
            label = page2label[page]

            seq = extract_direction_sequence(
                cells, seq_len=args.seq_len, direction_only=args.direction_only
            )

            all_sequences.append(seq)
            all_labels.append(label)
            port_counts[port] += 1

    X = np.array(all_sequences, dtype=np.float32)
    y = np.array(all_labels, dtype=np.int64)

    logging.info(f"Total samples: {len(X)}")
    logging.info(f"Skipped records: {skipped}")
    logging.info(f"Classes: {len(page2label)}")
    logging.info(f"Samples per class: min={np.bincount(y).min()}, max={np.bincount(y).max()}, "
                 f"mean={np.bincount(y).mean():.1f}")
    logging.info(f"Sequence length: {args.seq_len}")
    logging.info(f"Direction only: {args.direction_only}")

    # Save
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.output, X=X, y=y)
    logging.info(f"Saved to {args.output} (X: {X.shape}, y: {y.shape})")

    # Also save label mapping for reference
    label_path = Path(args.output).with_suffix(".labels.json")
    with open(label_path, "w") as f:
        json.dump({"page2label": page2label, "label2page": {v: k for k, v in page2label.items()}}, f, indent=2)
    logging.info(f"Saved label mapping to {label_path}")


if __name__ == "__main__":
    main()
