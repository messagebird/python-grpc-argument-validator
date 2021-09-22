from concurrent.futures import ThreadPoolExecutor

import grpc
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.empty_pb2 import Empty
from google.protobuf.wrappers_pb2 import BytesValue
from grpc_argument_validator import AbstractArgumentValidator
from grpc_argument_validator import validate_args
from grpc_argument_validator import ValidationContext
from grpc_argument_validator import ValidationResult
from tests.route_guide_protos.route_guide_pb2 import Area
from tests.route_guide_protos.route_guide_pb2 import Path
from tests.route_guide_protos.route_guide_pb2 import PlanetValue
from tests.route_guide_protos.route_guide_pb2 import Route
from tests.route_guide_protos.route_guide_pb2_grpc import add_RouteServiceServicer_to_server
from tests.route_guide_protos.route_guide_pb2_grpc import RouteServiceServicer
from tests.route_guide_protos.route_guide_pb2_grpc import RouteServiceStub


class PathValidator(AbstractArgumentValidator):
    def check(
        self, name: str, value: Path, field_descriptor: FieldDescriptor, validation_context: ValidationContext
    ) -> ValidationResult:
        if len(value.points) > 5:
            return ValidationResult(valid=True)
        return ValidationResult(False, f"path for '{name}' should be at least five points long")


class RouteServiceImpl(RouteServiceServicer):
    @validate_args(validators={"path": PathValidator()}, non_default=["planet.value"])
    def CreateRoute(self, request: Route, context: grpc.ServicerContext):
        return Empty()

    @validate_args(uuids=["uuid.value"])
    def CreateArea(self, request: Area, context: grpc.ServicerContext):
        return Empty()


if __name__ == "__main__":
    route_service = RouteServiceImpl()
    grpc_server = grpc.server(ThreadPoolExecutor(max_workers=20))
    add_RouteServiceServicer_to_server(route_service, grpc_server)
    grpc_server.add_insecure_port("[::]:50051")
    grpc_server.start()

    with grpc.insecure_channel("127.0.0.1:50051") as c:
        route_client = RouteServiceStub(channel=c)
        try:
            route_client.CreateArea(Area(uuid=BytesValue(value="not a uuid".encode())))
        except grpc.RpcError as e:
            if isinstance(e, grpc.Call):
                print(e.details())

        try:
            route_client.CreateRoute(Route(planet=PlanetValue()))
        except grpc.RpcError as e:
            if isinstance(e, grpc.Call):
                print(e.details())
