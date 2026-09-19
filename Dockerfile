# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS builder

ARG POETRY_VERSION=2.2.1

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1

WORKDIR /app

RUN pip install "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-ansi


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}" \
    PORT=8000 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app . .
COPY --chown=app:app docker/entrypoint.sh /usr/local/bin/entrypoint

RUN chmod 0555 /usr/local/bin/entrypoint

USER 10001:10001

EXPOSE 8000

ENTRYPOINT ["entrypoint"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
