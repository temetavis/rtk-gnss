import json
import threading
import time
import urllib.request

import pytest

from exercises.dashboard.app import DashboardHandler, HOST
from exercises.dashboard.service import (
    STATIONS, classify, service_health, simulate_station_health,
)
from exercises.dashboard.ui import PAGE
from http.server import ThreadingHTTPServer


# --- health model ----------------------------------------------------------

def test_classify_thresholds():
    assert classify(0.5, 1.0, False) == "healthy"
    assert classify(3.0, 1.0, False) == "degraded"
    assert classify(6.0, 1.0, False) == "degraded"
    assert classify(0.5, 1.0, True) == "degraded"
    assert classify(0.5, 120.0, False) == "down"


def test_snapshot_shape_and_consistency():
    snap = service_health(seed="demo", now=1_700_000_000.0)
    assert snap["stations_total"] == len(STATIONS)
    assert (snap["stations_healthy"] + snap["stations_degraded"]
            + snap["stations_down"]) == snap["stations_total"]
    assert snap["overall_status"] in ("healthy", "degraded", "down")
    statuses = {s["status"] for s in snap["stations"]}
    assert statuses <= {"healthy", "degraded", "down"}
    assert snap["rover_sessions"] == sum(
        s["rover_sessions"] for s in snap["stations"])
    if snap["stations_down"]:
        assert snap["overall_status"] in ("degraded", "down")


def test_snapshot_is_deterministic_per_minute():
    t = 1_700_000_000.0
    a = service_health(seed="demo", now=t)
    b = service_health(seed="demo", now=t + 30.0)
    assert a["stations"] == b["stations"]


def test_outage_seed_forces_a_down_station():
    snap = service_health(seed="demo-outage", now=1_700_000_000.0)
    assert snap["stations_down"] >= 1
    assert snap["overall_status"] in ("degraded", "down")
    tur = next(s for s in snap["stations"] if s["name"] == "TURSW")
    assert tur["status"] == "down"
    assert tur["latency_s"] is None


def test_station_record_fields():
    rec = simulate_station_health("x", STATIONS[0], 1_700_000_000.0)
    assert rec["name"] == "HELSON"
    assert 0.0 <= rec["uptime_24h"] <= 1.0
    assert rec["status"] in ("healthy", "degraded", "down")


# --- web app ----------------------------------------------------------------

@pytest.fixture
def server():
    srv = ThreadingHTTPServer((HOST, 0), DashboardHandler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def _get(port, path):
    with urllib.request.urlopen(
            f"http://{HOST}:{port}{path}", timeout=3) as resp:
        return resp.status, resp.headers["Content-Type"], resp.read()


def test_serves_html_page(server):
    status, ctype, body = _get(server.server_address[1], "/")
    assert status == 200
    assert ctype.startswith("text/html")
    assert b"MockNet RTK service" in body
    assert b"/api/health" in body


def test_serves_health_json(server):
    status, ctype, body = _get(server.server_address[1], "/api/health")
    assert status == 200
    assert ctype == "application/json"
    snap = json.loads(body)
    assert snap["stations_total"] == len(STATIONS)
    assert "stations" in snap and "overall_status" in snap


def test_unknown_path_is_404(server):
    with pytest.raises(urllib.error.HTTPError) as exc:
        _get(server.server_address[1], "/nope")
    assert exc.value.code == 404


def test_page_contains_mobile_viewport_meta():
    assert 'name="viewport"' in PAGE
