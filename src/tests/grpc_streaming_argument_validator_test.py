import unittest
import uuid
from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from unittest.mock import MagicMock

import grpc
from google.protobuf.message import Message
from google.protobuf.wrappers_pb2 import BytesValue
from google.protobuf.wrappers_pb2 import StringValue
from grpc_argument_validator import AbstractStreamingArgumentValidator
from grpc_argument_validator import validate_streaming_args
from grpc_argument_validator.streaming_argument_validators import StreamingRegexpValidator
from tests.route_guide_protos.route_guide_pb2 import Area
from tests.route_guide_protos.route_guide_pb2 import Point


class TestValidators(unittest.TestCase):
    def test_validate_args(self):
        @dataclass
        class TestCase:
            description: str
            has: List[str]
            proto_stream: Iterable[Message]
            error: bool = False
            non_empty: List[str] = field(default_factory=list)
            non_default: List[str] = field(default_factory=list)
            optional_non_default: List[str] = field(default_factory=list)
            uuids: List[str] = field(default_factory=list)
            optional_uuids: List[str] = field(default_factory=list)
            error_message: Optional[str] = None
            decorator_error_message: Optional[str] = None
            validators: Optional[Dict[str, AbstractStreamingArgumentValidator]] = None
            optional_validators: Optional[Dict[str, AbstractStreamingArgumentValidator]] = None

        for test_case in [
            TestCase(description="Test no stream", proto_stream=[], has=[],),
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
                error_message="name must be set in message request index 1",
            ),
            TestCase(
                description="Test field uuid available in every part of streaming request",
                proto_stream=[
                    Area(uuid=BytesValue(value=uuid.uuid4().bytes),),
                    Area(uuid=BytesValue(value=uuid.uuid4().bytes),),
                ],
                has=[],
                uuids=["uuid.value"],
            ),
            TestCase(
                description="Test field uuid not available in every part of streaming request",
                proto_stream=[Area(uuid=BytesValue(value=uuid.uuid4().bytes),), Area(),],
                has=[],
                uuids=["uuid.value"],
                error=True,
                error_message="uuid.value must be a valid UUID in message request index 1",
            ),
            TestCase(
                description="Test regex every part of streaming request",
                has=[],
                proto_stream=[Point(name=StringValue(value="1234")), Point(name=StringValue(value="567890"))],
                validators={"name.value": StreamingRegexpValidator(r"\d+")},
            ),
            TestCase(
                description="Test regex not matching every part of streaming request",
                has=[],
                proto_stream=[Point(name=StringValue(value="1234")), Point(name=StringValue(value="another name"))],
                validators={"name.value": StreamingRegexpValidator(r"\d+")},
                error=True,
                error_message=r"name.value must match regexp pattern: \d+ in message request index 1",
            ),
        ]:
            with self.subTest(test_case.description):
                try:

                    class C:
                        @validate_streaming_args(
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

                except KeyError as e:
                    assert str(e) == test_case.decorator_error_message
                else:
                    context = MagicMock()
                    context.abort.side_effect = Exception("invalid arg")

                    c = C()

                    if test_case.error:
                        self.assertRaisesRegex(Exception, "invalid arg", lambda: c.fn(test_case.proto_stream, context))
                        context.abort.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT, test_case.error_message)
                    else:
                        c.fn(test_case.proto_stream, context)
