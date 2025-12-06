#!/bin/bash
 

set -e

# Generate Python protobuf files
python -m grpc_tools.protoc \
    -I/protos \
    -I/protos/grpc/health/v1 \
    --python_out=. \
    --grpc_python_out=. \
    /protos/demo.proto \
    /protos/grpc/health/v1/health.proto

echo "Protobuf generation completed successfully" 