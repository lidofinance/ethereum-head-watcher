from prometheus_client import start_http_server
from web3.middleware import simple_cache_middleware

from src import variables
from src.handlers.consolidation import ConsolidationHandler
from src.handlers.el_triggered_exit import ElTriggeredExitHandler
from src.handlers.execution_requests import ExecutionRequestsHandler
from src.handlers.exit import ExitsHandler
from src.handlers.fork import ForkHandler
from src.handlers.handler import WatcherHandler
from src.handlers.slashing import SlashingHandler
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

CONFIGURABLE_HANDLER_TYPES: dict[str, type[WatcherHandler]] = {
    'slashing': SlashingHandler,
    'exits': ExitsHandler,
    'consolidation': ConsolidationHandler,
    'el_triggered_exit': ElTriggeredExitHandler,
    'execution_requests': ExecutionRequestsHandler,
}


def build_handlers(enabled_handlers: list[str] | None = None) -> list[WatcherHandler]:
    handler_names = list(CONFIGURABLE_HANDLER_TYPES) if enabled_handlers is None else enabled_handlers
    if not handler_names:
        raise ValueError('ENABLED_HANDLERS must contain at least one handler name')

    duplicate_handlers = sorted({name for name in handler_names if handler_names.count(name) > 1})
    if duplicate_handlers:
        raise ValueError(f'Duplicate handlers in ENABLED_HANDLERS: {", ".join(duplicate_handlers)}')

    unknown_handlers = sorted(set(handler_names) - CONFIGURABLE_HANDLER_TYPES.keys())
    if unknown_handlers:
        available_handlers = ', '.join(CONFIGURABLE_HANDLER_TYPES)
        raise ValueError(
            f'Unknown handlers in ENABLED_HANDLERS: {", ".join(unknown_handlers)}. '
            f'Available handlers: {available_handlers}'
        )

    handlers: list[WatcherHandler] = [ForkHandler()]
    handlers.extend(CONFIGURABLE_HANDLER_TYPES[name]() for name in handler_names)
    return handlers


def main():
    handlers = build_handlers(variables.parse_enabled_handlers(variables.ENABLED_HANDLERS))

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

    Watcher(handlers, keys_source, web3).run()


if __name__ == "__main__":
    errors = variables.check_uri_required_variables()
    variables.raise_from_errors(errors)
    main()
