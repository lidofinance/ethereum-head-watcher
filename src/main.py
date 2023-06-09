from prometheus_client import start_http_server

from src import variables
from src.handlers.fork import ForkHandler
from src.handlers.slashing import SlashingHandler
from src.metrics.healthcheck_server import start_pulse_server
from src.metrics.logging import logging
from src.watcher import Watcher

logger = logging.getLogger()


def main():
    logger.info({'msg': 'Ethereum head watcher startup.'})

    logger.info({'msg': f'Start healthcheck server for Docker container on port {variables.HEALTHCHECK_SERVER_PORT}'})
    start_pulse_server()

    logger.info({'msg': f'Start http server with prometheus metrics on port {variables.PROMETHEUS_PORT}'})
    start_http_server(variables.PROMETHEUS_PORT)

    if variables.DRY_RUN:
        logger.warning({'msg': 'Dry run mode enabled! No alerts will be sent.'})

    handlers = [
        SlashingHandler(),
        ForkHandler(),
        # ExitsHandler(), ???
        # FinalityHandler(), ???
    ]
    Watcher(handlers).run()


if __name__ == "__main__":
    errors = variables.check_uri_required_variables()
    variables.raise_from_errors(errors)
    main()
