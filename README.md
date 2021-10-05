[![codecov](https://codecov.io/gh/messagebird/python-grpc-argument-validator/branch/master/graph/badge.svg)](https://codecov.io/gh/messagebird/python-grpc-argument-validator)
[![PyPI](https://img.shields.io/pypi/v/grpc-argument-validator.svg?color=blue)](https://pypi.org/project/python-grpc-argument-validator/)
[![License](https://img.shields.io/github/license/messagebird/python-grpc-argument-validator)](https://opensource.org/licenses/BSD-3-Clause)
[![Docs](https://img.shields.io/static/v1?label=Docs&message=Github%20Pages&color=blue)](https://messagebird.github.io/python-grpc-argument-validator/grpc_argument_validator/)
[![tests](https://github.com/messagebird/python-grpc-argument-validator/workflows/Tests/badge.svg)](https://github.com/messagebird/python-grpc-argument-validator/actions?workflow=tests)


# gRPC argument validator
gRPC argument validator is a library that provides decorators to automatically validate arguments in requests to rpc methods.

<!-- GETTING STARTED -->
## Getting Started

This is an example of how you may give instructions on setting up your project locally.
To get a local copy up and running follow these simple example steps.

### Installation

#### From PyPI
```sh
pip install grpc-argument-validator
```

#### From source

- Install [`poetry`](https://python-poetry.org/docs/)

- Clone repo

```sh
git clone https://github.com/messagebird/python-grpc-argument-validator.git
```

- Install packages

```sh
cd python-grpc-argument-validator && poetry install
```

- Run the tests

```sh
cd src/tests
poetry run python -m unittest
```



<!-- USAGE EXAMPLES -->
## Quick Example
```python
from google.protobuf.descriptor import FieldDescriptor
from grpc_argument_validator import validate_args
from grpc_argument_validator import AbstractArgumentValidator, ValidationResult, ValidationContext

class PathValidator(AbstractArgumentValidator):

    def check(self, name: str, value: Path, field_descriptor: FieldDescriptor, validation_context: ValidationContext) -> ValidationResult:
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

<!-- DOCUMENTATION -->
## Documentation

We host the full API reference on [GitHub pages](https://messagebird.github.io/python-grpc-argument-validator/grpc_argument_validator/).

### Argument field syntax
To specify which argument field should be validated, `grpc-argument-validator` expects strings that match the field names
as defined in the protobufs. To access nested fields, use a dot (`.`).

Consider the following protobuf definition:
```protobuf
syntax = "proto3";

package routeguide;

import "google/protobuf/empty.proto";
import "google/protobuf/wrappers.proto";

message Point {
  int32 x = 1;
  int32 y = 2;
  google.protobuf.StringValue name = 3;
}

message Rectangle {
  Point lo = 1;
  Point hi = 2;
}

message Area {
  Rectangle rectangle = 1;
  google.protobuf.StringValue message = 2;
  google.protobuf.BytesValue uuid = 3;
}

message Path {
  repeated Point points = 1;
}

enum Planet {
  PLANET_INVALID = 0;
  PLANET_EARTH = 1;
  PLANET_MARS = 2;
}

message PlanetValue {
  Planet value = 1;
}

message Route {
  Path path = 1;
  google.protobuf.StringValue name = 2;
  PlanetValue planet = 3;
  repeated string tags = 4;
}

service RouteService {
  rpc CreateRoute(Route) returns (google.protobuf.Empty);
  rpc CreateArea(Area) returns (google.protobuf.Empty);
}
```
- If you want to validate the field `planet` in a `Route` proto, simply specify `"planet"` or equivalently `".planet"`.
- If you want to validate the `value` field within the `name` field of a `Route` proto, use `"name.value"` or
equivalently `".name.value"`.
- If you want to apply a check to each element of a `repeated` field, append `[]` to the name of the field.
- If you want to apply a check to the 'root proto' (i.e. the request itself), use `"."` as the field path.

To clarify this, let's say that we know that both `planet` and `name.value` should have non-default values. We can then
decorate a method in our gRPC server as follows:

```python
import grpc
from google.protobuf.empty_pb2 import Empty
from grpc_argument_validator import validate_args
from tests.route_guide_protos.route_guide_pb2 import Route
from tests.route_guide_protos.route_guide_pb2_grpc import RouteServiceServicer


class RouteServiceImpl(RouteServiceServicer):
    @validate_args(non_empty=["planet", "name.value"])
    def CreateRoute(self, request: Route, context: grpc.ServicerContext):
        return Empty()
```

Calling the service with a default value for either `planet` or `name.value` will yield an `INVALID_ARGUMENT` status code
with further details on which fields violate the validation.

### Validators
There are two kinds of validators you might consider:

- There are predefined validators which we will cover shortly
- Another option is to define your own validators

In the examples below, we have used exactly one validator + field path per `validate_args` decorator for clarity.
Fortunately, our API allows you to use multiple validators and fields!

#### 'Has' validator
The simplest of all predefined validators is the 'has' validator which simply checks whether a `HasField` evaluates to
`True`. This of course works in combination with nested fields.

In the example below, calling the `Create` endpoint without setting `Route.name` would result in an `INVALID_ARGUMENT`
status.
```python

class RouteServiceImpl(RouteServiceServicer):
    @validate_args(has=["name"])
    def CreateRoute(self, request: Route, context: grpc.ServicerContext):
        return Empty()
```
Run this on a local machine and make a request with an invalid argument:
```python
with grpc.insecure_channel("127.0.0.1:50051") as c:
    route_client = RouteServiceStub(channel=c)
    try:
        route_client.CreateRoute(Route(tags=["tag"]))
    except grpc.RpcError as e:
        if isinstance(e, grpc.Call):
            print(e.details())
```
The following will be printed:
`must have 'name'`

#### UUID validator
Another common use-case is the validation of UUIDs. You can enlist the fields that should be UUIDs (represented as
16 bytes) with the `uuids` argument:
```python
class RouteServiceImpl(RouteServiceServicer):
    @validate_args(uuids=["uuid.value"])
    def CreateArea(self, request: Area, context: grpc.ServicerContext):
        return Empty()
```
The client side might violate the UUID requirement as follows:
```python
with grpc.insecure_channel("127.0.0.1:50051") as c:
    route_client = RouteServiceStub(channel=c)
    try:
        route_client.CreateArea(Area(uuid=BytesValue(value="not a uuid".encode())))
    except grpc.RpcError as e:
        if isinstance(e, grpc.Call):
            print(e.details())
```
This will print `'uuid.value' must be a valid UUID`.

#### Non-default validator
For fields that should have a non-default value, such as
[enums](https://developers.google.com/protocol-buffers/docs/style#enums), we have provided the `non_default` argument:
```python
class RouteServiceImpl(RouteServiceServicer):
    @validate_args(non_default=["planet.value"])
    def CreateRoute(self, request: Route, context: grpc.ServicerContext):
        return Empty()
```
The client side may violate this as follows:
```python
with grpc.insecure_channel("127.0.0.1:50051") as c:
    route_client = RouteServiceStub(channel=c)
    try:
        route_client.CreateRoute(Route(planet=PlanetValue()))
    except grpc.RpcError as e:
        if isinstance(e, grpc.Call):
            print(e.details())
```
Which will print `'planet.value' must have non-default value`.

#### Non-empty validator
We provide a 'non-'empty validator which can be used to ensure that a `repeated` field has more than zero elements.
```python
class RouteServiceImpl(RouteServiceServicer):
    @validate_args(non_empty=["tags"])
    def CreateRoute(self, request: Route, context: grpc.ServicerContext):
        return Empty()
```
Which can be violated as follows:

```python
with grpc.insecure_channel("127.0.0.1:50051") as c:
    route_client = RouteServiceStub(channel=c)
    try:
        route_client.CreateRoute(Route(tags=[]))
    except grpc.RpcError as e:
        if isinstance(e, grpc.Call):
            print(e.details())
```
Which will print `'tags' must be non-empty`.

#### Regexp validator
Finally, we have the regexp validator that can be used to check whether a string field matches a regular expression.
```python
class RouteServiceImpl(RouteServiceServicer):
    @validate_args(validators={"message.value": RegexpValidator(pattern=r"\d+")})
    def CreateArea(self, request: Area, context: grpc.ServicerContext):
        return Empty()
```

```python
with grpc.insecure_channel("127.0.0.1:50051") as c:
    route_client = RouteServiceStub(channel=c)
    try:
        route_client.CreateArea(Area(message=StringValue(value="hello world")))
    except grpc.RpcError as e:
        if isinstance(e, grpc.Call):
            print(e.details())
```
Which will print `'message.value' must match regexp pattern: \d+`.

#### Custom validators
You can also write custom validators to flexibily handle your use-case. You need to derive a class from
`AbstractArgumentValidator` and implement its `check` method. The example below shows how to implement a simple
validator for checking that a path has 5 points. You can provide such custom validators through a `dict` that
maps a field path to a validator:
```python
from grpc_argument_validator import AbstractArgumentValidator
from grpc_argument_validator import ValidationContext
from grpc_argument_validator import ValidationResult
from google.protobuf.descriptor import FieldDescriptor

from examples.route_guide_pb2 import Path

class PathValidator(AbstractArgumentValidator):
    def check(
        self, name: str, value: Path, field_descriptor: FieldDescriptor, validation_context: ValidationContext
    ) -> ValidationResult:
        if len(value.points) > 5:
            return ValidationResult(valid=True)
        return ValidationResult(False, f"path for '{name}' should be at least five points long")


class RouteServiceImpl(RouteServiceServicer):

    @validate_args(validators={"path": PathValidator()})
    def CreateRoute(self, request: Route, context: grpc.ServicerContext):
        return Empty()
```

### Optional vs. required validators
For each of the built-in validators (except for the `has` validator), `validate_args` has not one but two keyword
arguments. One of those is prepended with `optional_`. This means that apart from `uuid`, `non_default` and
`non_empty` we also have `optional_uuid`, `optional_non_default` and `optional_non_empty`. The behavior is slightly
different: for any of the `optional_*` validators, it is OK if the field is not contained by the incoming request.
Sometimes fields are simply optional, and you only want to validate them _if_ they are present.

Since it is also common that fields are _not optional_, we also provide the required validators (without `optional_*`)
for which [`HasField`](https://googleapis.dev/python/protobuf/latest/google/protobuf/message.html#google.protobuf.message.Message.HasField)
must evaluate to `True` for that field and all preceding fields in the protos hierarchy.

The custom validator counterparts are `validators` and `optional_validators`. Each takes a `dict` with a mapping of
field paths to validators. These can be used for validators that might be preconfigured such as the `RegexpValidator`
or for customer validators.

### Streaming requests
You can also use the validators for streaming requests. Since streaming requests might not all look the same in a
single stream (e.g. the first request might have metadata describing the remainder of the stream), we provide a
streaming request index in a `ValidationContext` that is passed to an `AbstractArgumentValidator`.

Here's an example of how that could be used:
```python
class StreamingPathValidator(AbstractArgumentValidator):
    def __init__(self, first_number_of_points: int, second_number_of_points: int):
        self._first_number_of_points = first_number_of_points
        self._second_number_of_points = second_number_of_points

    def check(
        self, name: str, value: Any, field_descriptor: FieldDescriptor, validation_context: ValidationContext
    ) -> ValidationResult:
        if not validation_context.is_streaming:
            return ValidationResult(False, "request must be a streaming request")

        if validation_context.streaming_message_index == 0:
            if len(value.points) != self._first_number_of_points:
                return ValidationResult(False, f"first path should have {self._first_number_of_points} points")

        if validation_context.streaming_message_index == 1:
            if len(value.points) != self._second_number_of_points:
                return ValidationResult(False, f"second path should have {self._second_number_of_points} points")

        return ValidationResult(True)
```

### Enabling rich error details
To enable [richer error responses](https://cloud.google.com/apis/design/errors#error_model) where each violation is
contained in a
[`BadRequest` proto](https://github.com/googleapis/googleapis/blob/master/google/rpc/error_details.proto), you can use
```python
from grpc_argument_validator import ArgumentValidatorConfig

ArgumentValidatorConfig.set_rich_grpc_errors(enabled=True)
```

Now, your client-side can parse the error details as follows:
```python
def extract_error_details(err):
    status_proto = status_pb2.Status()

    for metadatum in err.trailing_metadata():
        if isinstance(metadatum, _Metadatum):
            if metadatum.key == "grpc-status-details-bin":
                status_proto.MergeFromString(metadatum.value)

    unpacked = [_unpack_error_detail(det) for det in status_proto.details]
    return unpacked

def _unpack_error_detail(grpc_detail):
    val = error_details_pb2.BadRequest()
    grpc_detail.Unpack(val)
    return val

with grpc.insecure_channel("127.0.0.1:50051") as c:
    route_client = RouteServiceStub(channel=c)
    try:
        route_client.CreateArea(Area(message=StringValue(value="hello world")))
    except grpc.RpcError as e:
        error_details = extract_error_details(e)
        print(error_details)
```

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to be learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Generating HTML Documentation
Generate the docs by running:
```sh
pdoc --html -o docs src/grpc_argument_validator
```


<!-- LICENSE -->
## License

Distributed under The BSD 3-Clause License. Copyright (c) 2021, MessageBird
