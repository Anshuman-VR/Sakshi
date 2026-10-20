FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY adapter/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY shared /app/shared
COPY adapter /app/adapter
RUN useradd --system --uid 10001 sakshi && chown -R sakshi:sakshi /app
USER sakshi
EXPOSE 8003
CMD ["uvicorn", "adapter.main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "1"]
