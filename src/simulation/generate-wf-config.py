#!/usr/bin/env python3
"""
generate-wf-config.py — Add WF experiment nodes to a tornettools-generated shadow config.

Takes an existing shadow.config.yaml (with Tor relays, authorities, etc.) and adds:
- Monitor nodes that fetch pages ONE AT A TIME through Tor using wget2
- ZIM server node(s) serving Wikipedia pages
- pcap capture on each monitor for traffic analysis

Each monitor:
  1. Starts Tor + oniontrace
  2. Fetches page A with wget2 (--page-requisites --max-threads=30)
  3. Waits for the visit window to end
  4. Sends NEWNYM (fresh Tor circuit)
  5. Fetches page B
  6. Repeats for all assigned pages × num_visits

Since each monitor fetches only one page at a time, the pcap can be segmented
by timing to produce labeled samples for training and testing a WF classifier.

Usage:
    python3 generate-wf-config.py \\
        --base-config src/simulation/exp1/shadow.config.yaml \\
        --urls explainwf-popets2023/data/urls.txt \\
        --output src/simulation/exp2/shadow.config.yaml \\
        --num-monitors 5 \\
        --num-pages 20 \\
        --visits-per-page 50
"""

import argparse
import csv
import json
import random
import sys
from pathlib import Path

import yaml


def read_urls(urls_path):
    """Read urls.txt -> list of {ip, port, url} dicts."""
    entries = []
    with open(urls_path) as f:
        reader = csv.reader(f, delimiter=" ")
        for fields in reader:
            if len(fields) == 3:
                entries.append({"ip": fields[0], "port": int(fields[1]), "url": fields[2]})
    return entries


def get_existing_node_ids(config):
    """Collect all network_node_id values already used in the base config.

    Only these IDs are guaranteed to exist in the network graph (atlas_v201801).
    Picking random integers would often hit IDs that aren't in the graph,
    causing Shadow to fail with 'network node id N does not exist'.
    """
    used = []
    for host_config in config.get("hosts", {}).values():
        nid = host_config.get("network_node_id")
        if nid is not None:
            used.append(nid)
    return used


def pick_node_id(existing_ids, rng):
    """Pick a random valid node ID from the base config's existing IDs.

    Shadow allows multiple hosts to share a network_node_id (they're placed
    at the same topology node). So we reuse existing IDs rather than invent
    new ones.
    """
    if not existing_ids:
        raise ValueError("Base config has no hosts with network_node_id — can't pick a valid ID")
    return rng.choice(existing_ids)


WGET2_ARGS_TEMPLATE = (
    "--page-requisites --max-threads=30 --timeout=30 --tries=1 "
    "--no-retry-on-http-error --no-tcp-fastopen --delete-after --quiet "
    '--user-agent="Mozilla/5.0 (Windows NT 10.0; rv:102.0) '
    'Gecko/20100101 Firefox/102.0" '
    "--no-robots --filter-urls --reject-regex=/w/|\\.js$ "
    "--http-proxy=127.0.0.1:9050 --https-proxy=127.0.0.1:9050 "
    "--no-check-hostname --no-check-certificate --no-hpkp --no-hsts "
    "{url}"
)

WGET2_ENV = {
    "LANG": "en_US.UTF-8",
    "LC_ALL": "en_US.UTF-8",
    "LANGUAGE": "en_US.UTF-8",
}


