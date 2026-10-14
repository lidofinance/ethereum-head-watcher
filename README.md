
---
# <img src="https://docs.lido.fi/img/logo.svg" alt="Lido" width="46"/> Ethereum head watcher

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Bot which watches Ethereum head and handle "events" and sends notifications through Alertmanager to Discord channel.

Currently it supports:
 - new slashing events
 - unexpected exit events
 - forking events

## Run via docker to monitor Lido validators

1. Copy `.env.example` to `.env` and fill it with your values
2. `docker-compose up -d`

## Run via local python (for development)

1. Copy `.env.example` to `.env` and fill it with your values
2. `poetry install`
3. `poetry run python -m src.main`

## Run with keys file to monitor your custom validators

> All exits will be handled as unexpected for specified keys

1. Fill `docker/validators/keys.yml` with your values
2. Set `KEYS_SOURCE=file` in `.env`

> If you want to use another path, specify it in `KEYS_FILE_PATH` env variable

## Configuration sources

Every setting below is read from the environment, and — when it exists — from a JSON file whose values take precedence.
The file is how deployments that hold credentials in a secret store deliver them: on Kubernetes the OpenBao agent writes
`/vault/secrets/config`, and the application re-reads it when it changes, so a rotated node endpoint is picked up
**without a restart**. That matters because a restart re-reads the whole validator set and every validator key — minutes
during which nothing is watched.

The file is polled by path rather than watched: the agent replaces it with an atomic rename, so a watcher attached to
the file itself would go silent after the first rotation. A reload emits one log line and increments
`ethereum_head_watcher_secrets_reloads_total{status="success"}`; a file that changed but cannot be applied leaves the
previous values in place and increments the same counter with `status="failure"`.

Only the node and Alertmanager endpoints can be swapped while the watcher runs. Any other setting in the file that
changes is logged and counted as `status="not_applied"` — it keeps its startup value until the process restarts.
`ethereum_head_watcher_secrets_file_mtime_seconds` reports the mtime of the file in force, or 0 when the configuration
came from the environment.

## Application Env variables

---
`LOG_LEVEL` - Application log level
* **Required:** false
* **Default:** info
---
`DRY_RUN` - Dry run mode. If true, application will not send any alerts
* **Required:** false
* **Default:** false
---
`ENABLED_HANDLERS` - Comma-separated list of configurable handlers enabled for this instance. Available handlers: `slashing`, `exits`, `consolidation`, `el_triggered_exit`. Chain reorganization monitoring is always enabled
* **Required:** false
* **Default:** all available handlers
---
`KEYS_SOURCE` - Keys source. If `keys_api` - application will fetch keys from Keys API, if `file` - application will fetch keys from `KEYS_FILE_PATH`
* **Required:** false
* **Default:** keys_api
---
`KEYS_FILE_PATH` - Path to file with keys
* **Required:** if `KEYS_SOURCE` is `file`
* **Default:** ./docker/validators/keys.yml
---
`CONSENSUS_CLIENT_URI` - Ethereum consensus layer comma separated API urls
* **Required:** true
---
`EXECUTION_CLIENT_URI` - Ethereum execution layer comma separated API urls
* **Required:** if `KEYS_SOURCE` is `keys_api`
---
`LIDO_LOCATOR_ADDRESS` - Lido locator contract address
* **Required:** if `KEYS_SOURCE` is `keys_api`
---
`LIDO_CONSOLIDATION_BUS_ADDRESS` - Lido ConsolidationBus contract address
* **Required:** false
---
`KEYS_API_URI` - Comma separated Keys API urls
* **Required:** if `KEYS_SOURCE` is `keys_api`
---
`ALERTMANAGER_URI` - Comma separated Alertmanager API urls
* **Required:** if `DRY_RUN` is `false`
---
`NETWORK_NAME` - Ethereum network name (mainnet or goerli)
* **Required:** false
* **Default:** mainnet
---
`ADDITIONAL_ALERTMANAGER_LABELS` - Additional labels for Alertmanager alerts for `HeadWatcherUser.*` alerts
* **Required:** false
* **Default:** {}
---
`SLOTS_RANGE` - Range of slots to check (for development purposes)
* **Required:** false
* **Default:** undefined
---
`CYCLE_SLEEP_IN_SECONDS` - Sleep time between main app task cycles
* **Required:** false
* **Default:** 1
---
`PROMETHEUS_PORT` - Prometheus port
* **Required:** false
* **Default:** 9000
---
`PROMETHEUS_PREFIX` - Prometheus metrics prefix
* **Required:** false
* **Default:** ethereum_head_watcher
---
`HEALTHCHECK_SERVER_PORT` - Healthcheck server port
* **Required:** false
* **Default:** 9010
---
`HEALTHCHECK_SERVER_HOST` - Healthcheck server bind address
* **Required:** false
* **Default:** 0.0.0.0
---
`MAX_CYCLE_LIFETIME_IN_SECONDS` - Max cycle lifetime in seconds for healthcheck
* **Required:** false
* **Default:** 3000
---
`KEYS_API_REQUEST_TIMEOUT` - Keys API request timeout in seconds
* **Required:** false
* **Default:** 180
---
`KEYS_API_REQUEST_RETRY_COUNT` - Keys API request retries
* **Required:** false
* **Default:** 3
---
`KEYS_API_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS` - Keys API request retry timeout in seconds
* **Required:** false
* **Default:** 5
---
`CL_REQUEST_TIMEOUT` - Consensus layer request timeout in seconds
* **Required:** false
* **Default:** 180
* **Note:** This variable don't change timeout for requests to blocks for keeping in sync with Ethereum head
---
`CL_REQUEST_RETRY_COUNT` - Consensus layer request retries
* **Required:** false
* **Default:** 3
* **Note:** This variable don't change retries for requests to blocks for keeping in sync with Ethereum head
---
`CL_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS` - Consensus layer request retry timeout in seconds
* **Required:** false
* **Default:** 5
* **Note:** This variable don't change timeout for requests to blocks for keeping in sync with Ethereum head
---
`EL_REQUEST_TIMEOUT` - Execution layer request timeout in seconds
* **Required:** false
* **Default:** 5
---
`ALERTMANAGER_REQUEST_TIMEOUT` - Alertmanager request timeout in seconds
* **Required:** false
* **Default:** 2
---
`ALERTMANAGER_REQUEST_RETRY_COUNT` - Alertmanager request retries
* **Required:** false
* **Default:** 2
---
`ALERTMANAGER_REQUEST_SLEEP_BEFORE_RETRY_IN_SECONDS` - Alertmanager request retry timeout in seconds
* **Required:** false
* **Default:** 1
---
`VALID_WITHDRAWAL_ADDRESSES` - A comma-separated list of addresses. Triggers a critical alert if a monitored
execution_request contains a source_address matching any of these addresses.
* **Required:** false
* **Default:** []
---
`DISABLE_UNEXPECTED_EXIT_ALERTS` - A comma-separated list of module indexes for which unexpected exit alerts are
disabled.  
* **Required:** false
* **Default:** []
---
`EVENTS_SEARCH_STEP` - Maximum length of a range for `eth_getLogs` EL method calls.
* **Required:** false
* **Default:** 10000
---
`SECRETS_FILE_PATH` - Path to a JSON file of settings that override the environment. Absent is normal — it means every
setting comes from the environment.
* **Required:** false
* **Default:** /vault/secrets/config
---
`SECRETS_POLL_INTERVAL_IN_SECONDS` - How often the secrets file is checked for a change.
* **Required:** false
* **Default:** 10

