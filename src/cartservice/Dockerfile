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

WORKDIR /cartservice

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/ /usr/local/lib/python3.12/

# Copy application files
COPY . .

EXPOSE 7070
ENTRYPOINT ["python", "cart_server.py"]
