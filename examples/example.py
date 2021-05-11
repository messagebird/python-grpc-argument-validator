from unittest.mock import MagicMock

import grpc
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.wrappers_pb2 import BoolValue
from grpc_argument_validator import AbstractArgumentValidator
from grpc_argument_validator import validate_args
from grpc_argument_validator import ValidationResult
from tests.route_guide_protos.route_guide_pb2 import Path
from tests.route_guide_protos.route_guide_pb2 import Route


class PathValidator(AbstractArgumentValidator):
    def check(self, name: str, value: Path, field_descriptor: FieldDescriptor) -> ValidationResult:
        if len(value.points) > 5:
            return ValidationResult(valid=True)
        return ValidationResult(False, f"path for '{name}' should be at least five points long")


class RouteService:
    @validate_args(
        non_empty=["tags", "tags[]", "path.points"], validators={"path": PathValidator()},
    )
    def Create(self, request: Route, context: grpc.ServicerContext):
        return BoolValue(value=True)


if __name__ == "__main__":
    checker = RouteService()

    context = MagicMock()
    context.abort.side_effect = Exception("invalid arg")

    # this is not good
    checker.Create(Route(path=Path(points=[])), context=context)
