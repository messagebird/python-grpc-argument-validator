import unittest
import uuid
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from unittest.mock import MagicMock

import grpc
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message
from google.protobuf.wrappers_pb2 import BytesValue
from google.protobuf.wrappers_pb2 import StringValue
from grpc_argument_validator import AbstractArgumentValidator
from grpc_argument_validator import ArgumentValidatorConfig
from grpc_argument_validator import RegexpValidator
from grpc_argument_validator import validate_args
from grpc_argument_validator import ValidationContext
from grpc_argument_validator import ValidationResult
from tests import StatusMatcher
from tests.route_guide_protos.route_guide_pb2 import Area
from tests.route_guide_protos.route_guide_pb2 import Path
from tests.route_guide_protos.route_guide_pb2 import Point


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


class TestStreamingValidators(unittest.TestCase):
    def test_validate_streaming_args(self):
        @dataclass
        class TestCase:
            description: str
            has: List[str]
            proto_stream: Iterable[Message]
            error: bool = False
            non_empty: List[str] = field(default_factory=list)
            non_default: List[str] = field(default_factory=list)
            uuids: List[str] = field(default_factory=list)
            optional_non_default: List[str] = field(default_factory=list)
            optional_uuids: List[str] = field(default_factory=list)
            error_message: Optional[str] = None
            decorator_error_message: Optional[str] = None
            validators: Optional[Dict[str, AbstractArgumentValidator]] = None
            optional_validators: Optional[Dict[str, AbstractArgumentValidator]] = None

        ArgumentValidatorConfig.set_rich_grpc_errors(enabled=True)

        for test_case in [
            TestCase(description="Test no stream", proto_stream=[], has=["name"]),
            TestCase(
                description="Test field available in every part of streaming request",
                has=["name"],
                proto_stream=[Point(name=StringValue(value="name")), Point(name=StringValue(value="another name"))],
            ),
            TestCase(
                description="Test missing field in every part of streaming request should throw error",
                has=["name"],
                proto_stream=[Point(name=StringValue(value="name")), Point()],
                error=True,
                error_message="must have 'name'",
            ),
            TestCase(
                description="Test field uuid available in every part of streaming request",
                proto_stream=[
                    Area(uuid=BytesValue(value=uuid.uuid4().bytes)),
                    Area(uuid=BytesValue(value=uuid.uuid4().bytes)),
                ],
                has=[],
                uuids=["uuid.value"],
            ),
            TestCase(
                description="Test field uuid not available in every part of streaming request",
                proto_stream=[Area(uuid=BytesValue(value=uuid.uuid4().bytes)), Area()],
                has=[],
                uuids=["uuid.value"],
                error=True,
                error_message="must have 'uuid'",
            ),
            TestCase(
                description="Test optional uuid not available in every part of streaming request",
                proto_stream=[Area(uuid=BytesValue(value=uuid.uuid4().bytes)), Area()],
                has=[],
                optional_uuids=["uuid.value"],
            ),
            TestCase(
                description="Test optional uuid not available in every part of streaming request",
                proto_stream=[Area(uuid=BytesValue(value=uuid.uuid4().bytes)), Area(uuid=BytesValue())],
                has=[],
                optional_uuids=["uuid.value"],
                error=True,
                error_message="'uuid.value' must be a valid UUID",
            ),
            TestCase(
                description="Test non-default check in every part of streaming request",
                proto_stream=[Point(name=StringValue(value="1234")), Point(name=StringValue(value="56789"))],
                has=[],
                non_default=["name.value"],
            ),
            TestCase(
                description="Test non-default check invalid in every part of streaming request",
                proto_stream=[Point(name=StringValue(value="")), Point(name=StringValue(value="56789"))],
                has=[],
                non_default=["name.value"],
                error=True,
                error_message="'name.value' must have non-default value",
            ),
            TestCase(
                description="Test non-empty check in every part of streaming request",
                proto_stream=[Point(name=StringValue(value="1234")), Point(name=StringValue(value="56789"))],
                has=[],
                non_empty=["name.value"],
            ),
            TestCase(
                description="Test non-empty check invalid in every part of streaming request",
                proto_stream=[Point(name=StringValue(value="")), Point(name=StringValue(value="56789"))],
                has=[],
                non_empty=["name.value"],
                error=True,
                error_message="'name.value' must be non-empty",
            ),
            TestCase(
                description="Test regex matching every part of streaming request",
                has=[],
                proto_stream=[Point(name=StringValue(value="1234")), Point(name=StringValue(value="567890"))],
                validators={"name.value": RegexpValidator(r"\d+")},
            ),
            TestCase(
                description="Test regex not matching every part of streaming request",
                has=[],
                proto_stream=[Point(name=StringValue(value="1234")), Point(name=StringValue(value="another name"))],
                validators={"name.value": RegexpValidator(r"\d+")},
                error=True,
                error_message=r"'name.value' must match regexp pattern: \d+",
            ),
            TestCase(
                description="Test iteration specific validation",
                has=[],
                proto_stream=[Path(points=[Point(), Point(), Point()]), Path(points=[Point(), Point()]),],
                validators={".": StreamingPathValidator(3, 2)},
            ),
            TestCase(
                description="Test iteration specific validation",
                has=[],
                proto_stream=[Path(points=[Point(), Point(), Point()]), Path(points=[Point(), Point()]),],
                validators={".": StreamingPathValidator(3, 3)},
                error=True,
                error_message="second path should have 3 points",
            ),
            TestCase(
                description="Empty set of validators",
                proto_stream=[Path(points=[Point(), Point(), Point()]), Path(points=[Point(), Point()]),],
                has=[],
                decorator_error_message="Should provide at least one field to validate",
            ),
        ]:
            with self.subTest(test_case.description):
                try:

                    class C:
                        @validate_args(
                            has=test_case.has,
                            uuids=test_case.uuids,
                            non_empty=test_case.non_empty,
                            optional_uuids=test_case.optional_uuids,
                            non_default=test_case.non_default,
                            optional_non_default=test_case.optional_non_default,
                            validators=test_case.validators,
                            optional_validators=test_case.optional_validators,
                        )
                        def fn(self, stream: Iterable[Message], context: grpc.ServicerContext):
                            for _ in stream:
                                pass

                except (KeyError, ValueError) as e:
                    assert str(e) == test_case.decorator_error_message
                else:
                    assert test_case.decorator_error_message is None
                    context = MagicMock()
                    context.abort_with_status.side_effect = Exception("invalid arg")
                    context.abort.side_effect = Exception("invalid arg")

                    c = C()

                    if test_case.error:
                        ArgumentValidatorConfig.set_rich_grpc_errors(enabled=True)
                        self.assertRaisesRegex(Exception, "invalid arg", lambda: c.fn(test_case.proto_stream, context))
                        context.abort_with_status.assert_called_once_with(
                            StatusMatcher(grpc.StatusCode.INVALID_ARGUMENT, test_case.error_message)
                        )

                        ArgumentValidatorConfig.set_rich_grpc_errors(enabled=False)
                        self.assertRaisesRegex(Exception, "invalid arg", lambda: c.fn(test_case.proto_stream, context))
                        context.abort.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT, test_case.error_message)
                    else:
                        c.fn(test_case.proto_stream, context)
