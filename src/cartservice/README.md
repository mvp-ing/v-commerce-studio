# Cart Service (Python)

This is the Python implementation of the Cart Service, rewritten from the original C# version.

## Description

The Cart Service is a gRPC service that manages user shopping carts. It supports adding items to a cart, retrieving cart contents, and emptying a cart.

## Features

- Add items to user cart
- Get cart contents
- Empty cart
- Multiple storage backends:
  - **Redis** (recommended for production)
  - **In-memory** (for development/testing)
- gRPC health checking support
- OpenTelemetry tracing support
- Google Cloud Profiler support

## Storage Backends

The service automatically selects a storage backend based on environment variables:

1. **Redis**: Set `REDIS_ADDR` environment variable (e.g., `redis:6379`)
2. **In-memory**: Default when no external store is configured

Note: AlloyDB and Spanner support from the original C# implementation is not yet ported.

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
   # With in-memory storage (default)
   python cart_server.py

   # With Redis storage
   REDIS_ADDR=localhost:6379 python cart_server.py
   ```

The service will start on port 7070 by default. You can override this with the `PORT` environment variable.

## Environment Variables

- `PORT`: Server port (default: 7070)
- `REDIS_ADDR`: Redis server address (e.g., `redis:6379`)
- `DISABLE_PROFILER`: Set to disable Google Cloud Profiler
- `DISABLE_TRACING`: Set to disable OpenTelemetry tracing
- `ENABLE_TRACING`: Set to "1" to enable tracing
- `COLLECTOR_SERVICE_ADDR`: OpenTelemetry collector address (default: localhost:4317)
- `GCP_PROJECT_ID`: Google Cloud project ID for profiler

## Docker

Build and run with Docker:

```bash
# Build
docker build -t cartservice-python .

# Run with in-memory storage
docker run -p 7070:7070 cartservice-python

# Run with Redis
docker run -p 7070:7070 -e REDIS_ADDR=redis:6379 cartservice-python
```

## gRPC API

### AddItem

Adds an item to the user's cart. If the item already exists, the quantity is incremented.

### GetCart

Returns the user's cart with all items.

### EmptyCart

Clears all items from the user's cart.
