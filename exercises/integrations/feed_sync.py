"""Idempotent partner-data sync: the pattern behind "automations between
the software we use".

A partner sends reference station metadata; we upsert it into our own
database. The job must be safe to run twice (idempotent) and must record
what changed, so it can be scheduled hourly/daily without fear.
"""

from ..db.engine import utcnow


class FeedSync:
    def __init__(self, store):
        self.store = store
        self.last_run = None
        self.last_report = None

    def _find_by_code(self, code):
        rows = self.store.select("reference_stations", where={"code": code})
        return rows[0] if rows else None

    def sync_stations(self, partner_feed):
        """Upssert stations from a partner feed.

        partner_feed: list of dicts with keys
            code, name, lat, lon, owner, status
        Returns a report dict. Running twice changes nothing the second
        time (idempotency is asserted in the tests).
        """
        created, updated, unchanged = [], [], []
        for item in partner_feed:
            existing = self._find_by_code(item["code"])
            if existing is None:
                self.store.add_station(
                    code=item["code"], name=item["name"],
                    lat=item["lat"], lon=item["lon"],
                    owner=item.get("owner", ""),
                    status=item.get("status", "online"),
                    metadata=item.get("metadata"))
                created.append(item["code"])
            else:
                changes = {}
                for key in ("name", "owner", "status"):
                    if key in item and item[key] != existing[key]:
                        changes[key] = item[key]
                if abs(item["lat"] - existing["lat"]) > 1e-9:
                    changes["lat"] = item["lat"]
                if abs(item["lon"] - existing["lon"]) > 1e-9:
                    changes["lon"] = item["lon"]
                if changes:
                    self.store.update("reference_stations", existing["id"],
                                      **changes)
                    updated.append({"code": item["code"],
                                    "changed": sorted(changes)})
                else:
                    unchanged.append(item["code"])

        report = {"created": created, "updated": updated,
                  "unchanged": unchanged, "ran_at": utcnow().isoformat()}
        self.last_run = utcnow()
        self.last_report = report
        return report
