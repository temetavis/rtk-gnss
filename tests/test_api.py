import json
import threading

import pytest

from exercises.api.service import Api, ApiError, HOST
from exercises.db.engine import MemoryStore


@pytest.fixture
def api():
    store = MemoryStore()
    store.add_station("HEL1", "Helsinki 1", 60.17, 24.94)
    store.add_station("TKU1", "Turku 1", 60.45, 22.27)
    return Api(store=store, tokens={})


def auth_headers(api, token="tok_abc"):
    api.tokens[token] = "alice"
    return {"Authorization": f"Bearer {token}"}


def test_health_needs_no_token(api):
    status, body = api.handle("GET", "/api/v1/health", {}, {})
    assert status == 200
    assert body["ok"] is True


def test_stations_require_auth(api):
    with pytest.raises(ApiError) as err:
        api.handle("GET", "/api/v1/stations", {}, {})
    assert err.value.status == 401


def test_stations_with_valid_token(api):
    status, body = api.handle("GET", "/api/v1/stations", {},
                              auth_headers(api))
    assert status == 200
    assert {row["code"] for row in body} == {"HEL1", "TKU1"}


def test_invalid_token_rejected(api):
    with pytest.raises(ApiError) as err:
        api.handle("GET", "/api/v1/stations", {},
                  {"Authorization": "Bearer nope"})
    assert err.value.status == 401


def test_station_detail_and_404(api):
    headers = auth_headers(api)
    status, body = api.handle("GET", "/api/v1/stations/1", {}, headers)
    assert status == 200
    assert body["code"] == "HEL1"
    with pytest.raises(ApiError) as err:
        api.handle("GET", "/api/v1/stations/999", {}, headers)
    assert err.value.status == 404


def test_station_health_endpoint(api):
    headers = auth_headers(api)
    status, body = api.handle("GET", "/api/v1/stations/1/health", {}, headers)
    assert status == 200
    assert body["metrics"] is None  # no metrics recorded yet
    api.store.add_metric(1, stream_age_s=2.0, sats_tracked=12,
                         cycle_slips=1, phase_noise_mm=1.0)
    status, body = api.handle("GET", "/api/v1/stations/1/health", {}, headers)
    assert body["metrics"]["sats_tracked"] == 12


def test_unknown_route_404(api):
    with pytest.raises(ApiError) as err:
        api.handle("GET", "/api/v1/nonsense", {}, auth_headers(api))
    assert err.value.status == 404


def test_create_account_validation(api):
    cases = [
        ({"username": "x", "password": "longenough1"}, 422),      # bad username
        ({"username": "validuser", "password": "short"}, 422),   # bad password
        ({"username": "validuser", "password": "longenough1",
          "subscription": "gold"}, 422),                          # bad tier
        ("not a dict", 400),
    ]
    for payload, expected in cases:
        with pytest.raises(ApiError) as err:
            api.handle("POST", "/api/v1/accounts", {}, {}, payload)
        assert err.value.status == expected


def test_create_account_success_and_conflict(api):
    payload = {"username": "newuser", "password": "longenough1"}
    status, body = api.handle("POST", "/api/v1/accounts", {}, {}, payload)
    assert status == 201
    assert body["api_token"].startswith("rtk_")
    # token works immediately
    status, _ = api.handle("GET", "/api/v1/stations", {},
                          {"Authorization": f"Bearer {body['api_token']}"})
    assert status == 200
    # duplicate username -> 409
    with pytest.raises(ApiError) as err:
        api.handle("POST", "/api/v1/accounts", {}, {}, payload)
    assert err.value.status == 409


def test_post_not_allowed_on_stations(api):
    with pytest.raises(ApiError) as err:
        api.handle("POST", "/api/v1/stations", {}, auth_headers(api), {})
    assert err.value.status == 405


def test_http_end_to_end(api):
    """The route table works through a real loopback HTTP server too."""
    from http.server import ThreadingHTTPServer
    from exercises.api.service import make_handler

    server = ThreadingHTTPServer((HOST, 0), make_handler(api))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request
        import urllib.error
        port = server.server_address[1]

        req = urllib.request.Request(
            f"http://{HOST}:{port}/api/v1/stations",
            headers=auth_headers(api))
        with urllib.request.urlopen(req, timeout=3) as resp:
            assert resp.status == 200
            data = json.loads(resp.read())
            assert {row["code"] for row in data} == {"HEL1", "TKU1"}

        req = urllib.request.Request(f"http://{HOST}:{port}/api/v1/stations")
        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(req, timeout=3)
        assert err.value.code == 401
    finally:
        server.shutdown()
        server.server_close()
