FROM python:3.12-slim AS base

FROM base AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ \
    && rm -rf /var/lib/apt/lists/*

# get packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base
# Enable unbuffered logging
ENV PYTHONUNBUFFERED=1
# Disable Profiler for local development (no GCP credentials)
ENV ENABLE_PROFILER=0

# Datadog APM Configuration
ENV DD_SERVICE=emailservice
ENV DD_ENV=hackathon
ENV DD_VERSION=1.0.0
ENV DD_TRACE_ENABLED=true
ENV DD_LOGS_INJECTION=true

WORKDIR /email_server

# Grab packages from builder
COPY --from=builder /usr/local/lib/python3.12/ /usr/local/lib/python3.12/
# Copy executables (including ddtrace-run)
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Add the application
COPY . .

EXPOSE 8080
ENTRYPOINT [ "ddtrace-run", "python", "email_server.py" ]
