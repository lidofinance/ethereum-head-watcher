from abc import ABC


class Alert(ABC):
    name: str
    severity: str
