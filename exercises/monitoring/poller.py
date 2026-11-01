"""Poller: reads the latest observation metrics per station and records them.

In production the poller pulls from the caster or station feeds; here it
reads a simulated station feed so the whole monitoring loop is testable.
"""

from ..db.engine import utcnow


class SimulatedStation:
    """A station whose health drifts on a script, for testing the loop."""

    def __init__(self, station_id, stream_age=1.0, sats=12, slips=2,
                 noise=1.0):
        self.station_id = station_id
        self.stream_age = stream_age
        self.sats = sats
        self.slips = slips
        self.noise = noise

    def set_state(self, **changes):
        for key, value in changes.items():
            setattr(self, key, value)

    def latest_metric(self):
        return {
            "stream_age_s": self.stream_age,
            "sats_tracked": self.sats,
            "cycle_slips": self.slips,
            "phase_noise_mm": self.noise,
            "recorded_at": utcnow(),
        }


class Poller:
    """Polls stations and writes their metrics into the store."""

    def __init__(self, store, stations):
        self.store = store
        self.stations = stations
        self.last_polled = {}

    def poll_all(self):
        for st in self.stations:
            m = st.latest_metric()
            self.store.add_metric(st.station_id,
                                  m["stream_age_s"], m["sats_tracked"],
                                  m["cycle_slips"], m["phase_noise_mm"],
                                  recorded_at=m["recorded_at"])
            self.last_polled[st.station_id] = m["recorded_at"]
        return len(self.stations)
