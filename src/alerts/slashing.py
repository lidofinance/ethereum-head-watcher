from datetime import datetime, timedelta, timezone

from src.alerts.alert import Alert
from src.providers.alertmanager.typings import AlertBody, Labels, Annotations, ISODateString


class CommonAlert(Alert):
    def __init__(self, name: str, severity: str):
        self.name = name
        self.severity = severity

    def build_body(self, summary: str, description: str, additional_labels=None) -> AlertBody:
        now = datetime.now(timezone(timedelta(hours=0)))  # Must be always in UTC
        starts_at = now.isoformat()
        ends_at = (now + timedelta(seconds=5)).isoformat()
        return AlertBody(
            startsAt=ISODateString(starts_at.replace("+00:00", "") + "Z"),
            endsAt=ISODateString(ends_at.replace("+00:00", "") + "Z"),
            labels=Labels(
                alertname=self.name + str(now.timestamp() * 1000),
                severity=self.severity,
                **(additional_labels or {}),
            ),
            annotations=Annotations(
                summary=summary,
                description=description,
            ),
        )
