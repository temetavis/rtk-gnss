"""Alert objects and severity model for network monitoring."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Alert:
    station_id: int
    kind: str
    severity: str            # 'warning' | 'critical'
    details: dict = field(default_factory=dict)
    state: str = "firing"     # 'firing' | 'resolved'
    raised_at: datetime | None = None
    resolved_at: datetime | None = None
    id: int | None = None

    def resolve(self, at):
        self.state = "resolved"
        self.resolved_at = at


class AlertSink:
    """Collects alerts; in production this pages, emails, or posts webhooks."""

    def __init__(self):
        self.alerts = []

    def fire(self, alert: Alert):
        self.alerts.append(alert)

    def firing(self):
        return [a for a in self.alerts if a.state == "firing"]

    def count(self, severity=None):
        return sum(1 for a in self.alerts
                   if severity is None or a.severity == severity)
