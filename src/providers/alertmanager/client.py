import logging
from dataclasses import asdict

from src.metrics.prometheus.basic import ALERTMANAGER_REQUESTS_DURATION
from src.providers.alertmanager.typings import AlertBody
from src.providers.http_provider import HTTPProvider
from src.variables import NETWORK_NAME

logger = logging.getLogger()


class AlertmanagerClient(HTTPProvider):
    PROMETHEUS_HISTOGRAM = ALERTMANAGER_REQUESTS_DURATION

    ALERTS = "api/v1/alerts"

    def send_alerts(self, alerts: list[AlertBody]):
        alerts = [asdict(alert) for alert in alerts]
        for alert in alerts:
            alert['labels']['network'] = NETWORK_NAME
        logger.debug({'msg': f'Sending {len(alerts)} alerts', 'alerts': alerts})
        self._post(self.ALERTS, query_body=alerts)
