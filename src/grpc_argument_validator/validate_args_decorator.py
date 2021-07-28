import functools
import itertools
import re
from dataclasses import dataclass
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Union

import grpc
from google.protobuf import any_pb2
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message
from google.rpc import code_pb2
from google.rpc import error_details_pb2
from google.rpc import status_pb2
from grpc_argument_validator import AbstractArgumentValidator
from grpc_argument_validator.argument_validators import NonDefaultValidator
from grpc_argument_validator.argument_validators import NonEmptyValidator
from grpc_argument_validator.argument_validators import UUIDBytesValidator
from grpc_argument_validator.fields import validate_field_names
from grpc_argument_validator.validation_context import ValidationContext
from grpc_status import rpc_status


@dataclass
class _Error:
    field_name: str
    reason: str


def validate_args(
    has: Optional[List[str]] = None,
    uuids: Optional[List[str]] = None,
    non_default: Optional[List[str]] = None,
    non_empty: Optional[List[str]] = None,
    optional_uuids: Optional[List[str]] = None,
    optional_non_empty: Optional[List[str]] = None,
    optional_non_default: Optional[List[str]] = None,
    validators: Optional[Dict[str, AbstractArgumentValidator]] = None,
    optional_validators: Optional[Dict[str, AbstractArgumentValidator]] = None,
) -> Callable:
    """
    Decorator to validate Message type arguments for gRPC methods.

    Subfields can be separated by a `.`.

    E.g. `foo.bar` where bar is a property of the Message in foo.


    For lists the same notation can be used, for clarity `[]` can be added optionally. Both `foo.bar` and `foo[].bar`
    can be used, where bar is a property of the Message in the list foo.

        Parameters:
            has (Optional[List[str]]):
                Fields the Message should contain
            uuids (Optional[List[str]]):
                Fields to be validated for UUIDs
            non_default (Optional[List[str]]):
                Fields that should not have the default value
            non_empty (Optional[List[str]]):
                Fields that should not be empty
            optional_uuids (Optional[List[str]]):
                Fields that can be None or a valid UUID
            optional_non_empty (Optional[List[str]]):
                Fields that can be None or non-empty
            optional_non_default (Optional[List[str]]):
                Fields that can be None or non-default
            validators (Optional[Dict[str, AbstractArgumentValidator]]):
                Dict mapping field names to validators
            optional_validators (Optional[Dict[str, AbstractArgumentValidator]]):
                Dict mapping field names to validators, the fields can be None or validated using the specified
                validator

        Returns:
            decorating_function (func): the decorating function wrapping the gRPC method function
    """
    if all(arg is None for arg in locals().values()):
        raise ValueError("Should provide at least one field to validate")
    has_value = has or []

    optional_uuids_value = optional_uuids or []
    optional_non_empty_value = optional_non_empty or []
    optional_non_default_value = optional_non_default or []
    optional_validators_value: Dict[str, AbstractArgumentValidator] = optional_validators or dict()

    uuids_value = uuids or []
    non_empty_value = non_empty or []
    non_default_value = non_default or []
    validators_value = validators or dict()

    field_names = list(
        itertools.chain(
            has_value,
            uuids_value,
            optional_uuids_value,
            non_empty_value,
            optional_non_empty_value,
            non_default_value,
            optional_non_default_value,
            validators_value.keys(),
            optional_validators_value.keys(),
        )
    )
    validate_field_names(field_names)

    mandatory_fields = set(uuids_value + non_empty_value + non_default_value + list(validators_value.keys()))
    optional_fields = set(
        optional_uuids_value
        + optional_non_empty_value
        + optional_non_default_value
        + list(optional_validators_value.keys())
    )

    if mandatory_fields.intersection(optional_fields):
        raise ValueError("Overlap in mandatory and optional fields")

    def decorating_function(func):
        def validate_message(request: Message, context: grpc.ServicerContext, validation_context: ValidationContext):
            errors = []
            for field_name in field_names:
                field_validators: List[AbstractArgumentValidator] = []
                is_optional = (
                    field_name in optional_non_empty_value
                    or field_name in optional_uuids_value
                    or field_name in optional_non_default_value
                    or field_name in optional_validators_value
                )
                if field_name in uuids_value + optional_uuids_value:
                    field_validators.append(UUIDBytesValidator())
                if field_name in non_empty_value + optional_non_empty_value:
                    field_validators.append(NonEmptyValidator())
                if field_name in non_default_value + optional_non_default_value:
                    field_validators.append(NonDefaultValidator())
                if field_name in itertools.chain(validators_value.keys(), optional_validators_value.keys()):
                    validator = {**validators_value, **optional_validators_value}.get(field_name)
                    if validator is not None:
                        field_validators.append(validator)

                errors.extend(
                    _recurse_validate(
                        request,
                        name=field_name,
                        validators=field_validators,
                        is_optional=is_optional,
                        validation_context=validation_context,
                    )
                )
            if len(errors) > 0:
                rich_status = _create_rich_validation_error(errors)
                context.abort_with_status(rpc_status.to_status(rich_status))

        def validate_streaming(requests: Iterable[Message], context: grpc.ServicerContext):
            for i, req in enumerate(requests):
                validate_message(req, context, ValidationContext(is_streaming=True, streaming_message_index=i))
                yield req

        @functools.wraps(func)
        def validate_wrapper(self, request: Union[Message, Iterable[Message]], context: grpc.ServicerContext):
            if isinstance(request, Iterable):
                return func(self, validate_streaming(request, context), context)
            else:
                validate_message(request, context, ValidationContext(is_streaming=False, streaming_message_index=None))
                return func(self, request, context)

        return validate_wrapper

    return decorating_function


