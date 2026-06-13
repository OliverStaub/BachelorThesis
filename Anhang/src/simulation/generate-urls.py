#!/usr/bin/env python3
"""
generate-urls.py — Sample random Wikipedia articles from a ZIM file and write
a urls.txt compatible with generate-wf-config.py.

Runs on the server (where the ZIM file is). Uses libzim to enumerate articles.

Output format (same as explainwf-popets2023/data/urls.txt):
    <IP> <PORT> http://<IP>:<PORT>/<ArticleTitle>

Example:
    129.114.108.192 8000 http://129.114.108.192:8000/Football
    129.114.108.192 8001 http://129.114.108.192:8001/Paris
    ...

Usage on the server:
    # Install libzim if not already
    pip install libzim

    # Generate 20 random URLs starting at port 8000
    python3 generate-urls.py \\
        --zim /home/projectadmin/wikidata/wikipedia_en_all_maxi.zim \\
        --num-pages 20 \\
        --output /home/projectadmin/urls.txt
"""

import argparse
import random
import re
import sys
from pathlib import Path


def sample_articles(zim_path, n, seed=42):
    """
    Sample `n` distinct article titles from a ZIM file.

    Filters: only entries in the article namespace (typical real articles),
    skipping redirects and non-article content.
    """
    try:
        from libzim.reader import Archive
    except ImportError:
        print("ERROR: libzim not installed. Run: pip install libzim", file=sys.stderr)
        sys.exit(1)

    archive = Archive(zim_path)
    total = archive.entry_count
    print(f"ZIM file: {zim_path}", file=sys.stderr)
    print(f"Total entries: {total}", file=sys.stderr)

    rng = random.Random(seed)
    seen_titles = set()
    selected = []

    # Sample with over-fetching to account for skipped entries (redirects,
    # non-articles). Cap the number of attempts to avoid infinite loops on
    # small ZIMs.
    max_attempts = n * 20
    attempts = 0

    while len(selected) < n and attempts < max_attempts:
        attempts += 1
        idx = rng.randint(0, total - 1)

        try:
            entry = archive._get_entry_by_id(idx)
        except Exception:
            continue

        # Skip redirects
        if entry.is_redirect:
            continue

        title = entry.title
        path = entry.path

        # Filter: title should be non-empty and look like a Wikipedia article.
        # Skip things like MediaWiki namespace pages, images, CSS, etc.
        if not title or not title.strip():
            continue
        if title in seen_titles:
            continue

        # Skip common non-article paths (depends on ZIM structure)
        if path.startswith(("-/", "I/", "M/", "X/")):
            continue
        # Further filter: mimetype should be html
        try:
            if entry.get_item().mimetype != "text/html":
                continue
        except Exception:
            continue

        # Replace spaces with underscores for URL use
        safe_title = title.replace(" ", "_")

        # WHITELIST approach: only allow characters that are safe in
        # Shadow's YAML argument parser, HTTP URLs, and shell expansion.
        # Letters, digits, underscores, hyphens, and periods only.
        if not re.match(r'^[A-Za-z0-9_\-\.]+$', safe_title):
            continue

        # Must be at least 3 chars (skip stub-like entries)
        if len(safe_title) < 3:
            continue

        seen_titles.add(title)
        selected.append(safe_title)

    if len(selected) < n:
        print(f"WARNING: only found {len(selected)} articles (wanted {n}) "
              f"after {attempts} attempts", file=sys.stderr)

    return selected


def main():
    parser = argparse.ArgumentParser(
        description="Sample random Wikipedia articles from a ZIM file → urls.txt"
    )
    parser.add_argument("--zim", required=True,
                        help="Path to ZIM file (e.g. wikipedia_en_all_maxi.zim)")
    parser.add_argument("--num-pages", type=int, default=100,
                        help="Number of articles to sample (default: 100)")
    parser.add_argument("--output", required=True,
                        help="Output path for urls.txt")
    parser.add_argument("--ip", default="129.114.108.192",
                        help="IP address for the URLs (default: 129.114.108.192)")
    parser.add_argument("--start-port", type=int, default=8000,
                        help="First port (default: 8000, will use start..start+N-1)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42)")
    args = parser.parse_args()

    titles = sample_articles(args.zim, args.num_pages, args.seed)

    if not titles:
        print("ERROR: no articles extracted", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w") as f:
        for i, title in enumerate(titles):
            port = args.start_port + i
            f.write(f"{args.ip} {port} http://{args.ip}:{port}/{title}\n")

    print(f"\nWrote {len(titles)} URLs to {out_path}", file=sys.stderr)
    print(f"Port range: {args.start_port}..{args.start_port + len(titles) - 1}", file=sys.stderr)
    print(f"First 3 articles: {titles[:3]}", file=sys.stderr)


if __name__ == "__main__":
    main()
