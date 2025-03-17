FROM python:3.9-slim

WORKDIR /app
COPY shared_models /app/shared_models/shared_models
COPY pyproject.toml /app/shared_models/pyproject.toml
RUN pip install --no-cache-dir /app/shared_models