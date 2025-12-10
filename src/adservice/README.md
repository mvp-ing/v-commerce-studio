# Ad Service (Python)

This is the Python implementation of the Ad Service, rewritten from the original Java version.

## Description

The Ad Service is a gRPC service that serves advertisements based on context keywords. It maintains a catalog of ads organized by categories (clothing, accessories, footwear, hair, decor, kitchen) and returns relevant ads based on the requested context.

## Features

- Returns ads based on context keywords/categories
- Falls back to random ads when no matching context is found
- gRPC health checking support
- OpenTelemetry tracing support
- Google Cloud Profiler support

## Running Locally

1. Generate the protobuf code:

   ```bash
   ./genproto.sh
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the service:
   ```bash
   python ad_server.py
   ```

The service will start on port 9555 by default. You can override this with the `PORT` environment variable.

## Environment Variables

- `PORT`: Server port (default: 9555)
- `DISABLE_PROFILER`: Set to disable Google Cloud Profiler
- `DISABLE_TRACING`: Set to disable OpenTelemetry tracing
- `ENABLE_TRACING`: Set to "1" to enable tracing
- `COLLECTOR_SERVICE_ADDR`: OpenTelemetry collector address (default: localhost:4317)
- `GCP_PROJECT_ID`: Google Cloud project ID for profiler

## Docker

Build and run with Docker:

```bash
docker build -t adservice-python .
docker run -p 9555:9555 adservice-python
```
