"""Named queries used by the service layer, mirrored in queries.sql."""

from datetime import timedelta

from .engine import MemoryStore, PostgresStore, utcnow  # noqa: F401


def stations_summary(store):
    """Station list with latest metric joined in (dashboard view)."""
    out = []
    for st in store.select("reference_stations", order_by="code"):
        latest = store.latest_metric(st["id"])
        out.append({
            "id": st["id"],
            "code": st["code"],
            "name": st["name"],
            "lat": st["lat"],
            "lon": st["lon"],
            "status": st["status"],
            "latest_stream_age_s": latest["stream_age_s"] if latest else None,
            "latest_recorded_at": latest["recorded_at"].isoformat()
                                  if latest else None,
        })
    return out


def stations_with_stale_streams(store, max_age_s=15.0):
    return store.stale_stations(max_age_s)


def firing_alerts(store):
    rows = [a for a in store.select("alerts")
            if a["state"] == "firing"]
    codes = {st["id"]: st["code"] for st in store.select("reference_stations")}
    return [{
        "id": a["id"],
        "station": codes.get(a["station_id"]),
        "kind": a["kind"],
        "severity": a["severity"],
        "raised_at": a["raised_at"].isoformat(),
    } for a in rows]


def mountpoint_usage_last_day(store):
    cutoff = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    usage = {}
    for s in store.select("sessions"):
        if s["started_at"] >= cutoff:
            u = usage.setdefault(s["mountpoint"], {"sessions": 0, "bytes": 0})
            u["sessions"] += 1
            u["bytes"] += s["bytes_sent"]
    return usage


def cycle_slips_now_vs_baseline(store, window_minutes=15):
    """Per station: recent slip rate vs same window a day earlier."""
    now = utcnow()
    window = timedelta(minutes=window_minutes)
    day_ago = timedelta(hours=24)
    out = {}
    for st in store.select("reference_stations"):
        recent = [m for m in store.select("station_metrics")
                  if m["station_id"] == st["id"]
                  and m["recorded_at"] > now - window]
        baseline = [m for m in store.select("station_metrics")
                    if m["station_id"] == st["id"]
                    and now - window - day_ago < m["recorded_at"]
                    < now - day_ago]

        def avg(rows):
            return sum(r["cycle_slips"] for r in rows) / len(rows) if rows else 0.0

        out[st["code"]] = {"now": avg(recent), "baseline": avg(baseline)}
    return out