def build_monitor_processes(pages, num_visits, visit_interval,
                            tor_start_time, first_fetch_time, wget2_path):
    """
    Build process list for a monitor node.

    Pages are fetched ONE AT A TIME in a round-robin pattern:
      fetch page_0, NEWNYM, fetch page_1, NEWNYM, ..., fetch page_N, NEWNYM,
      fetch page_0 (visit 2), NEWNYM, ...

    Each fetch gets a `visit_interval`-second window.
    """
    procs = []

    # Tor
    procs.append({
        "path": "~/.local/bin/tor",
        "args": "--defaults-torrc torrc-defaults -f torrc",
        "environment": {"OPENBLAS_NUM_THREADS": "1"},
        "start_time": tor_start_time,
        "expected_final_state": "running",
    })

    # Oniontrace
    procs.append({
        "path": "~/.local/bin/oniontrace",
        "args": "Mode=log TorControlPort=9051 LogLevel=info Events=BW,CIRC",
        "start_time": tor_start_time + 1,
        "expected_final_state": "running",
    })

    # Build the sequential fetch schedule
    # We interleave pages across visits so that the same page isn't always
    # fetched at the same relative time in the simulation.
    schedule = []
    for visit in range(num_visits):
        for page in pages:
            schedule.append(page)

    for idx, page in enumerate(schedule):
        t_fetch = first_fetch_time + (idx * visit_interval)
        t_newnym = t_fetch + visit_interval - 1

        # wget2 fetch
        procs.append({
            "path": wget2_path,
            "args": WGET2_ARGS_TEMPLATE.format(url=page["url"]),
            "environment": WGET2_ENV,
            "start_time": t_fetch,
        })

        # NEWNYM (circuit isolation). newnym.py uses only stdlib, so system
        # python is fine here.
        procs.append({
            "path": "/usr/bin/python3",
            "args": "/home/projectadmin/newnym.py",
            "start_time": t_newnym,
        })

    return procs, schedule


def build_zimserver_processes(pages, zimroot):
    """One zimsrv.py process per port on the zimserver.

    zimsrv.py is our own tiny HTTP server wrapping libzim. We can't use
    kiwix-serve because its prebuilt binary is statically linked and Shadow
    rejects static ELFs (it needs to LD_PRELOAD its shim). We can't use the
    `zimply` library either because it only supports the old ZIM namespace
    format ("A/ArticleName"), which modern Kiwix ZIMs (v6+) dropped.
    libzim handles the current format natively.

    Each process serves the whole ZIM on one port; since we run one per
    page/port, the URL path (http://ip:PORT/<article>) still identifies the
    specific page the client is fetching.
    """
    procs = []
    for page in pages:
        procs.append({
            "path": "/home/projectadmin/toolsenv/bin/python3",
            "args": "/home/projectadmin/zimsrv.py",
            "environment": {
                "ZIMROOT": zimroot,
                "ZIMIP":   page["ip"],
                "ZIMPORT": str(page["port"]),
                "LANG":    "en_US.UTF-8",
                "LC_ALL":  "en_US.UTF-8",
            },
            "start_time": "3s",
            # Servers run until Shadow kills them at stop_time. Without this,
            # Shadow reports "unexpected final state" for every server process.
            "expected_final_state": "running",
        })
    return procs


