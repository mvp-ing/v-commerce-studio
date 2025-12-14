 

FROM --platform=$BUILDPLATFORM golang:1.23.4-alpine@sha256:c23339199a08b0e12032856908589a6d41a0dab141b8b3b21f156fc571a3f1d3 AS builder
ARG TARGETOS
ARG TARGETARCH
WORKDIR /src

# restore dependencies
COPY go.mod go.sum ./
# Use multiple proxies with fallback to direct, and retry on failure
ENV GOPROXY=https://proxy.golang.org,https://goproxy.io,direct
RUN for i in 1 2 3 4 5; do \
      go mod download && break || \
      (echo "Attempt $i failed, retrying in 5s..." && sleep 3); \
    done
COPY . .

# Skaffold passes in debug-oriented compiler flags
ARG SKAFFOLD_GO_GCFLAGS
RUN GOOS=${TARGETOS} GOARCH=${TARGETARCH} CGO_ENABLED=0 go build -gcflags="${SKAFFOLD_GO_GCFLAGS}" -o /go/bin/frontend .

FROM scratch
WORKDIR /src
COPY --from=builder /go/bin/frontend /src/server
COPY ./templates ./templates
COPY ./static ./static

# Definition of this variable is used by 'skaffold debug' to identify a golang binary.
# Default behavior - a failure prints a stack trace for the current goroutine.
# See https://golang.org/pkg/runtime/
ENV GOTRACEBACK=single

# Datadog APM Configuration (for OTLP trace tagging)
ENV DD_SERVICE=frontend
ENV DD_ENV=hackathon
ENV DD_VERSION=1.0.0
ENV DD_SITE=us5.datadoghq.com

# Datadog RUM Configuration (set via K8s secrets or deployment)
# DD_RUM_CLIENT_TOKEN and DD_RUM_APPLICATION_ID must be set at runtime

# OpenTelemetry Resource Attributes (used by OTLP exporter)
ENV OTEL_SERVICE_NAME=frontend
ENV OTEL_RESOURCE_ATTRIBUTES=service.name=frontend,service.version=1.0.0,deployment.environment=hackathon

EXPOSE 8080
ENTRYPOINT ["/src/server"]
