"""Loopback-only REST API over the station database.

Demonstrates the API layer of a positioning service: resource-oriented
routing, token authentication, JSON validation, and correct status codes.
No frameworks — the standard library is enough to learn the concepts.

Run: python3 -m exercises.api.service   (binds 127.0.0.1 only)
"""

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from ..db import queries
from ..db.engine import connect
from ..ops import security

HOST = "127.0.0.1"
PORT = 8080

VALID_SUBSCRIPTIONS = ("trial", "standard", "pro")


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def validate_account_payload(payload):
    if not isinstance(payload, dict):
        raise ApiError(400, "body must be a JSON object")
    username = payload.get("username")
    password = payload.get("password")
    if not isinstance(username, str) or not re.fullmatch(r"[a-z0-9_.-]{3,32}",
                                                        username):
        raise ApiError(422, "username must be 3-32 chars [a-z0-9_.-]")
    if not isinstance(password, str) or len(password) < 8:
        raise ApiError(422, "password must be at least 8 characters")
    subscription = payload.get("subscription", "standard")
    if subscription not in VALID_SUBSCRIPTIONS:
        raise ApiError(422, f"subscription must be one of {VALID_SUBSCRIPTIONS}")
    return username, password, subscription


class Api:
    """Route table + handlers, testable without a socket."""

    def __init__(self, store=None, tokens=None):
        self.store = store or connect()
        # tokens maps api_token -> username; in production only the hash is kept
        self.tokens = tokens or {}

    # -- auth ------------------------------------------------------------
    def authenticate(self, headers):
        headers = {k.lower(): v for k, v in headers.items()}
        auth = headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            raise ApiError(401, "missing bearer token")
        token = auth[len("Bearer "):]
        username = self.tokens.get(token)
        if username is None:
            raise ApiError(401, "invalid token")
        return username

    # -- endpoints ---------------------------------------------------------
    def handle(self, method, path, query, headers, body=None):
        """Returns (status, json_body)."""
        if path.startswith("/api/v1/accounts") and method == "POST":
            return self.create_account(body)
        try:
            self.authenticate(headers)
        except ApiError:
            if path != "/api/v1/health":
                raise
        if method != "GET":
            raise ApiError(405, "method not allowed")

        if path == "/api/v1/health":
            return 200, {"ok": True}
        if path == "/api/v1/stations":
            return 200, queries.stations_summary(self.store)
        if path == "/api/v1/alerts":
            return 200, queries.firing_alerts(self.store)
        if path == "/api/v1/usage":
            return 200, queries.mountpoint_usage_last_day(self.store)
        m = re.fullmatch(r"/api/v1/stations/(\d+)", path)
        if m:
            return self.station_detail(int(m.group(1)))
        m = re.fullmatch(r"/api/v1/stations/(\d+)/health", path)
        if m:
            return self.station_health(int(m.group(1)))
        raise ApiError(404, "not found")

    def station_detail(self, station_id):
        st = self.store.get("reference_stations", station_id)
        if st is None:
            raise ApiError(404, "unknown station")
        return 200, {"id": st["id"], "code": st["code"], "name": st["name"],
                     "lat": st["lat"], "lon": st["lon"],
                     "status": st["status"]}

    def station_health(self, station_id):
        st = self.store.get("reference_stations", station_id)
        if st is None:
            raise ApiError(404, "unknown station")
        latest = self.store.latest_metric(station_id)
        if latest is None:
            return 200, {"station": st["code"], "metrics": None}
        return 200, {
            "station": st["code"],
            "metrics": {
                "stream_age_s": latest["stream_age_s"],
                "sats_tracked": latest["sats_tracked"],
                "cycle_slips": latest["cycle_slips"],
                "phase_noise_mm": latest["phase_noise_mm"],
                "recorded_at": latest["recorded_at"].isoformat(),
            },
        }

    def create_account(self, payload):
        username, password, subscription = validate_account_payload(payload)
        if self.store.find_account(username) is not None:
            raise ApiError(409, "username already exists")
        token = security.generate_api_token()
        account = self.store.add_account(
            username, security.hash_password(password), subscription,
            api_token_hash=security.token_fingerprint(token))
        self.tokens[token] = username
        return 201, {"id": account["id"], "username": username,
                     "subscription": subscription, "api_token": token}


def make_handler(api):
    class Handler(BaseHTTPRequestHandler):
        def _respond(self, status, payload):
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _dispatch(self, method):
            parsed = urlparse(self.path)
            query = {k: v[0] for k, v in
                     parse_qs(parsed.query).items()}
            length = int(self.headers.get("Content-Length") or 0)
            body = None
            if length:
                body = json.loads(self.rfile.read(length) or b"null")
            try:
                status, payload = api.handle(method, parsed.path, query,
                                             self.headers, body)
                self._respond(status, payload)
            except ApiError as err:
                self._respond(err.status, {"error": err.message})
            except json.JSONDecodeError:
                self._respond(400, {"error": "invalid JSON body"})

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        def log_message(self, *args):
            pass

    return Handler


def serve(api=None, host=HOST, port=PORT):
    api = api or Api()
    server = ThreadingHTTPServer((host, port), make_handler(api))
    print(f"station API on http://{host}:{port}/api/v1/ "
          f"(bearer token required for most endpoints)")
    server.serve_forever()


if __name__ == "__main__":
    serve()
