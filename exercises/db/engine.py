"""Portable station-network store.

Two backends behind one API:
- psycopg + PostgreSQL when DATABASE_URL is set and reachable (production-like)
- an in-process store otherwise, so every exercise runs anywhere

The store backs the API, monitoring, and integration exercises.
"""

import json
import os
import threading
from datetime import datetime, timedelta, timezone

def utcnow():
    return datetime.now(timezone.utc)


class Record(dict):
    """Dict with attribute access, standing in for a table row."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as err:
            raise AttributeError(key) from err


class MemoryStore:
    """In-process relational-ish store with row ids and transactions."""

    _TABLES = (
        "reference_stations", "mountpoints", "accounts", "sessions",
        "station_metrics", "alerts",
    )

    def __init__(self):
        self._lock = threading.RLock()
        self._data = {name: {} for name in self._TABLES}
        self._sequences = {name: 0 for name in self._TABLES}

    def _next_id(self, table):
        self._sequences[table] += 1
        return self._sequences[table]

    # -- generic CRUD -----------------------------------------------------
    def insert(self, table, **fields):
        with self._lock:
            row = Record(fields)
            row["id"] = self._next_id(table)
            self._data[table][row["id"]] = row
            return row

    def get(self, table, row_id):
        with self._lock:
            return self._data[table].get(row_id)

    def update(self, table, row_id, **fields):
        with self._lock:
            row = self._data[table].get(row_id)
            if row is None:
                raise KeyError(f"{table}#{row_id} not found")
            row.update(fields)
            return row

    def delete(self, table, row_id):
        with self._lock:
            return self._data[table].pop(row_id, None)

    def select(self, table, where=None, order_by=None, desc=False):
        with self._lock:
            rows = list(self._data[table].values())
        if where:
            rows = [r for r in rows if all(r[k] == v for k, v in where.items()
                                          if not callable(v))]
            rows = [r for r in rows
                    if all(w(r) for k, w in where.items() if callable(w))]
        if order_by:
            rows.sort(key=lambda r: r.get(order_by), reverse=desc)
        return rows

    # -- domain helpers ----------------------------------------------------
    def add_station(self, code, name, lat, lon, status="online", owner="",
                    metadata=None):
        return self.insert("reference_stations", code=code, name=name,
                           owner=owner, lat=lat, lon=lon, status=status,
                           metadata=json.dumps(metadata or {}),
                           created_at=utcnow())

    def add_metric(self, station_id, stream_age_s, sats_tracked,
                   cycle_slips, phase_noise_mm, recorded_at=None):
        return self.insert(
            "station_metrics", station_id=station_id,
            stream_age_s=stream_age_s, sats_tracked=sats_tracked,
            cycle_slips=cycle_slips, phase_noise_mm=phase_noise_mm,
            recorded_at=recorded_at or utcnow())

    def latest_metric(self, station_id):
        rows = [m for m in self.select("station_metrics",
                                       where={"station_id": station_id})
                if station_id is not None]
        if not rows:
            return None
        # tie-break on row id: metrics recorded within the same timestamp
        # still order by insertion, so the newest poll always wins
        return max(rows, key=lambda m: (m["recorded_at"], m["id"]))

    def stale_stations(self, max_age_s=15.0):
        """Online/degraded stations whose newest metric is older than max_age."""
        now = utcnow()
        stale = []
        for st in self.select("reference_stations"):
            if st["status"] in ("offline", "maintenance"):
                continue
            latest = self.latest_metric(st["id"])
            if latest is None or (now - latest["recorded_at"]).total_seconds() > max_age_s:
                stale.append(st)
        return stale

    def add_alert(self, station_id, kind, severity, details=None):
        return self.insert("alerts", station_id=station_id, kind=kind,
                           severity=severity,
                           details=json.dumps(details or {}),
                           raised_at=utcnow(), resolved_at=None,
                           state="firing")

    def firing_alert(self, station_id, kind):
        for a in self.select("alerts", order_by="raised_at", desc=True):
            if (a["station_id"] == station_id and a["kind"] == kind
                    and a["state"] == "firing"):
                return a
        return None

    def resolve_alert(self, alert_id):
        return self.update("alerts", alert_id, state="resolved",
                           resolved_at=utcnow())

    # -- account / session helpers ------------------------------------------
    def add_account(self, username, password_hash, subscription="standard",
                    api_token_hash=None):
        return self.insert("accounts", username=username,
                           password_hash=password_hash,
                           subscription=subscription,
                           api_token_hash=api_token_hash,
                           active=True, created_at=utcnow())

    def find_account(self, username):
        for a in self.select("accounts"):
            if a["username"] == username:
                return a
        return None

    def add_session(self, account_id, mountpoint, bytes_sent=0,
                    rover_lat=None, rover_lon=None):
        return self.insert("sessions", account_id=account_id,
                           mountpoint=mountpoint, started_at=utcnow(),
                           ended_at=None, bytes_sent=bytes_sent,
                           rover_lat=rover_lat, rover_lon=rover_lon)

    def close_session(self, session_id, bytes_sent):
        return self.update("sessions", session_id, ended_at=utcnow(),
                           bytes_sent=bytes_sent)


def connect():
    """Return the process-wide store (psycopg-backed when DATABASE_URL works)."""
    global _STORE
    try:
        return _STORE
    except NameError:
        _STORE = _build_store()
        return _STORE


def _build_store():
    url = os.environ.get("DATABASE_URL")
    if url:
        try:
            import psycopg  # noqa: F401
            return PostgresStore(url)
        except Exception:
            pass
    return MemoryStore()


class PostgresStore:
    """psycopg-backed store exposing the same helpers as MemoryStore.

    Requires exercises/db/schema.sql to be applied. Used when DATABASE_URL
    points at a live PostgreSQL.
    """

    def __init__(self, url):
        import psycopg
        self._conn = psycopg.connect(url, autocommit=False)

    def _roundtrip(self, table, row):
        rec = Record({k: v for k, v in row.items()})
        rec["id"] = row[0] if not isinstance(row, dict) else row["id"]
        return rec

    def execute(self, sql, params=()):
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.description:
                cols = [d.name for d in cur.description]
                rows = [Record(zip(cols, r)) for r in cur.fetchall()]
            else:
                rows = None
        self._conn.commit()
        return rows

    def close(self):
        self._conn.close()
