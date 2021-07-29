import unittest
import uuid
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from unittest.mock import MagicMock

import grpc
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message
from google.protobuf.wrappers_pb2 import BytesValue
from google.protobuf.wrappers_pb2 import StringValue
from grpc_argument_validator import AbstractArgumentValidator
from grpc_argument_validator import ArugmentValidatorConfig
from grpc_argument_validator import RegexpValidator
from grpc_argument_validator import validate_args
from grpc_argument_validator.argument_validators import ValidationContext
from grpc_argument_validator.argument_validators import ValidationResult
from tests import StatusMatcher
from tests.route_guide_protos.route_guide_pb2 import Area
from tests.route_guide_protos.route_guide_pb2 import Path
from tests.route_guide_protos.route_guide_pb2 import PLANET_EARTH
from tests.route_guide_protos.route_guide_pb2 import PLANET_INVALID
from tests.route_guide_protos.route_guide_pb2 import PlanetValue
from tests.route_guide_protos.route_guide_pb2 import Point
from tests.route_guide_protos.route_guide_pb2 import Rectangle
from tests.route_guide_protos.route_guide_pb2 import Route


class RouteValidator(AbstractArgumentValidator):
    def check(
        self, name: str, value: Any, field_descriptor: FieldDescriptor, validation_context: ValidationContext
    ) -> ValidationResult:
        invalid_reasons = []
        if len(value.path.points) == 0:
            invalid_reasons.append(f"{name}.path.points should be non-empty")
        if not (value.HasField("name") and value.name.value != ""):
            invalid_reasons.append(f"{name}.name.value should be non-empty")
        return ValidationResult(len(invalid_reasons) == 0, ", ".join(invalid_reasons))


