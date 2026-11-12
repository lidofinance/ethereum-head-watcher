FROM python:3.11.18-slim-trixie AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=1.3.2 \
    VENV_PATH="/.venv"

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

WORKDIR /
# Manifests before the source, so a code change does not re-resolve the dependencies.
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root


FROM python:3.11.18-slim-trixie AS production

# The k8s build passes these as build args; the legacy pipeline passes none and rewrites
# build-info.json in the checkout instead, so the file is only overwritten when they are set.
ARG BUILD_VERSION
ARG BUILD_BRANCH
ARG BUILD_COMMIT

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PROMETHEUS_PORT=9000 \
    HEALTHCHECK_SERVER_PORT=9010 \
    VENV_PATH="/.venv"

ENV PATH="$VENV_PATH/bin:$PATH"

COPY --from=builder $VENV_PATH $VENV_PATH

WORKDIR /app
COPY . .

RUN if [ -n "$BUILD_COMMIT" ]; then \
      printf '{"version": "%s", "branch": "%s", "commit": "%s"}\n' \
        "$BUILD_VERSION" "$BUILD_BRANCH" "$BUILD_COMMIT" > build-info.json; \
    fi \
 && chown -R www-data /app/

EXPOSE $PROMETHEUS_PORT
USER www-data

HEALTHCHECK --interval=10s --timeout=3s \
  CMD sh -c 'python3 -c "import urllib.request; exit(0) if urllib.request.urlopen(f\"http://localhost:${HEALTHCHECK_SERVER_PORT}/pulse/\").status == 200 else exit(1)"'

ENTRYPOINT ["python3", "-m", "src.main"]
