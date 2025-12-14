# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Datadog APM Configuration
ENV DD_SERVICE=tryonservice
ENV DD_ENV=hackathon
ENV DD_VERSION=1.0.0
ENV DD_TRACE_ENABLED=true
ENV DD_LOGS_INJECTION=true

# System deps for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg62-turbo-dev \
    zlib1g-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8080

# Healthcheck optional; FastAPI exposes /_healthz
# HEALTHCHECK CMD curl -f http://localhost:8080/_healthz || exit 1

CMD ["ddtrace-run", "uvicorn", "try_on:app", "--host", "0.0.0.0", "--port", "8080"]
