#!/usr/bin/env bash

python -m grpc_tools.protoc -I./protos  -I/usr/local/include --python_out=. --grpc_python_out=. --mypy_out=. ./protos/route_guide.proto
