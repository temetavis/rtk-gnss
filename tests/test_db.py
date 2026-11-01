import os

import pytest

from exercises.db.engine import MemoryStore, connect, utcnow
from exercises.db import queries
from exercises.integrations.feed_sync import FeedSync


@pytest.fixture
def store():
    s = MemoryStore()
    s.add_station("HEL1", "Helsinki 1", 60.17, 24.94, owner="partner-a")
    s.add_station("TKU1", "Turku 1", 60.45, 22.27, owner="partner-b")
    s.add_station("ROV1", "Rovaniemi 1", 66.50, 25.73, owner="partner-a",
                  status="maintenance")
    return s


def test_add_and_get_station(store):
    st = store.find_by_code("HEL1") if hasattr(store, "find_by_code") else None
    rows = store.select("reference_stations", where={"code": "HEL1"})
    assert len(rows) == 1
    assert rows[0]["name"] == "Helsinki 1"
    assert rows[0]["status"] == "online"


def test_latest_metric(store):
    sid = store.select("reference_stations", where={"code": "HEL1"})[0]["id"]
    store.add_metric(sid, stream_age_s=2.0, sats_tracked=12,
                     cycle_slips=1, phase_noise_mm=1.0)
    store.add_metric(sid, stream_age_s=3.0, sats_tracked=11,
                     cycle_slips=2, phase_noise_mm=1.1)
    latest = store.latest_metric(sid)
    assert latest["stream_age_s"] == 3.0


def test_stale_station_detection(store):
    sid = store.select("reference_stations", where={"code": "TKU1"})[0]["id"]
    # HEL1 has a fresh metric; TKU1 has none; ROV1 is maintenance (ignored)
    fresh_id = store.select("reference_stations",
                            where={"code": "HEL1"})[0]["id"]
    store.add_metric(fresh_id, stream_age_s=1.0, sats_tracked=12,
                     cycle_slips=1, phase_noise_mm=1.0)
    stale = store.stale_stations(max_age_s=15.0)
    codes = {s["code"] for s in stale}
    assert "TKU1" in codes
    assert "HEL1" not in codes
    assert "ROV1" not in codes


def test_alert_lifecycle(store):
    sid = store.select("reference_stations", where={"code": "HEL1"})[0]["id"]
    alert = store.add_alert(sid, "stale_stream", "critical",
                            {"stream_age_s": 40.0})
    assert store.firing_alert(sid, "stale_stream")["id"] == alert["id"]
    store.resolve_alert(alert["id"])
    assert store.firing_alert(sid, "stale_stream") is None
    resolved = store.get("alerts", alert["id"])
    assert resolved["state"] == "resolved"


def test_queries_summary(store):
    sid = store.select("reference_stations", where={"code": "HEL1"})[0]["id"]
    store.add_metric(sid, stream_age_s=1.0, sats_tracked=12,
                     cycle_slips=1, phase_noise_mm=1.0)
    summary = queries.stations_summary(store)
    by_code = {row["code"]: row for row in summary}
    assert by_code["HEL1"]["latest_stream_age_s"] == 1.0
    assert by_code["TKU1"]["latest_stream_age_s"] is None


def test_queries_firing_alerts(store):
    sid = store.select("reference_stations", where={"code": "TKU1"})[0]["id"]
    store.add_alert(sid, "stale_stream", "critical")
    rows = queries.firing_alerts(store)
    assert len(rows) == 1
    assert rows[0]["station"] == "TKU1"
    assert rows[0]["severity"] == "critical"


def test_queries_usage(store):
    sid = store.select("reference_stations", where={"code": "HEL1"})[0]["id"]
    store.add_session(1, "HELSON", bytes_sent=1000)
    store.add_session(1, "HELSON", bytes_sent=2000)
    store.add_session(2, "TMPNOR", bytes_sent=500)
    usage = queries.mountpoint_usage_last_day(store)
    assert usage["HELSON"]["sessions"] == 2
    assert usage["HELSON"]["bytes"] == 3000
    assert usage["TMPNOR"]["bytes"] == 500


def test_schema_sql_files_exist():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schema = os.path.join(root, "exercises", "db", "schema.sql")
    migrations = os.path.join(root, "exercises", "db", "migrations",
                              "001_add_health_flag.sql")
    with open(schema) as f:
        assert "CREATE TABLE IF NOT EXISTS reference_stations" in f.read()
    with open(migrations) as f:
        assert "station_health_trigger" in f.read()


def test_connect_returns_shared_store():
    assert connect() is connect()
