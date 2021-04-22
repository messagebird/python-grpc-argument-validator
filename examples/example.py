from unittest.mock import MagicMock

import grpc
from google.protobuf.wrappers_pb2 import BoolValue
from grpc_argument_validator import AbstractArgumentValidator
from grpc_argument_validator import validate_args
from tests.route_guide_protos.route_guide_pb2 import Path
from tests.route_guide_protos.route_guide_pb2 import Route


class PathValidator(AbstractArgumentValidator):
    def is_valid(self, value: Path, field_descriptor) -> bool:
        return len(value.points) > 5

    def invalid_message(self, name: str) -> str:
        return f"path for '{name}' should be at least five points long"


# Some class that implements a gRPC servicer
class RouteChecker:
    @validate_args(
        non_empty=["tags", "tags[]", "path.points"], validators={"path": PathValidator()},
    )
    def Check(self, request: Route, context: grpc.ServicerContext):
        return BoolValue(value=True)


if __name__ == "__main__":
    checker = RouteChecker()

    context = MagicMock()
    context.abort.side_effect = Exception("invalid arg")

    # this is not good
    checker.Check(Route(path=Path(points=[])), context=context)
