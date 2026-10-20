# ==============================================================================
# SAKSHI LENDER APPLIANCE DOCKERFILE
# Multi-stage build: compiles React frontend, then bundles FastAPI verifier node,
# SQLite append-only ledger, Mock LMS disbursal gate, and static SPA assets.
# ==============================================================================

FROM node:20-alpine AS frontend-build
WORKDIR /workspace/dashboard
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY dashboard/ ./
RUN npm run build

FROM python:3.11-slim AS lender-runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libstdc++6 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY node/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY shared /app/shared
COPY node /app/node
COPY mock_lms /app/mock_lms
COPY --from=frontend-build /workspace/dashboard/dist /app/dashboard/dist

RUN mkdir -p /app/data /app/circuits/artifacts

EXPOSE 8000
CMD ["uvicorn", "node.main:app", "--host", "0.0.0.0", "--port", "8000"]
