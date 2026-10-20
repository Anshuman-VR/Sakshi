# ==============================================================================
# SAKSHI LSP PRIVATE PROVER DOCKERFILE
# Contains: ONNX scorecard model, EZKL circuit prover, outbox worker,
# policy signing tools, and private FastAPI prover sidecar.
# ==============================================================================

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libstdc++6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY sidecar/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY shared /app/shared
COPY model /app/model
COPY circuits /app/circuits
COPY policy /app/policy
COPY sidecar /app/sidecar

RUN mkdir -p /app/data /app/circuits/artifacts

EXPOSE 8001
CMD ["uvicorn", "sidecar.main:app", "--host", "0.0.0.0", "--port", "8001"]
