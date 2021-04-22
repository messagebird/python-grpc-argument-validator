from grpc_tools import protoc

protoc.main(("", "-I./protos", "-I/usr/local/include", "--python_out=.", "./protos/route_guide.proto"))
