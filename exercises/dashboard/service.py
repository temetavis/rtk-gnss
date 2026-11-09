"""Mock RTK correction-service health model.

Simulates the kind of telemetry a commercial network RTK provider monitors:
reference stations, caster mountpoint streams, correction latency and rover
sessions. Everything is deterministic for a given seed so tests (and the
dashboard UI) are reproducible.

Status thresholds (typical industry rules of thumb):
  - healthy : latency < 2 s and station streaming, no recent outage
  - degraded: latency 2-5 s, or a short outage in the last hour
  - down    : no data received for over 60 s
"""

import random
import time

STATIONS = [
    # name, identifier, lat, lon
    ("HELSON", "Helsinki south", 60.1699, 24.9384),
    ("TMPNOR", "Tampere north", 61.4981, 23.7610),
    ("TURSW", "Turku southwest", 60.4518, 22.2666),
    ("OULUN", "Oulu north", 65.0121, 25.4651),
    ("ROVEM", "Rovaniemi east", 66.5000, 25.7167),
]

LATENCY_HEALTHY = 2.0     # seconds
LATENCY_DEGRADED = 5.0    # seconds
OUTAGE_WINDOW = 3600.0    # seconds
SILENCE_DOWN = 60.0       # seconds since last message


def classify(latency_s, seconds_since_message, outage_recently):
    """Classify a stream into 'healthy', 'degraded' or 'down'."""
    if seconds_since_message > SILENCE_DOWN:
        return "down"
    if latency_s > LATENCY_DEGRADED or outage_recently:
        return "degraded"
    if latency_s > LATENCY_HEALTHY:
        return "degraded"
    return "healthy"


def simulate_station_health(seed, station, now):
    """Produce one deterministic health record for a station."""
    rng = random.Random(f"{seed}:{station[0]}:{int(now // 60)}")
    name, identifier, lat, lon = station

    # 20% of station-minutes are degraded, 5% down, one station is
    # pinned down when the seed ends in "outage" so tests have a stable case.
    roll = rng.random()
    if seed.endswith("outage") and name == "TURSW":
        roll = 0.99
    if roll > 0.95:
        latency = None
        silence = SILENCE_DOWN + rng.uniform(60, 600)
    elif roll > 0.75:
        latency = rng.uniform(LATENCY_HEALTHY, LATENCY_DEGRADED * 1.5)
        silence = rng.uniform(0.5, 5.0)
    else:
        latency = rng.uniform(0.3, LATENCY_HEALTHY * 0.9)
        silence = rng.uniform(0.2, 2.0)

    outage_recently = rng.random() < 0.1
    status = classify(latency if latency is not None else 99.0,
                      silence, outage_recently)

    return {
        "name": name,
        "identifier": identifier,
        "lat": lat,
        "lon": lon,
        "format": "RTCM 3.2",
        "status": status,
        "latency_s": round(latency, 2) if latency is not None else None,
        "seconds_since_message": round(silence, 1),
        "messages_per_minute": 0 if status == "down"
        else int(rng.uniform(40, 70)),
        "rover_sessions": int(rng.uniform(0, 25)),
        "uptime_24h": round(rng.uniform(0.97, 1.0), 4) if status != "down"
        else round(rng.uniform(0.5, 0.9), 4),
        "outage_recently": outage_recently,
    }


def service_health(seed="demo", now=None):
    """Full service health snapshot: stations plus aggregate counters."""
    now = now if now is not None else time.time()
    stations = [simulate_station_health(seed, s, now) for s in STATIONS]
    counts = {s: 0 for s in ("healthy", "degraded", "down")}
    for st in stations:
        counts[st["status"]] += 1
    total_rover_sessions = sum(st["rover_sessions"] for st in stations)
    latencies = [st["latency_s"] for st in stations
                 if st["latency_s"] is not None]
    overall = ("down" if counts["down"] > 0
               else "degraded" if counts["degraded"] > 0
               else "healthy")
    return {
        "service": "MockNet RTK corrections",
        "generated_at": round(now, 1),
        "seed": seed,
        "overall_status": overall,
        "stations_total": len(stations),
        "stations_healthy": counts["healthy"],
        "stations_degraded": counts["degraded"],
        "stations_down": counts["down"],
        "rover_sessions": total_rover_sessions,
        "median_latency_s": round(sorted(latencies)[len(latencies) // 2], 2)
        if latencies else None,
        "stations": stations,
    }
