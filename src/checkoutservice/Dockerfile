 

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
      (echo "Attempt $i failed, retrying in 3s..." && sleep 3); \
    done

COPY . .

# Skaffold passes in debug-oriented compiler flags
ARG SKAFFOLD_GO_GCFLAGS
RUN GOOS=${TARGETOS} GOARCH=${TARGETARCH} CGO_ENABLED=0 go build -gcflags="${SKAFFOLD_GO_GCFLAGS}" -o /checkoutservice .

FROM scratch

WORKDIR /src
COPY --from=builder /checkoutservice /src/checkoutservice

# Definition of this variable is used by 'skaffold debug' to identify a golang binary.
# Default behavior - a failure prints a stack trace for the current goroutine.
# See https://golang.org/pkg/runtime/
ENV GOTRACEBACK=single

# Datadog APM Configuration (for OTLP trace tagging)
ENV DD_SERVICE=checkoutservice
ENV DD_ENV=hackathon
ENV DD_VERSION=1.0.0

# OpenTelemetry Resource Attributes (used by OTLP exporter)
ENV OTEL_SERVICE_NAME=checkoutservice
ENV OTEL_RESOURCE_ATTRIBUTES=service.name=checkoutservice,service.version=1.0.0,deployment.environment=hackathon

EXPOSE 5050
ENTRYPOINT ["/src/checkoutservice"]
