
FROM python:3.12-alpine

RUN apk add curl

RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/etc/poetry python3 -

ENV PATH="$PATH:/etc/poetry/bin"

COPY pyproject.toml poetry.lock README.md ./

RUN poetry config virtualenvs.path pypoetry

RUN poetry install --no-root --no-interaction --no-ansi

