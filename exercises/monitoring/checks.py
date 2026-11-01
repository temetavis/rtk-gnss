"""Check engine: threshold rules with flap suppression and auto-resolve.

The engine keeps per-station state so a flaky link doesn't page you all
night: a check must fail N consecutive times before an alert fires, and
recover M consecutive times before it resolves.
"""

from .alerts import Alert
from ..db.engine import utcnow

CRITICAL = "critical"
WARNING = "warning"


class Check:
    """A single monitoring rule, e.g. 'stream age under 15 s'."""

    def __init__(self, kind, evaluate, severity=WARNING,
                 fire_after=3, resolve_after=2):
        self.kind = kind
        self.evaluate = evaluate    # fn(metric) -> bool (True = bad)
        self.severity = severity
        self.fire_after = fire_after
        self.resolve_after = resolve_after
        self._bad_streak = {}      # station_id -> consecutive bad results
        self._good_streak = {}

    def process(self, station_id, metric):
        """Returns an Alert if one should be (re)raised, else None."""
        bad = self.evaluate(metric)
        if bad:
            self._good_streak.pop(station_id, None)
            self._bad_streak[station_id] = self._bad_streak.get(station_id, 0) + 1
            if self._bad_streak[station_id] == self.fire_after:
                return Alert(station_id=station_id, kind=self.kind,
                             severity=self.severity,
                             details={"value": _snapshot(metric)})
        else:
            self._bad_streak.pop(station_id, None)
        return None

    def is_recovered(self, station_id, metric):
        """True when the station has been good for resolve_after checks."""
        if self.evaluate(metric):
            self._good_streak.pop(station_id, None)
            return False
        self._bad_streak.pop(station_id, None)
        self._good_streak[station_id] = self._good_streak.get(station_id, 0) + 1
        return self._good_streak[station_id] >= self.resolve_after

    def reset(self, station_id):
        self._bad_streak.pop(station_id, None)
        self._good_streak.pop(station_id, None)


def _snapshot(metric):
    keys = ("stream_age_s", "sats_tracked", "cycle_slips", "phase_noise_mm")
    return {k: metric[k] for k in keys if k in metric}


class CheckEngine:
    """Runs checks over the latest metrics of every station.

    Maintains one alert per (station, check) incident in the store,
    mirroring the alerts table and its firing/resolved state machine.
    """

    def __init__(self, store, sink, checks):
        self.store = store
        self.sink = sink
        self.checks = checks

    def run_once(self):
        """Evaluate all stations once; returns number of new alerts."""
        new_alerts = 0
        for station in self.store.select("reference_stations"):
            if station["status"] in ("offline", "maintenance"):
                continue
            metric = self.store.latest_metric(station["id"])
            if metric is None:
                continue
            for check in self.checks:
                existing = self.store.firing_alert(station["id"], check.kind)
                if existing is None:
                    alert = check.process(station["id"], metric)
                    if alert is not None:
                        stored = self.store.add_alert(
                            station["id"], check.kind, check.severity,
                            alert.details)
                        alert.id = stored["id"]
                        alert.raised_at = stored["raised_at"]
                        self.sink.fire(alert)
                        new_alerts += 1
                else:
                    if check.is_recovered(station["id"], metric):
                        self.store.resolve_alert(existing["id"])
                        check.reset(station["id"])
                        for a in self.sink.alerts:
                            if a.id == existing["id"] and a.state == "firing":
                                a.resolve(existing.get("resolved_at"))
        return new_alerts


def default_checks(stream_age_limit=15.0, min_sats=5, slip_limit=20,
                   noise_limit_mm=3.0):
    """The standard rule set for a reference station network."""
    return [
        Check("stale_stream",
              lambda m: m["stream_age_s"] > stream_age_limit,
              severity=CRITICAL, fire_after=2, resolve_after=2),
        Check("few_satellites",
              lambda m: m["sats_tracked"] < min_sats,
              severity=WARNING, fire_after=3, resolve_after=2),
        Check("cycle_slips",
              lambda m: m["cycle_slips"] > slip_limit,
              severity=WARNING, fire_after=3, resolve_after=3),
        Check("phase_noise",
              lambda m: m["phase_noise_mm"] > noise_limit_mm,
              severity=WARNING, fire_after=3, resolve_after=3),
    ]
