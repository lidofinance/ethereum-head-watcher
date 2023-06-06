from dataclasses import dataclass
from typing import NewType, Optional

from src.utils.dataclass import Nested

ISODateString = NewType('ISODateString', str)


@dataclass
class Labels:
    alertname: str
    severity: str
    mentions: Optional[str] = None


@dataclass
class Annotations:
    summary: str
    description: str


@dataclass
class AlertBody(Nested):
    startsAt: ISODateString
    endsAt: ISODateString
    labels: Labels
    annotations: Annotations
