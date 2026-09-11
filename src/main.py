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
from src.metrics.prometheus.basic import (
    BUILD_INFO,
    SECRETS_FILE_MTIME,
    SECRETS_RELOADS,
    Status,
)
from src.metrics.prometheus.rpc import LAYER_CL, LAYER_EL, set_chain_id
from src.secrets import SecretsWatcher, read_secrets_file_mtime
from src.utils.build import get_build_info, user_agent
from src.utils.urls import register_credential_urls
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


# The settings a rotation can be applied to while the watcher runs. Anything else in the file is
# read at startup and only at startup.
LIVE_APPLIED_SETTINGS = ('CONSENSUS_CLIENT_URI', 'EXECUTION_CLIENT_URI', 'KEYS_API_URI', 'ALERTMANAGER_URI')


def el_request_headers() -> dict[str, str]:
    """web3 drops its whole default header set the moment `headers` is given, so Content-Type is repeated here."""
    return {'Content-Type': 'application/json', 'User-Agent': user_agent()}


def resolve_chain_ids(watcher: Watcher) -> None:
    """
    Fill in the `chain_id` label the RPC metrics carry, once.

    A layer that will not answer keeps reporting `unknown` rather than holding up the start.
    """
    try:
        set_chain_id(LAYER_CL, watcher.consensus.get_deposit_chain_id())
    except Exception as error:  # pylint: disable=broad-except
        logger.warning({'msg': 'Can not resolve the consensus layer chain id', 'exception': str(error)})

    if watcher.execution is None:
        return
    try:
        provider: FallbackProviderModule = watcher.execution.provider  # type: ignore[assignment]
        set_chain_id(LAYER_EL, provider.check_providers_consistency())
    except Exception as error:  # pylint: disable=broad-except
        logger.warning({'msg': 'Can not resolve the execution layer chain id', 'exception': str(error)})


def unapplied_changes(values: dict[str, str], in_force: dict[str, str]) -> list[str]:
    """
    Keys the file changed that a live apply cannot reach.

    Without this a rotation of, say, a locator address is indistinguishable from no rotation at all: the file is read,
    the mtime is remembered, and the setting keeps its startup value forever.
    """
    return sorted(
        key for key, value in values.items() if key not in LIVE_APPLIED_SETTINGS and in_force.get(key) != value
    )


def apply_rotated_secrets(values: dict[str, str], watcher: Watcher, in_force: dict[str, str]) -> list[str]:
    """
    Swap in endpoints from a rotated secrets file, without a restart. Returns what changed.

    Restarting would re-read the whole validator set and key set, so the clients are re-pointed instead: each keeps its
    endpoints in a list it walks per request. The execution layer needs a new provider, which leaves the Web3 instance,
    its middlewares and its contracts in place.
    """
    changed = []

    # Before anything is applied or logged: the rotated-in key has to be redactable from this point on, and the
    # rotated-out one stays registered because a stale exception text still carries it.
    register_credential_urls(*(_split(values.get(name)) for name in LIVE_APPLIED_SETTINGS))

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
        # `Web3.provider` is read-only in web3 6.x; the manager's is the settable one. The middlewares (metrics, cache)
        # live on the manager too, so they survive the swap, and the contracts hold a reference to the Web3 instance
        # rather than to the provider.
        watcher.execution.manager.provider = FallbackProviderModule(
            execution_uri, request_kwargs={'timeout': variables.EL_REQUEST_TIMEOUT, 'headers': el_request_headers()}
        )
        variables.EXECUTION_CLIENT_URI = execution_uri
        changed.append('EXECUTION_CLIENT_URI')

    if changed:
        logger.info({'msg': f'Applied rotated secrets: {", ".join(changed)}'})
        SECRETS_RELOADS.labels(Status.SUCCESS.value).inc()

    if not_applied := unapplied_changes(values, in_force):
        logger.warning(
            {
                'msg': f'Rotated settings a restart is needed for: {", ".join(not_applied)}',
                'applied_live': ', '.join(LIVE_APPLIED_SETTINGS),
            }
        )
        SECRETS_RELOADS.labels(Status.NOT_APPLIED.value).inc()

    in_force.clear()
    in_force.update(values)
    SECRETS_FILE_MTIME.set((read_secrets_file_mtime(variables.SECRETS_FILE_PATH) or 0) / 1e9)
    return changed


def _split(value: str | None) -> list[str]:
    if not value:
        return []
    return [entry for entry in (part.strip() for part in value.split(',')) if entry]


def install_signal_handlers():
    """
    Make SIGTERM and SIGHUP stop the watcher the way Ctrl-C does.

    Python installs a disposition for SIGINT only, and as PID 1 the process gets no default action for the others, so
    without this they are dropped and the container is killed instead of stopping. Routed onto SIGINT because the loop
    already unwinds on KeyboardInterrupt.
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

    logger.info({'msg': 'Effective configuration', 'config': variables.effective_config()})

    logger.info({'msg': f'Start healthcheck server for Docker container on port {variables.HEALTHCHECK_SERVER_PORT}'})
    start_pulse_server()

    logger.info({'msg': f'Start http server with prometheus metrics on port {variables.PROMETHEUS_PORT}'})
    start_http_server(variables.PROMETHEUS_PORT)

    if variables.KEYS_SOURCE == SourceType.KEYS_API.value:
        keys_source = KeysApiSource()
        web3 = Web3(
            FallbackProviderModule(
                variables.EXECUTION_CLIENT_URI,
                request_kwargs={'timeout': variables.EL_REQUEST_TIMEOUT, 'headers': el_request_headers()},
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
    resolve_chain_ids(watcher)

    in_force = variables.secrets_in_force()
    SECRETS_FILE_MTIME.set((read_secrets_file_mtime(variables.SECRETS_FILE_PATH) or 0) / 1e9)

    SecretsWatcher(
        variables.SECRETS_FILE_PATH,
        on_change=lambda values: apply_rotated_secrets(values, watcher, in_force),
        interval=variables.SECRETS_POLL_INTERVAL_IN_SECONDS,
        on_error=lambda: SECRETS_RELOADS.labels(Status.FAILURE.value).inc(),
    ).start()

    install_signal_handlers()

    try:
        watcher.run()
    except KeyboardInterrupt:
        # One line, so a shutdown on purpose is distinguishable from being killed.
        logger.info({'msg': 'Shutting down on a termination signal'})


if __name__ == "__main__":
    errors = variables.check_uri_required_variables()
    variables.raise_from_errors(errors)
    main()
