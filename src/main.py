from prometheus_client import start_http_server

from src import variables
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

    logger.info({'msg': 'Start watching for slashing events.'})
    handlers = [
        SlashingHandler(),
        # ExitsHandler(), ???
        # FinalityHandler(), ???
    ]
    Watcher(handlers).run()


if __name__ == "__main__":
    errors = variables.check_uri_required_variables()
    variables.raise_from_errors(errors)
    main()
