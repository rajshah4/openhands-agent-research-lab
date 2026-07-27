FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY examples ./examples
COPY experiments/agent-canvas-kubernetes/controller/controller_tick.py \
  ./controller_tick.py

RUN pip install --no-cache-dir .

USER 65532:65532
ENTRYPOINT ["python", "/app/controller_tick.py"]