## Tests

`poetry run pytest` runs the whole suite. It has two halves, and both are kept on purpose:

- **hermetic** — `tests/test_watcher_offline.py` drives the watcher against a fake consensus node (`tests/node_fake.py`)
  with keys from a file, so a cycle, a slashing of one of our validators, an exit that is not ours and the reorg path
  are all checked with no provider and no credentials.
- **integration** — `tests/test_watcher.py` replays real mainnet slot ranges and asserts on the alert text those blocks
  produced: operator names, validator indices and wording that come from data nobody wrote for a test. It needs
  `CONSENSUS_CLIENT_URI`, `EXECUTION_CLIENT_URI` and `KEYS_API_URI`.

Both run by default. Without provider credentials, skip the second kind:

    poetry run pytest -m "not integration"

## Application metrics

You can see application metrics on `http://localhost:9000/metrics` endpoint 

The source of metrics:
 - src/metrics/prometheus/basic.py
 - src/metrics/prometheus/watcher.py

### Healthcheck endpoints

The healthcheck server serves three paths:

| Path       | Reports                                                                                                                 | Used by                          |
|------------|-------------------------------------------------------------------------------------------------------------------------|----------------------------------|
| `/pulse/`  | last cycle is newer than `MAX_CYCLE_LIFETIME_IN_SECONDS`. A GET also *records* a cycle, so it cannot be used as a probe | Docker `HEALTHCHECK`             |
| `/healthz` | this process is up and serving. Read-only                                                                               | Kubernetes liveness              |
| `/readyz`  | the watcher has finished its first cycle. Read-only, one-way                                                            | Kubernetes startup and readiness |

Neither `/healthz` nor `/readyz` reports staleness. A liveness failure would restart the pod and cost a full re-read of
the validator set and of every validator key; a readiness failure would take the pod out of Prometheus' targets, turning
a flat metric into an absent one. A stuck watcher is an alert on the metrics (`HeadBlockIsNotChanging`,
`EHWStuckBotProcessing`), not a kubelet decision.

## Release flow

To create new release:

1. Merge all changes to the `main` branch
1. Navigate to Repo => Actions
1. Run action "Prepare release" action against `main` branch
1. When action execution is finished, navigate to Repo => Pull requests
1. Find pull request named "chore(release): X.X.X" review and merge it with "Rebase and merge" (or "Squash and merge")
1. After merge release action will be triggered automatically
1. Navigate to Repo => Actions and see last actions logs for further details 
