"""
Provides decorator to validate arguments in protobuf messages.

Example:
```
from google.protobuf.descriptor import FieldDescriptor
from grpc_argument_validator import validate_args
from grpc_argument_validator import AbstractArgumentValidator, ValidationResult

class PathValidator(AbstractArgumentValidator):

    def check(self, name: str, value: Path, field_descriptor: FieldDescriptor) -> ValidationResult:
        if len(value.points) > 5:
            return ValidationResult(valid=True)
        return ValidationResult(False, f"path for '{name}' should be at least five points long")

class RouteService(RouteCheckerServicer):
    @validate_args(
        non_empty=["tags", "tags[]", "path.points"],
        validators={"path": PathValidator()},
    )
    def Create(self, request: Route, context: grpc.ServicerContext):
        return BoolValue(value=True)
```
"""
from .argument_validators import AbstractArgumentValidator
from .argument_validators import RegexpValidator
from .argument_validators import ValidationResult
from .validate_args_decorator import validate_args
