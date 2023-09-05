
---
# <img src="https://docs.lido.fi/img/logo.svg" alt="Lido" width="46"/> Ethereum head watcher

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Bot which watches Ethereum head and handle "events" and sends notifications through Alertmanager to Discord channel.

Currently it supports:
 - new slashing events
 - unexpected exit events
 - forking events

## Run via docker

1. Copy `.env.example` to `.env` and fill it with your values
2. `docker-compose up -d`

## Run via local python (for development)

1. Copy `.env.example` to `.env` and fill it with your values
2. `poetry install`
3. `poetry run python -m src.main`

## Release flow

To create new release:

1. Merge all changes to the `main` branch
1. Navigate to Repo => Actions
1. Run action "Prepare release" action against `main` branch
1. When action execution is finished, navigate to Repo => Pull requests
1. Find pull request named "chore(release): X.X.X" review and merge it with "Rebase and merge" (or "Squash and merge")
1. After merge release action will be triggered automatically
1. Navigate to Repo => Actions and see last actions logs for further details 