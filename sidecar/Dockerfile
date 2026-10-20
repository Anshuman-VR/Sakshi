# Dev 3 owns the top-level container integration file; Dev 1 owns the sidecar
# application modules and requirements.txt. Coordinate before changing this
# file on another branch to keep the two-container topology conflict-free.
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY sidecar/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY sidecar/ ./sidecar/
COPY model/ ./model/
COPY shared/ ./shared/
RUN mkdir -p /app/data /app/circuits/artifacts
EXPOSE 8001
CMD ["uvicorn", "sidecar.main:app", "--host", "0.0.0.0", "--port", "8001"]
