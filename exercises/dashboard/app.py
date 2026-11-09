"""A loopback-only mock service health dashboard web app.

Serves:
  - GET /          the mobile-first dashboard page
  - GET /api/health  the current health snapshot as JSON

The health snapshot is deterministic per minute and per seed, so the page
updates as the clock advances but any single fetch is reproducible.

Run:  python3 -m exercises.dashboard.app   (binds 127.0.0.1 only)
Then open http://127.0.0.1:8000/ in a browser (or narrow the window to
phone width) and watch stations flip between healthy/degraded/down.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from exercises.dashboard.service import service_health
from exercises.dashboard.ui import PAGE

HOST = "127.0.0.1"
PORT = 8000


class DashboardHandler(BaseHTTPRequestHandler):
    seed = "demo"

    def do_GET(self):
        if self.path.startswith("/api/health"):
            self._json(service_health(self.seed))
        elif self.path in ("/", "/index.html"):
            self._html(PAGE)
        else:
            self._json({"error": "not found"}, status=404)

    def _json(self, payload, status=200):
        body = json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, body, status=200):
        body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}")


def serve(host=HOST, port=PORT, seed="demo"):
    """Start the dashboard; returns the started server."""
    DashboardHandler.seed = seed
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"dashboard on http://{host}:{port}/  (Ctrl-C to stop)")
    server.serve_forever()
    return server


def main():
    try:
        serve()
    except KeyboardInterrupt:
        print("\\ndashboard stopped")


if __name__ == "__main__":
    main()
