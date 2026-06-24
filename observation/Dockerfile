FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir requests==2.32.3 pandas==2.2.3 matplotlib==3.9.3

COPY scripts/ /app/scripts/

ENTRYPOINT ["python", "/app/scripts/collect_metrics.py"]