def _create_rich_validation_error(errors: List[_Error]):
    detail = any_pb2.Any()
    detail.Pack(
        error_details_pb2.BadRequest(
            field_violations=[
                error_details_pb2.BadRequest.FieldViolation(field=e.field_name, description=e.reason,) for e in errors
            ]
        )
    )
    return status_pb2.Status(
        code=code_pb2.INVALID_ARGUMENT, message=", ".join([e.reason for e in errors])[:1000], details=[detail],
    )


def _recurse_validate(
    message: Message,
    name: str,
    validation_context: ValidationContext,
    validators: List[AbstractArgumentValidator],
    leading_parts_name: str = None,
    is_optional: bool = False,
) -> List[_Error]:
    errors: List[_Error] = []
    field_name_raw, *remaining_fields = name.split(".")
    field_name = field_name_raw.rstrip("[]")

    remaining_fields = [f for f in remaining_fields if f != ""]

    if leading_parts_name is None and field_name == "":
        field_value = message
        field_descriptor: FieldDescriptor = message.DESCRIPTOR  # type: ignore
        full_name = message.DESCRIPTOR.name
    else:
        field_descriptor = message.DESCRIPTOR.fields_by_name[field_name]

        full_name = field_name if leading_parts_name is None else f"{leading_parts_name}.{field_name}"
        if (
            field_descriptor.label != FieldDescriptor.LABEL_REPEATED
            and field_descriptor.type == FieldDescriptor.TYPE_MESSAGE
            and not message.HasField(field_name)
        ):
            if is_optional:
                return []
            return [_Error(field_name=full_name, reason=f"request must have {full_name}")]

        field_value = getattr(message, field_name)

    if remaining_fields:
        if field_descriptor.label == FieldDescriptor.LABEL_REPEATED:
            for i, elem in enumerate(field_value):  # type: ignore
                errors.extend(
                    _recurse_validate(
                        message=elem,
                        name=".".join(remaining_fields),
                        leading_parts_name=f"{full_name}[{i}]",
                        validators=validators,
                        is_optional=is_optional,
                        validation_context=validation_context,
                    )
                )
        else:
            errors.extend(
                _recurse_validate(
                    message=field_value,
                    name=".".join(remaining_fields),
                    leading_parts_name=full_name,
                    validators=validators,
                    is_optional=is_optional,
                    validation_context=validation_context,
                )
            )
    else:
        for v in validators:
            if field_name_raw.endswith("[]") and field_descriptor.label == FieldDescriptor.LABEL_REPEATED:
                for i, field_value_elem in enumerate(field_value):  # type: ignore
                    full_field_name = f"{full_name}[{i}]"
                    validation_result = v.check(full_field_name, field_value_elem, field_descriptor, validation_context)
                    if not validation_result.valid:
                        errors.append(
                            _Error(
                                field_name=full_field_name,
                                reason=""
                                if validation_result.invalid_reason is None
                                else validation_result.invalid_reason,
                            )
                        )
            else:
                validation_result = v.check(full_name, field_value, field_descriptor, validation_context)
                if not validation_result.valid:
                    errors.append(
                        _Error(
                            field_name=full_name,
                            reason="" if validation_result.invalid_reason is None else validation_result.invalid_reason,
                        )
                    )
    return errors
