import pytest

from exercises.db.engine import MemoryStore
from exercises.monitoring.alerts import AlertSink
from exercises.monitoring.checks import Check, CheckEngine, default_checks
from exercises.monitoring.poller import Poller, SimulatedStation


@pytest.fixture
def network():
    store = MemoryStore()
    hel = store.add_station("HEL1", "Helsinki 1", 60.17, 24.94)
    tku = store.add_station("TKU1", "Turku 1", 60.45, 22.27)
    return store, hel, tku


def test_healthy_network_no_alerts(network):
    store, hel, tku = network
    stations = [SimulatedStation(hel["id"]), SimulatedStation(tku["id"])]
    poller = Poller(store, stations)
    engine = CheckEngine(store, AlertSink(), default_checks())

    for _ in range(10):
        poller.poll_all()
        assert engine.run_once() == 0


def test_stale_stream_fires_after_consecutive_bad_checks(network):
    store, hel, tku = network
    sink = AlertSink()
    tku_station = SimulatedStation(tku["id"])
    poller = Poller(store, [SimulatedStation(hel["id"]), tku_station])
    engine = CheckEngine(store, sink, default_checks())

    tku_station.set_state(stream_age=40.0)
    for _ in range(5):
        poller.poll_all()
        engine.run_once()

    kinds = [(a.station_id, a.kind) for a in sink.firing()]
    assert (tku["id"], "stale_stream") in kinds
    assert all(a.station_id != hel["id"] for a in sink.firing())
    # one alert per incident, not per poll
    stale_alerts = [a for a in sink.firing() if a.kind == "stale_stream"]
    assert len(stale_alerts) == 1
    assert stale_alerts[0].severity == "critical"


def test_alert_resolves_after_recovery(network):
    store, hel, tku = network
    sink = AlertSink()
    tku_station = SimulatedStation(tku["id"])
    poller = Poller(store, [tku_station])
    engine = CheckEngine(store, sink, default_checks())

    tku_station.set_state(stream_age=40.0)
    for _ in range(3):
        poller.poll_all()
        engine.run_once()
    assert any(a.kind == "stale_stream" for a in sink.firing())

    tku_station.set_state(stream_age=1.0)
    for _ in range(3):
        poller.poll_all()
        engine.run_once()
    assert not any(a.kind == "stale_stream" for a in sink.firing())


def test_flap_suppression_does_not_fire(network):
    store, hel, tku = network
    sink = AlertSink()
    tku_station = SimulatedStation(tku["id"])
    poller = Poller(store, [tku_station])
    engine = CheckEngine(store, sink, default_checks())

    # alternate bad/good: streak never reaches fire threshold
    for i in range(10):
        tku_station.set_state(stream_age=40.0 if i % 2 == 0 else 1.0)
        poller.poll_all()
        engine.run_once()
    assert not any(a.kind == "stale_stream" for a in sink.firing())


def test_multiple_check_kinds(network):
    store, hel, tku = network
    sink = AlertSink()
    tku_station = SimulatedStation(tku["id"])
    poller = Poller(store, [tku_station])
    engine = CheckEngine(store, sink, default_checks())

    tku_station.set_state(stream_age=40.0, sats=2, slips=30, noise=5.0)
    for _ in range(4):
        poller.poll_all()
        engine.run_once()

    kinds = {a.kind for a in sink.firing()}
    assert kinds == {"stale_stream", "few_satellites", "cycle_slips",
                      "phase_noise"}


def test_maintenance_station_ignored(network):
    store, hel, tku = network
    store.update("reference_stations", tku["id"], status="maintenance")
    sink = AlertSink()
    tku_station = SimulatedStation(tku["id"], stream_age=40.0)
    poller = Poller(store, [tku_station])
    engine = CheckEngine(store, sink, default_checks())

    for _ in range(4):
        poller.poll_all()
        engine.run_once()
    assert not any(a.station_id == tku["id"] for a in sink.firing())
