# Dev 3 owns this integration Dockerfile because it builds the React assets and
# packages them with Dev 2's FastAPI service. Dev 2 owns node/main.py and its
# requirements.txt; coordinate before changing this file on another branch.
FROM node:20-alpine AS frontend-build
WORKDIR /workspace/dashboard
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY dashboard/ ./
RUN npm run build

FROM python:3.11-slim AS lender-runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY node/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY node/ ./node/
COPY mock_lms/ ./mock_lms/
COPY --from=frontend-build /workspace/dashboard/dist ./dashboard/dist
EXPOSE 8000
CMD ["uvicorn", "node.main:app", "--host", "0.0.0.0", "--port", "8000"]