def main():
    parser = argparse.ArgumentParser(description="Add WF nodes to a Shadow config")
    parser.add_argument("--base-config", required=True, help="Existing shadow.config.yaml")
    parser.add_argument("--urls", required=True, help="urls.txt (port-to-URL mapping)")
    parser.add_argument("--output", required=True, help="Output shadow.config.yaml")
    parser.add_argument("--num-monitors", type=int, default=5,
                        help="Number of monitor nodes (default: 5)")
    parser.add_argument("--num-pages", type=int, default=None,
                        help="Number of pages to use (default: all)")
    parser.add_argument("--visits-per-page", type=int, default=50,
                        help="Visits per page per monitor (default: 50)")
    parser.add_argument("--visit-interval", type=int, default=30,
                        help="Seconds per visit window (default: 30)")
    parser.add_argument("--zimroot", default="/home/projectadmin/wikidata",
                        help="ZIM data path on server")
    parser.add_argument("--wget2-path", default="/home/projectadmin/wget2_noinstall",
                        help="wget2 binary path on server")
    parser.add_argument("--tor-start-time", type=int, default=240,
                        help="Tor start time in sim seconds (default: 240)")
    parser.add_argument("--first-fetch-time", type=int, default=1200,
                        help="First wget2 fetch time (default: 1200, ~20min bootstrap)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)

    # Load base config
    with open(args.base_config) as f:
        config = yaml.safe_load(f)

    # Read URLs and optionally limit
    all_pages = read_urls(args.urls)
    if args.num_pages:
        all_pages = all_pages[:args.num_pages]

    existing_ids = get_existing_node_ids(config)
    print(f"Base config has {len(existing_ids)} hosts with valid node IDs "
          f"(will sample from these)", file=sys.stderr)

    # Distribute pages across monitors (round-robin)
    monitor_pages = [[] for _ in range(args.num_monitors)]
    for i, page in enumerate(all_pages):
        monitor_pages[i % args.num_monitors].append(page)

    # Track all schedules for the pcap converter
    all_schedules = {}

    for i in range(args.num_monitors):
        name = f"monitor{i}"
        pages = monitor_pages[i]
        node_id = pick_node_id(existing_ids, rng)

        procs, schedule = build_monitor_processes(
            pages, args.visits_per_page, args.visit_interval,
            args.tor_start_time, args.first_fetch_time, args.wget2_path,
        )

        config["hosts"][name] = {
            "network_node_id": node_id,
            "bandwidth_down": "100 megabit",
            "bandwidth_up": "100 megabit",
            # pcap_enabled lives under host_options in current Shadow releases
            "host_options": {
                "pcap_enabled": True,
                "pcap_capture_size": "65535 B",
            },
            "processes": procs,
        }

        # Save schedule for pcap_to_npz.py
        all_schedules[name] = [
            {"start_time": args.first_fetch_time + (idx * args.visit_interval),
             "port": page["port"],
             "url": page["url"]}
            for idx, page in enumerate(schedule)
        ]

        n_fetches = len(pages) * args.visits_per_page
        last_fetch = args.first_fetch_time + (n_fetches * args.visit_interval)
        print(f"  {name}: {len(pages)} pages, {n_fetches} fetches, "
              f"last fetch at t={last_fetch}s", file=sys.stderr)

    # Add zimserver
    pages_by_ip = {}
    for page in all_pages:
        pages_by_ip.setdefault(page["ip"], []).append(page)

    for ip_idx, (ip, pages) in enumerate(pages_by_ip.items()):
        name = f"zimserver{ip_idx}"
        node_id = pick_node_id(existing_ids, rng)
        config["hosts"][name] = {
            "network_node_id": node_id,
            "bandwidth_down": "200 megabit",
            "bandwidth_up": "200 megabit",
            "ip_addr": ip,
            "processes": build_zimserver_processes(pages, args.zimroot),
        }
        print(f"  {name}: {len(pages)} ports on {ip}", file=sys.stderr)

    # Adjust stop_time
    max_fetches = max(len(mp) * args.visits_per_page for mp in monitor_pages)
    required_time = args.first_fetch_time + (max_fetches * args.visit_interval) + 120
    if required_time > config["general"].get("stop_time", 0):
        config["general"]["stop_time"] = required_time
        print(f"  stop_time adjusted to {required_time}s "
              f"({required_time/3600:.1f}h)", file=sys.stderr)

    # Write shadow config
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, width=200)

    # Write schedule JSON (used by pcap_to_npz.py for segmentation)
    schedule_path = Path(args.output).with_suffix(".schedule.json")
    meta = {
        "visit_interval": args.visit_interval,
        "first_fetch_time": args.first_fetch_time,
        "num_pages": len(all_pages),
        "visits_per_page": args.visits_per_page,
        "monitors": all_schedules,
    }
    with open(schedule_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\nWrote {args.output}", file=sys.stderr)
    print(f"Wrote {schedule_path} (for pcap_to_npz.py)", file=sys.stderr)
    print(f"Total hosts: {len(config['hosts'])}", file=sys.stderr)
    print(f"Pages: {len(all_pages)}, Monitors: {args.num_monitors}, "
          f"Visits/page: {args.visits_per_page}", file=sys.stderr)


if __name__ == "__main__":
    main()
