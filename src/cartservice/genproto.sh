#!/bin/bash -eu
#
# Generate Python gRPC code from proto files

python -m grpc_tools.protoc -I../../protos --python_out=. --grpc_python_out=. ../../protos/demo.proto
