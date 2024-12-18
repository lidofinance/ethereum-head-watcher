from prometheus_client import start_http_server
from web3.middleware import simple_cache_middleware

from src import variables
from src.handlers.el_triggered_exit import ElTriggeredExitHandler
from src.handlers.exit import ExitsHandler
from src.handlers.fork import ForkHandler
from src.handlers.slashing import SlashingHandler
from src.handlers.consolidation import ConsolidationHandler
from src.keys_source.base_source import SourceType
from src.keys_source.file_source import FileSource
from src.keys_source.keys_api_source import KeysApiSource
from src.metrics.healthcheck_server import start_pulse_server
from src.metrics.logging import logging
from src.metrics.prometheus.basic import BUILD_INFO
from src.utils.build import get_build_info
from src.watcher import Watcher
from src.web3py.extensions import FallbackProviderModule, LidoContracts
from src.web3py.middleware import metrics_collector
from src.web3py.typings import Web3

logger = logging.getLogger()


def main():
    BUILD_INFO.info(get_build_info())

    logger.info({'msg': 'Ethereum head watcher startup.'})

    logger.info({'msg': f'Start healthcheck server for Docker container on port {variables.HEALTHCHECK_SERVER_PORT}'})
    start_pulse_server()

    logger.info({'msg': f'Start http server with prometheus metrics on port {variables.PROMETHEUS_PORT}'})
    start_http_server(variables.PROMETHEUS_PORT)

    if variables.KEYS_SOURCE == SourceType.KEYS_API.value:
        keys_source = KeysApiSource()
        web3 = Web3(
            FallbackProviderModule(
                variables.EXECUTION_CLIENT_URI, request_kwargs={'timeout': variables.EL_REQUEST_TIMEOUT}
            )
        )
        web3.attach_modules(
            {
                'lido_contracts': LidoContracts,
            }
        )
        web3.middleware_onion.add(metrics_collector)
        web3.middleware_onion.add(simple_cache_middleware)
    elif variables.KEYS_SOURCE == SourceType.FILE.value:
        keys_source = FileSource()
        web3 = None
    else:
        raise ValueError(f'Unknown keys source: {variables.KEYS_SOURCE}')
    logger.info({'msg': f'Using keys source: {variables.KEYS_SOURCE}'})

    if variables.DRY_RUN:
        logger.warning({'msg': 'Dry run mode enabled! No alerts will be sent.'})

    handlers = [
        SlashingHandler(),
        ForkHandler(),
        ExitsHandler(),
        # FinalityHandler(), ???
        ConsolidationHandler(),
        ElTriggeredExitHandler()
    ]
    Watcher(handlers, keys_source, web3).run()


if __name__ == "__main__":
    errors = variables.check_uri_required_variables()
    variables.raise_from_errors(errors)
    main()
