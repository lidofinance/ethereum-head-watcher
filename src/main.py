import signal

from prometheus_client import start_http_server
from web3.middleware import simple_cache_middleware

from src import variables
from src.handlers.consolidation import ConsolidationHandler
from src.handlers.el_triggered_exit import ElTriggeredExitHandler
from src.handlers.exit import ExitsHandler
from src.handlers.fork import ForkHandler
from src.handlers.handler import WatcherHandler
from src.handlers.slashing import SlashingHandler
from src.keys_source.base_source import SourceType
from src.keys_source.file_source import FileSource
from src.keys_source.keys_api_source import KeysApiSource
from src.metrics.healthcheck_server import start_pulse_server
from src.metrics.logging import logging
from src.metrics.prometheus.basic import BUILD_INFO, SECRETS_RELOADS, Status
from src.secrets import SecretsWatcher
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


def apply_rotated_secrets(values: dict[str, str], watcher: Watcher) -> list[str]:
    """
    Swap in endpoints from a rotated secrets file, without a restart. Returns what changed.

    A restart would work and is what an environment-variable delivery would force, but it costs a
    full re-read of the validator set and of every Lido key — minutes with nothing watched, on
    every rotation. Each client here keeps its endpoints in a plain list that it walks per
    request, so replacing the list is enough; the execution layer needs its provider rebuilt,
    which leaves the Web3 instance, its middlewares and the contracts bound to it in place.
    """
    changed = []

    consensus_uri = _split(values.get('CONSENSUS_CLIENT_URI'))
    if consensus_uri and consensus_uri != watcher.consensus.hosts:
        watcher.consensus.hosts = consensus_uri
        changed.append('CONSENSUS_CLIENT_URI')

    alertmanager_uri = _split(values.get('ALERTMANAGER_URI'))
    if alertmanager_uri and alertmanager_uri != watcher.alertmanager.hosts:
        watcher.alertmanager.hosts = alertmanager_uri
        changed.append('ALERTMANAGER_URI')

    keys_api = getattr(watcher.keys_source, 'keys_api', None)
    keys_api_uri = _split(values.get('KEYS_API_URI'))
    if keys_api is not None and keys_api_uri and keys_api_uri != keys_api.hosts:
        keys_api.hosts = keys_api_uri
        changed.append('KEYS_API_URI')

    execution_uri = _split(values.get('EXECUTION_CLIENT_URI'))
    if watcher.execution is not None and execution_uri and execution_uri != variables.EXECUTION_CLIENT_URI:
        # `Web3.provider` is read-only in web3 6.x; the manager's is the settable one. The
        # middlewares (metrics, cache) live on the manager too, so they survive the swap, and the
        # contracts hold a reference to the Web3 instance rather than to the provider.
        watcher.execution.manager.provider = FallbackProviderModule(
            execution_uri, request_kwargs={'timeout': variables.EL_REQUEST_TIMEOUT}
        )
        variables.EXECUTION_CLIENT_URI = execution_uri
        changed.append('EXECUTION_CLIENT_URI')

    if changed:
        logger.info({'msg': f'Applied rotated secrets: {", ".join(changed)}'})
        SECRETS_RELOADS.labels(Status.SUCCESS.value).inc()
    return changed


def _split(value: str | None) -> list[str]:
    if not value:
        return []
    return [entry for entry in (part.strip() for part in value.split(',')) if entry]


def install_signal_handlers():
    """
    Make SIGTERM and SIGHUP stop the watcher the way Ctrl-C does.

    Python installs a disposition for SIGINT only, and this process is PID 1 in its container --
    the kernel does not apply a default action to a signal PID 1 has no handler for. So SIGTERM,
    which is what a pod termination is, would be dropped: the kubelet would wait out
    terminationGracePeriodSeconds and then SIGKILL, on every rollout and every node drain. The
    30 seconds are not the cost. The cost is that the last thing a SIGKILLed watcher does is
    unpredictable, while the SIGINT path unwinds the cycle it is in.

    Routed onto SIGINT rather than given a handler of their own because the loop already unwinds
    on KeyboardInterrupt, and `except Exception` in the cycle does not catch it.
    """
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, signal.default_int_handler)


def main():
    handlers = build_handlers(variables.parse_enabled_handlers(variables.ENABLED_HANDLERS))

    BUILD_INFO.info(get_build_info())

    logger.info({'msg': 'Ethereum head watcher startup.'})

    if variables.SECRETS_FILE_LOADED:
        logger.info({'msg': f'Configuration: {variables.SECRETS_FILE_PATH} over the environment'})
    else:
        logger.info(
            {'msg': f'Configuration: the environment (no secrets file at {variables.SECRETS_FILE_PATH})'}
        )

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

    watcher = Watcher(handlers, keys_source, web3)

    SecretsWatcher(
        variables.SECRETS_FILE_PATH,
        on_change=lambda values: apply_rotated_secrets(values, watcher),
        interval=variables.SECRETS_POLL_INTERVAL_IN_SECONDS,
        on_error=lambda: SECRETS_RELOADS.labels(Status.FAILURE.value).inc(),
    ).start()

    install_signal_handlers()

    try:
        watcher.run()
    except KeyboardInterrupt:
        # Reached from Ctrl-C and, through install_signal_handlers, from SIGTERM/SIGHUP. One line
        # so that a pod that went away on purpose is distinguishable in the logs from one that
        # was killed -- the two look identical from the outside, and only one of them is a bug.
        logger.info({'msg': 'Shutting down on a termination signal'})


if __name__ == "__main__":
    errors = variables.check_uri_required_variables()
    variables.raise_from_errors(errors)
    main()
