# gRPC argument validator
gRPC argument validator is a library that provides decorators to automatically validate arguments in requests to rpc methods.

<!-- GETTING STARTED -->
## Getting Started

This is an example of how you may give instructions on setting up your project locally.
To get a local copy up and running follow these simple example steps.

### Prerequisites

Poetry is required to locally run the tests for this library
* poetry
  ```sh
  pip install --user poetry
  ```

### Installation
1. Clone the repo
   ```sh
   git clone https://github.com/messagebird/python-grpc-argument-validator.git
   ```
2. Install packages
   ```sh
   poetry install
   ```
3. Run the tests
   ```sh
   cd src/tests
   poetry run python -m unittest
   ```

### Installation via pip
```sh
pip install grpc-argument-validator
```


<!-- USAGE EXAMPLES -->
## Example
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




<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to be learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request


## Documentation
Generate the docs by running:
```sh
pdoc --html -o docs src/grpc_argument_validator
```


<!-- LICENSE -->
## License

Distributed under The BSD 3-Clause License. Copyright (c) 2021, MessageBird
