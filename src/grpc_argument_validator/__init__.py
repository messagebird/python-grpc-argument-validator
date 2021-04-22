"""
Provides decorator to validate arguments in protobuf messages.

Example:
```
from grpc_argument_validator import validate_args
from grpc_argument_validator import AbstractArgumentValidator

class PathValidator(AbstractArgumentValidator):
    def is_valid(self, value: Path, field_descriptor) -> bool:
        return len(value.points) > 5

    def invalid_message(self, name: str) -> str:
        return f"path for '{name}' should be at least five points long"

class RouteChecker(RouteCheckerServicer):
    @validate_args(
        non_empty=["tags", "tags[]", "path.points"],
        validators={"path": PathValidator()},
    )
    def Check(self, request: Route, context: grpc.ServicerContext):
        return BoolValue(value=True)
```
"""
from .argument_validators import AbstractArgumentValidator
from .argument_validators import RegexpValidator
from .validate_args_decorator import validate_args
