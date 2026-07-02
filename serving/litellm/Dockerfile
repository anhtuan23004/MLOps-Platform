FROM docker.litellm.ai/berriai/litellm:latest

RUN ["/app/.venv/bin/python", "-m", "ensurepip"]
RUN ["/app/.venv/bin/python", "-m", "pip", "install", "--no-cache-dir", "mlflow==3.14.0"]
