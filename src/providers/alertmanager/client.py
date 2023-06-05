import logging
from dataclasses import asdict

from src.metrics.prometheus.basic import ALERTMANAGER_REQUESTS_DURATION
from src.providers.alertmanager.typings import AlertBody
from src.providers.http_provider import HTTPProvider
from src.variables import (
    NETWORK_NAME,
    ALERTMANAGER_REQUEST_TIMEOUT,
    ALERTMANAGER_REQUEST_RETRY_COUNT,
    ALERTMANAGER_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS,
)

logger = logging.getLogger()


class AlertmanagerClient(HTTPProvider):
    PROMETHEUS_HISTOGRAM = ALERTMANAGER_REQUESTS_DURATION

    HTTP_REQUEST_TIMEOUT = ALERTMANAGER_REQUEST_TIMEOUT
    HTTP_REQUEST_RETRY_COUNT = ALERTMANAGER_REQUEST_RETRY_COUNT
    HTTP_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS = ALERTMANAGER_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS

    ALERTS = "api/v1/alerts"

    def send_alerts(self, alerts: list[AlertBody]):
        to_sent = [asdict(alert) for alert in alerts]
        for alert in to_sent:
            alert['labels']['network'] = NETWORK_NAME
        logger.debug({'msg': f'Sending {len(alerts)} alerts', 'alerts': to_sent})
        self._post(self.ALERTS, query_body=to_sent)
