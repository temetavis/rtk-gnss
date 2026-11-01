# NTRIP — Networked Transport of RTCM via Internet Protocol

NTRIP is the HTTP-based protocol used to deliver RTK correction streams from a
**caster** to **rovers** over the internet (usually cellular). It is
standardized in **RFC 9100** (successor of the original BKG paper).

## The three roles

```
   NTRIP Server ----push----> NTRIP Caster <----pull---- NTRIP Client (rover)
   (reference station/network)   (HTTP front end)        (GNSS receiver)
```

- **Server**: a reference station or network processing center that pushes one
  correction stream to the caster.
- **Caster**: an HTTP front-end multiplexing many streams ("mountpoints"),
  handling client authentication and routing.
- **Client**: the rover, requesting a mountpoint and feeding corrections into
  its GNSS receiver; also sends its position upstream.

## Protocol essentials (NTRIP 2.0)

A client's request looks like plain HTTP, but with custom headers and
`NTRIP` as the method token:

```
GET /MOUNTPOINT HTTP/1.1
Host: caster.example.com:2101
Ntrip-Version: Ntrip/2.0
User-Agent: NTRIP myclient/1.0
Authorization: Basic <base64(user:password)>
```

Caster replies, then immediately streams binary RTCM data with no further
framing:

```
HTTP/1.1 200 OK
Ntrip-Version: Ntrip/2.0
Content-Type: gnss/data
```

Error responses:

| Status | Meaning |
|---|---|
| 401 Unauthorized | bad credentials |
| 403 Forbidden | user not entitled to this mountpoint |
| 404 Not Found | unknown mountpoint |
| SOURCETABLE reply | response to `GET /` — the caster's mountpoint list |

## GGA upload (why the rover talks back)

For **VRS-type network RTK**, the caster needs the rover's approximate position
to generate tailored corrections. The client sends a line like:

```
$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47
```

up the same TCP connection every ~5–10 s. The caster/parser extracts
lat/lon/quality indicator. If no GGA arrives, VRS services degrade or stop.

## SOURCETABLE

`GET /` returns a table with `STR` lines per mountpoint: name, identifier,
format (e.g. `RTCM 3.2`), format-details (message list), carrier, nav-system,
network, country, lat/lon, authentication scheme, fee, and extra info. The
NMEA field (`N`) marks mountpoints that require GGA.

## Practical notes for operating a caster

- Default port 2101 is convention; 80/443 used for HTTP(S).
- Many rovers/mountpoints use plain HTTP — credentials travel in clear
  unless TLS (NTRIP 2.0 over TLS) is used.
- Latency is critical: monitor stream age and drop stale data.
- 1 caster → thousands of clients per mountpoint (fan-out).

## The exercise

`exercises/ntrip/caster.py` implements a real, loopback-only mock caster:

- parses client `GET /MOUNT` requests, Basic auth, and NTRIP version headers
- validates mountpoints against a built-in sourcetable
- parses `GPGGA` lines from the client (the VRS position flow)
- broadcasts a synthetic RTCM byte stream

Client: `exercises/ntrip/client.py`.
Tests: `tests/test_ntrip.py` exercise the full protocol conversation.
