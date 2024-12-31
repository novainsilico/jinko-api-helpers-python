FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    curl \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/etc/poetry python3 -
ENV PATH="$PATH:/etc/poetry/bin"

COPY pyproject.toml poetry.lock README.md ./

RUN poetry config virtualenvs.path pypoetry

RUN poetry install --no-root --no-interaction --no-ansi
