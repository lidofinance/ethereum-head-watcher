FROM python:3.11.3-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends -qq \
    gcc=4:10.2.1-1 \
    libffi-dev=3.3-6 \
    g++=4:10.2.1-1 \
    git=1:2.30.2-1+deb11u2 \
    curl=7.74.0-1.3+deb11u14 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    VENV_PATH="/.venv"

ENV PATH="$VENV_PATH/bin:$PATH"

FROM base AS builder

ENV POETRY_VERSION=1.3.2
RUN pip install --no-cache-dir poetry==$POETRY_VERSION

WORKDIR /
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root


FROM base AS production

COPY --from=builder $VENV_PATH $VENV_PATH
WORKDIR /app
COPY . .

RUN apt-get clean && find /var/lib/apt/lists/ -type f -delete && chown -R www-data /app/

ENV PROMETHEUS_PORT=9000
ENV HEALTHCHECK_SERVER_POR=9010

EXPOSE $PROMETHEUS_PORT
USER www-data

HEALTHCHECK --interval=10s --timeout=3s \
    CMD curl -f http://localhost:$HEALTHCHECK_SERVER_PORT/pulse/ || exit 1

WORKDIR /app/

ENTRYPOINT ["python3", "-m", "src.main"]
