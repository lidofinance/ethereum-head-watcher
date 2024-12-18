
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

## Application metrics

You can see application metrics on `http://localhost:9000/metrics` endpoint 

The source of metrics:
 - src/metrics/prometheus/basic.py
 - src/metrics/prometheus/watcher.py

## Release flow

To create new release:

1. Merge all changes to the `main` branch
1. Navigate to Repo => Actions
1. Run action "Prepare release" action against `main` branch
1. When action execution is finished, navigate to Repo => Pull requests
1. Find pull request named "chore(release): X.X.X" review and merge it with "Rebase and merge" (or "Squash and merge")
1. After merge release action will be triggered automatically
1. Navigate to Repo => Actions and see last actions logs for further details 