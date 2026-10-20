FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY sidecar/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY shared /app/shared
COPY sidecar /app/sidecar
COPY circuits /app/circuits
COPY policy /app/policy
RUN mkdir -p /app/data /app/circuits/artifacts && useradd --create-home --uid 10001 sakshi && chown -R sakshi:sakshi /app
USER sakshi
EXPOSE 8001
CMD ["uvicorn", "sidecar.main:app", "--host", "0.0.0.0", "--port", "8001"]
