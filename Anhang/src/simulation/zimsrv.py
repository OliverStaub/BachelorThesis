#!/usr/bin/env python3
"""
zimsrv.py — Minimal HTTP server that serves one Wikipedia ZIM file.

Uses `libzim` directly (which handles modern v6+ ZIM files with their flat,
namespace-free path layout). Runs under the toolsenv Python, which is a
dynamically linked executable (required by Shadow's LD_PRELOAD shim — prebuilt
`kiwix-serve` binaries are statically linked and Shadow rejects them).

Configuration via environment variables:
    ZIMROOT  directory containing wikipedia_en_all_maxi.zim
    ZIMIP    IP address to bind to
    ZIMPORT  TCP port to listen on

URL routing:
    /                    — returns 200 with a minimal index listing
    /<ArticlePath>       — looks the path up in the ZIM, returns its content
    /<ArticlePath>.html  — same, extension stripped (some clients add it)
"""

import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

from libzim.reader import Archive
from libzim.suggestion import SuggestionSearcher  # noqa: F401 (keeps libzim loaded)


ZIM_ROOT = os.environ["ZIMROOT"]
ZIM_IP   = os.environ["ZIMIP"]
ZIM_PORT = int(os.environ["ZIMPORT"])
ZIM_FILE = f"{ZIM_ROOT}/wikipedia_en_all_maxi.zim"

print(f"[zimsrv] Opening {ZIM_FILE}", flush=True)
ARCHIVE = Archive(ZIM_FILE)
print(f"[zimsrv] {ARCHIVE.entry_count} entries in archive", flush=True)


def lookup(path):
    """Return (mimetype, content_bytes) for a path, or None if not found."""
    path = unquote(path.lstrip("/"))

    # Accept "Article.html" by trying both forms.
    candidates = [path]
    if path.endswith(".html"):
        candidates.append(path[: -len(".html")])
    # Also try stripping an "A/" legacy-namespace prefix, just in case.
    if path.startswith("A/"):
        candidates.append(path[2:])

    for candidate in candidates:
        if not candidate:
            continue
        try:
            entry = ARCHIVE.get_entry_by_path(candidate)
        except KeyError:
            continue
        except Exception:
            continue

        # Follow redirects.
        while entry.is_redirect:
            entry = entry.get_redirect_entry()

        item = entry.get_item()
        return item.mimetype, bytes(item.content)

    return None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Split off any query string
            path = self.path.split("?", 1)[0]

            if path in ("/", "/index.html", "/main.html"):
                try:
                    main = ARCHIVE.main_entry
                    while main.is_redirect:
                        main = main.get_redirect_entry()
                    item = main.get_item()
                    self._send(200, item.mimetype, bytes(item.content))
                    return
                except Exception:
                    self._send(200, "text/html",
                               f"<h1>{ARCHIVE.entry_count} entries</h1>".encode())
                    return

            result = lookup(path)
            if result is None:
                self._send(404, "text/plain", b"404 Not Found\n")
                return

            mimetype, content = result
            self._send(200, mimetype, content)

        except Exception:
            traceback.print_exc(file=sys.stderr)
            self._send(500, "text/plain", b"500 Internal Server Error\n")

    def _send(self, status, mimetype, body):
        self.send_response(status)
        self.send_header("Content-Type", mimetype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # Silence the default access log; Shadow captures it anyway via stdout.
    def log_message(self, format, *args):
        sys.stderr.write("[%s] %s - %s\n" % (self.log_date_time_string(),
                                              self.address_string(),
                                              format % args))


def main():
    print(f"[zimsrv] Listening on {ZIM_IP}:{ZIM_PORT}", flush=True)
    server = ThreadingHTTPServer((ZIM_IP, ZIM_PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
