import base64
import threading
import time

import pytest

from exercises.ntrip.caster import (
    NtripCaster, NtripCasterHandler, PORT, HOST,
    parse_gga, parse_request, sourcetable_text,
)


@pytest.fixture
def caster():
    NtripCasterHandler.gga_seen = []
    server = NtripCaster((HOST, 0), NtripCasterHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


def _recv_until(sock, marker, timeout=3.0):
    sock.settimeout(timeout)
    buf = b""
    deadline = time.time() + timeout
    while marker not in buf and time.time() < deadline:
        try:
            chunk = sock.recv(4096)
        except TimeoutError:
            break
        if not chunk:
            break
        buf += chunk
    return buf


def _request(port, path, auth="user:pass", version="Ntrip/2.0"):
    import socket
    sock = socket.create_connection((HOST, port), timeout=3)
    head = f"GET {path} HTTP/1.1\r\nHost: {HOST}:{port}\r\n"
    head += f"Ntrip-Version: {version}\r\n"
    head += "User-Agent: NTRIP test/1.0\r\n"
    if auth is not None:
        token = base64.b64encode(auth.encode()).decode()
        head += f"Authorization: Basic {token}\r\n"
    head += "\r\n"
    sock.sendall(head.encode())
    return sock


def test_parse_gga():
    gga = parse_gga("$GPGGA,123519,6008.607,N,02457.551,E,1,08,0.9,45.4,M,46.9,M,,*55")
    assert gga is not None
    assert abs(gga["lat"] - 60.143450) < 1e-5
    assert abs(gga["lon"] - 24.959183) < 1e-5
    assert gga["quality"] == "1"


def test_parse_gga_south_west():
    gga = parse_gga("$GNGGA,000001,6000.000,S,02500.000,W,1,08,0.9,45.4,M,46.9,M,,")
    assert gga is not None
    assert gga["lat"] == pytest.approx(-60.0)
    assert gga["lon"] == pytest.approx(-25.0)


def test_parse_gga_malformed():
    assert parse_gga("hello world") is None
    assert parse_gga("$GPGGA,123519,XX,N,,E,1,08") is None


def test_parse_request():
    data = (b"GET /HELSON HTTP/1.1\r\nHost: x\r\n"
            b"Authorization: Basic dXNlcjpwYXNz\r\n\r\n")
    method, path, headers = parse_request(data)
    assert method == "GET"
    assert path == "/HELSON"
    assert headers["authorization"].startswith("Basic ")


def test_sourcetable_lists_mountpoints():
    table = sourcetable_text()
    assert table.startswith("SOURCETABLE 200 OK")
    assert "STR;HELSON;" in table
    assert "STR;TMPNOR;" in table
    assert table.rstrip().endswith("ENDSOURCETABLE")


def test_caster_sourcetable(caster):
    port = caster.server_address[1]
    sock = _request(port, "/")
    resp = _recv_until(sock, b"ENDSOURCETABLE")
    sock.close()
    assert b"SOURCETABLE 200 OK" in resp
    assert b"STR;HELSON;" in resp


def test_caster_mountpoint_streams_rtcm(caster):
    port = caster.server_address[1]
    sock = _request(port, "/HELSON")
    resp = _recv_until(sock, b"Content-Type: gnss/data")
    # keep reading binary stream for a moment
    time.sleep(1.0)
    try:
        sock.settimeout(1.0)
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            resp += chunk
    except TimeoutError:
        pass
    sock.close()
    assert b"200 OK" in resp
    assert b"\xd3" in resp  # RTCM preamble in the stream


def test_caster_unknown_mountpoint_404(caster):
    port = caster.server_address[1]
    sock = _request(port, "/NOSUCH")
    resp = _recv_until(sock, b"\r\n\r\n")
    sock.close()
    assert b"404" in resp


def test_caster_bad_credentials_401(caster):
    port = caster.server_address[1]
    sock = _request(port, "/HELSON", auth="user:wrong")
    resp = _recv_until(sock, b"\r\n\r\n")
    sock.close()
    assert b"401" in resp


def test_caster_no_auth_401(caster):
    port = caster.server_address[1]
    sock = _request(port, "/HELSON", auth=None)
    resp = _recv_until(sock, b"\r\n\r\n")
    sock.close()
    assert b"401" in resp


def test_caster_receives_gga(caster):
    port = caster.server_address[1]
    sock = _request(port, "/HELSON")
    _recv_until(sock, b"Content-Type: gnss/data")
    gga = "$GPGGA,123519,6008.607,N,02457.551,E,1,08,0.9,45.4,M,46.9,M,,*55"
    sock.sendall((gga + "\r\n").encode())
    deadline = time.time() + 3
    while not NtripCasterHandler.gga_seen and time.time() < deadline:
        time.sleep(0.05)
    sock.close()
    assert NtripCasterHandler.gga_seen
    seen = NtripCasterHandler.gga_seen[0]
    assert seen["lat"] == pytest.approx(60.143450, abs=1e-4)
    assert seen["lon"] == pytest.approx(24.959183, abs=1e-4)