class TestValidators(unittest.TestCase):
    def test_validate_args(self):
        @dataclass
        class TestCase:
            description: str
            has: List[str]
            proto: Message
            error: bool = False
            non_empty: List[str] = field(default_factory=list)
            non_default: List[str] = field(default_factory=list)
            optional_non_default: List[str] = field(default_factory=list)
            uuids: List[str] = field(default_factory=list)
            optional_uuids: List[str] = field(default_factory=list)
            error_message: Optional[str] = None
            decorator_error_message: Optional[str] = None
            validators: Optional[Dict[str, AbstractArgumentValidator]] = None
            optional_validators: Optional[Dict[str, AbstractArgumentValidator]] = None

        ArugmentValidatorConfig.set_rich_grpc_errors(enabled=True)

        for test_case in [
            TestCase(
                description="Test valid proto",
                proto=Area(
                    message=StringValue(value="message"),
                    rectangle=Rectangle(
                        lo=Point(x=0, y=0, name=StringValue(value="point0")),
                        hi=Point(x=1, y=1, name=StringValue(value="point1")),
                    ),
                    uuid=BytesValue(value=uuid.uuid4().bytes),
                ),
                has=["rectangle.lo.name", "rectangle.hi.name"],
                non_empty=["message.value"],
                uuids=["uuid.value"],
                error=False,
            ),
            TestCase(
                description="Test empty name invalid",
                proto=Area(
                    message=StringValue(value=""),
                    rectangle=Rectangle(
                        lo=Point(x=0, y=0, name=StringValue(value="point0")),
                        hi=Point(x=1, y=1, name=StringValue(value="point1")),
                    ),
                    uuid=BytesValue(value=uuid.uuid4().bytes),
                ),
                has=["rectangle.lo.name", "rectangle.hi.name"],
                non_empty=["message.value"],
                uuids=["uuid.value"],
                error=True,
                error_message="message.value must be non-empty",
            ),
            TestCase(
                description="Test missing uuid",
                proto=Area(
                    message=StringValue(value="message"),
                    rectangle=Rectangle(
                        lo=Point(x=0, y=0, name=StringValue(value="point0")),
                        hi=Point(x=1, y=1, name=StringValue(value="point1")),
                    ),
                ),
                has=["message.value", "rectangle.lo.name", "rectangle.hi.name"],
                uuids=["uuid.value"],
                error=True,
                error_message="request must have uuid",
            ),
            TestCase(
                description="Test invalid uuid",
                proto=Area(
                    message=StringValue(value="message"),
                    rectangle=Rectangle(
                        lo=Point(x=0, y=0, name=StringValue(value="point0")),
                        hi=Point(x=1, y=1, name=StringValue(value="point1")),
                    ),
                    uuid=BytesValue(value=b""),
                ),
                has=["message.value", "rectangle.lo.name", "rectangle.hi.name"],
                uuids=["uuid.value"],
                error=True,
                error_message="uuid.value must be a valid UUID",
            ),
            TestCase(
                description="Test optional uuid",
                proto=Area(
                    message=StringValue(value="message"),
                    rectangle=Rectangle(
                        lo=Point(x=0, y=0, name=StringValue(value="point0")),
                        hi=Point(x=1, y=1, name=StringValue(value="point1")),
                    ),
                ),
                has=["message.value", "rectangle.lo.name", "rectangle.hi.name"],
                optional_uuids=["uuid.value"],
                error=False,
            ),
            TestCase(
                description="Test without name invalid",
                proto=Area(
                    message=StringValue(value="message"),
                    rectangle=Rectangle(lo=Point(x=0, y=0, name=StringValue(value="point0")), hi=Point(x=1, y=1)),
                ),
                has=["message.value", "rectangle.lo.name", "rectangle.hi.name"],
                error=True,
                error_message="request must have rectangle.hi.name",
            ),
            TestCase(
                description="Test without hi valid",
                proto=Area(
                    message=StringValue(value="message"),
                    rectangle=Rectangle(lo=Point(x=0, y=0, name=StringValue(value="point0")),),
                ),
                has=["message.value", "rectangle.lo"],
                error=False,
            ),
            TestCase(
                description="Test without rectangle invalid",
                proto=Area(message=StringValue(value="message")),
                has=["message.value", "rectangle.lo"],
                error=True,
                error_message="request must have rectangle",
            ),
            TestCase(
                description="Test repeated non-empty valid",
                proto=Path(points=[Point(), Point(), Point()]),
                has=[],
                non_empty=["points"],
                error=False,
            ),
            TestCase(
                description="Test repeated empty invalid",
                proto=Path(points=[]),
                has=[],
                non_empty=["points"],
                error=True,
                error_message="points must be non-empty",
            ),
            TestCase(
                description="Test repeated recursive",
                proto=Path(points=[Point(x=1, y=1, name=StringValue(value="a")), Point(x=1, y=1)]),
                has=["points.name"],
                error=True,
                error_message="request must have points[1].name",
            ),
            TestCase(
                description="Test repeated recursive valid",
                proto=Path(
                    points=[Point(x=1, y=1, name=StringValue(value="a")), Point(x=1, y=1, name=StringValue(value="b"))]
                ),
                has=["points.name"],
                error=False,
            ),
            TestCase(
                description="Test repeated recursive valid",
                proto=Path(
                    points=[Point(x=1, y=1, name=StringValue(value="a")), Point(x=1, y=1, name=StringValue(value=""))]
                ),
                has=[],
                non_empty=["points.name.value"],
                error=True,
                error_message="points[1].name.value must be non-empty",
            ),
            TestCase(
                description="Test repeated recursive valid because empty list",
                proto=Path(points=[]),
                has=[],
                non_empty=["points.name.value"],
                error=False,
            ),
            TestCase(
                description="Test repeated recursive valid because no list",
                proto=Path(),
                has=[],
                non_empty=["points.name.value"],
                error=False,
            ),
            TestCase(
                description="Test repeated recursive valid because no list",
                proto=Path(),
                has=[],
                non_empty=["points.name.value"],
                error=False,
            ),
            TestCase(
                description="Non-default invalid",
                proto=Route(planet=PlanetValue(value=PLANET_INVALID)),
                has=[],
                non_default=["planet.value"],
                error=True,
                error_message="planet.value must have non-default value",
            ),
            TestCase(
                description="Non-default optional",
                proto=Route(),
                has=[],
                optional_non_default=["planet.value"],
                error=False,
            ),
            TestCase(
                description="Non-default optional invalid",
                proto=Route(planet=PlanetValue(value=PLANET_INVALID)),
                has=[],
                optional_non_default=["planet.value"],
                error=True,
                error_message="planet.value must have non-default value",
            ),
            TestCase(
                description="Non-default valid",
                proto=Route(planet=PlanetValue(value=PLANET_EARTH)),
                has=[],
                non_default=["planet.value"],
                error=False,
            ),
            TestCase(
                description="Test invalid args empty",
                proto=Path(),
                has=[],
                non_empty=[],
                decorator_error_message="Should provide at least one field to validate",
            ),
            TestCase(
                description="Test invalid args intersection required and optional",
                proto=Route(),
                optional_uuids=["uuid.value"],
                uuids=["uuid.value"],
                has=[],
                decorator_error_message="Overlap in mandatory and optional fields",
            ),
            TestCase(
                description="Test invalid regex",
                proto=Area(message=StringValue(value="abc")),
                has=[],
                validators={"message.value": RegexpValidator(pattern=r"\d+")},
                error=True,
                error_message=r"message.value must match regexp pattern: \d+",
            ),
            TestCase(
                description="Test valid regex",
                proto=Area(message=StringValue(value="123")),
                has=[],
                validators={"message.value": RegexpValidator(pattern=r"\d+")},
                error=False,
            ),
            TestCase(
                description="Test valid regex optional",
                proto=Area(message=StringValue(value="123")),
                has=[],
                optional_validators={"message.value": RegexpValidator(pattern=r"\d+")},
                error=False,
            ),
            TestCase(
                description="Test valid regex optional, field absent",
                proto=Area(),
                has=[],
                optional_validators={"message.value": RegexpValidator(pattern=r"\d+")},
                error=False,
            ),
            TestCase(
                description="Test invalid regex optional",
                proto=Area(message=StringValue(value="abc")),
                has=[],
                optional_validators={"message.value": RegexpValidator(pattern=r"\d+")},
                error=True,
                error_message=r"message.value must match regexp pattern: \d+",
            ),
            TestCase(
                description="Test valid list multi tags",
                has=[],
                proto=Route(tags=["first", "second"]),
                non_empty=["tags", "tags[]"],
                error=False,
            ),
            TestCase(
                description="Test invalid list elem multi tags",
                has=[],
                proto=Route(tags=["first", ""]),
                non_empty=["tags", "tags[]"],
                error=True,
                error_message="tags[1] must be non-empty",
            ),
            TestCase(
                description="Test invalid list empty list multi tags",
                has=[],
                proto=Route(tags=[]),
                non_empty=["tags", "tags[]"],
                error=True,
                error_message="tags must be non-empty",
            ),
            TestCase(
                description="Test base proto invalid route empty name",
                proto=Route(path=Path(points=[Point()])),
                has=[],
                validators={".": RouteValidator()},
                error=True,
                error_message=r"Route.name.value should be non-empty",
            ),
            TestCase(
                description="Test base proto invalid route empty points and empty name",
                proto=Route(path=Path()),
                has=[],
                validators={".": RouteValidator()},
                error=True,
                error_message=r"Route.path.points should be non-empty, Route.name.value should be non-empty",
            ),
            TestCase(
                description="Test base proto invalid route empty points",
                proto=Route(name=StringValue(value="name")),
                has=[],
                validators={".": RouteValidator()},
                error=True,
                error_message=r"Route.path.points should be non-empty",
            ),
            TestCase(
                description="Test invalid field name symbol",
                proto=Route(name=StringValue(value="name")),
                has=["-"],
                decorator_error_message=f"Field name - does not adhere to Protobuf 3 language specification, "
                f"may be prepended with '.' or appended with '[]'. Alternatively, '.' should be used for "
                f"performing validations on the 'root' proto.",
            ),
            TestCase(
                description="Test invalid field name digit",
                proto=Route(name=StringValue(value="name")),
                has=["0"],
                decorator_error_message=f"Field name 0 does not adhere to Protobuf 3 language specification, "
                f"may be prepended with '.' or appended with '[]'. Alternatively, '.' should be used for "
                f"performing validations on the 'root' proto.",
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
                        def fn(self, field: Message, context: grpc.ServicerContext):
                            pass

                except ValueError as e:
                    assert str(e) == test_case.decorator_error_message
                else:
                    context = MagicMock()
                    context.abort_with_status.side_effect = Exception("invalid arg")

                    c = C()

                    if test_case.error:
                        self.assertRaisesRegex(Exception, "invalid arg", lambda: c.fn(test_case.proto, context))
                        context.abort_with_status.assert_called_once_with(
                            StatusMatcher(grpc.StatusCode.INVALID_ARGUMENT, test_case.error_message)
                        )
                    else:
                        c.fn(test_case.proto, context)
