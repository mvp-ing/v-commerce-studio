# Cart Service - Python Implementation

FROM python:3.12-slim AS base

FROM base AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base

# Enable unbuffered logging
ENV PYTHONUNBUFFERED=1
# Disable Profiler for local development (no GCP credentials)
ENV ENABLE_PROFILER=0

# Datadog APM Configuration
ENV DD_SERVICE=cartservice
ENV DD_ENV=hackathon
ENV DD_VERSION=1.0.0
ENV DD_TRACE_ENABLED=true
ENV DD_LOGS_INJECTION=true

WORKDIR /cartservice

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/ /usr/local/lib/python3.12/
# Copy executables (including ddtrace-run)
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application files
COPY . .

EXPOSE 7070
ENTRYPOINT ["ddtrace-run", "python", "cart_server.py"]
