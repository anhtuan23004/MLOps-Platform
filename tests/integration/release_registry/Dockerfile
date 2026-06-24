FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir ruamel.yaml>=0.18.0

COPY llm_local /app/llm_local
COPY tests/integration/release_registry/scripts /app/tests/integration/release_registry/scripts

ENV PYTHONPATH=/app
ENV RELEASE_REGISTRY_ROOT=/data

ENTRYPOINT ["python", "-m", "llm_local.releases.cli"]
