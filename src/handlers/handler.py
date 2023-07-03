from abc import ABC, abstractmethod

from unsync import unsync

from src.providers.alertmanager.typings import AlertBody
from src.providers.consensus.typings import BlockHeaderFullResponse

# Enough count for different handlers to store in memory
KEEP_MAX_SENT_ALERTS = 10


class WatcherHandler(ABC):
    sent_alerts: list[AlertBody] = []

    def alert_is_sent(self, current: AlertBody):
        return str(current.annotations) in [str(s.annotations) for s in self.sent_alerts]

    @unsync
    @abstractmethod
    def handle(self, watcher, head: BlockHeaderFullResponse):
        """
        Implement this method to handle new head.
        It will be called async and return BlockDetailsResponse.
        """
        pass  # pylint: disable=unnecessary-pass

    def send_alert(self, watcher, alert: AlertBody):
        if not self.alert_is_sent(alert):
            watcher.alertmanager.send_alerts([alert])
            self.sent_alerts.append(alert)
            if len(self.sent_alerts) > KEEP_MAX_SENT_ALERTS:
                self.sent_alerts.pop(0)
