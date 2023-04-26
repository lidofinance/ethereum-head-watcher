import logging
from dataclasses import asdict

from src.metrics.prometheus.basic import ALERTMANAGER_REQUESTS_DURATION
from src.providers.alertmanager.typings import AlertBody
from src.providers.http_provider import HTTPProvider

logger = logging.getLogger()


class AlertmanagerClient(HTTPProvider):
    PROMETHEUS_HISTOGRAM = ALERTMANAGER_REQUESTS_DURATION

    ALERTS = "api/v1/alerts"

    def send_alerts(self, alerts: list[AlertBody]):
        logger.debug({'msg': f'Sending {len(alerts)} alerts', 'alerts': [asdict(alert) for alert in alerts]})
        self._post(self.ALERTS, query_body=[asdict(alert) for alert in alerts])
