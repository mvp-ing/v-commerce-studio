FROM --platform=$BUILDPLATFORM node:20.18.1-alpine@sha256:24fb6aa7020d9a20b00d6da6d1714187c45ed00d1eb4adb01395843c338b9372 AS builder

# Some packages (e.g. @google-cloud/profiler, dd-trace) require additional
# deps for post-install scripts
RUN apk add --update --no-cache \
    python3 \
    make \
    g++

WORKDIR /usr/src/app

COPY package*.json ./

RUN npm install --only=production

FROM alpine:3.20.3@sha256:1e42bbe2508154c9126d48c2b8a75420c3544343bf86fd041fb7527e017a4b4a

RUN apk add --no-cache nodejs

WORKDIR /usr/src/app

COPY --from=builder /usr/src/app/node_modules ./node_modules

COPY . .

EXPOSE 7000

# Datadog APM environment variables (configured via K8s manifest or docker-compose)
ENV DD_SERVICE=currencyservice
ENV DD_ENV=production
ENV DD_LOGS_INJECTION=true
ENV DD_RUNTIME_METRICS_ENABLED=true
ENV DD_PROFILING_ENABLED=true

# Use --require dd-trace/init to ensure tracer is loaded first
ENTRYPOINT [ "node", "--require", "dd-trace/init", "server.js" ]
