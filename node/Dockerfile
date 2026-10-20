FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
COPY node/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY shared /app/shared
COPY node /app/node
RUN mkdir -p /app/data && useradd --system --uid 10001 sakshi && chown -R sakshi:sakshi /app
USER sakshi
EXPOSE 8000
CMD ["uvicorn", "node.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
