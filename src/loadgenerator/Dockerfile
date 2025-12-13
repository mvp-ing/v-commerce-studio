FROM python:3.12-slim AS base

FROM base AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --prefix="/install" --no-cache-dir -r requirements.txt

FROM base

WORKDIR /loadgen

COPY --from=builder /install /usr/local

# Add application code.
COPY locustfile.py .

# enable gevent support in debugger
ENV GEVENT_SUPPORT=True

ENTRYPOINT tail -f /dev/null
