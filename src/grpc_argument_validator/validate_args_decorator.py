import functools
import itertools
import re
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

import grpc
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message
from grpc_argument_validator import AbstractArgumentValidator
from grpc_argument_validator.argument_validators import NonDefaultValidator
from grpc_argument_validator.argument_validators import NonEmptyValidator
from grpc_argument_validator.argument_validators import UUIDBytesValidator


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
    for field_name in field_names:
        if not _is_valid_field_path(field_name):
            raise ValueError(
                f"Field name {field_name} does not adhere to Protobuf 3 language specification, "
                f"may be prepended with '.' or appended with '[]'. Alternatively, '.' should be used for "
                f"performing validations on the 'root' proto."
            )

    if set(uuids_value + non_empty_value + non_default_value + list(validators_value.keys())).intersection(
        set(
            optional_uuids_value
            + optional_non_empty_value
            + optional_non_default_value
            + list(optional_validators_value.keys())
        )
    ):
        raise ValueError("Overlap in mandatory and optional fields")

    def decorating_function(func):
        @functools.wraps(func)
        def validate_wrapper(self, request: Message, context: grpc.ServicerContext):
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
                    _recurse_validate(request, name=field_name, validators=field_validators, is_optional=is_optional)
                )
            if len(errors) > 0:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, ", ".join(errors)[:1000])
            return func(self, request, context)

        return validate_wrapper

    return decorating_function


def _recurse_validate(
    message: Message,
    name: str,
    validators: List[AbstractArgumentValidator],
    leading_parts_name: str = None,
    is_optional: bool = False,
):
    errors = []
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
            return [f"request must have {full_name}"]

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
                )
            )
    else:
        for v in validators:
            if field_name_raw.endswith("[]") and field_descriptor.label == FieldDescriptor.LABEL_REPEATED:
                for i, field_value_elem in enumerate(field_value):  # type: ignore
                    validation_result = v.check(f"{full_name}[{i}]", field_value_elem, field_descriptor)
                    if not validation_result.valid:
                        errors.append(validation_result.invalid_reason)
            else:
                validation_result = v.check(full_name, field_value, field_descriptor)
                if not validation_result.valid:
                    errors.append(validation_result.invalid_reason)
    return errors


def _is_valid_field_path(path: str):
    return re.match(r"^(?:\.|\.?(?:[a-zA-Z][a-zA-Z_0-9]*\.)*(?:[a-zA-Z][a-zA-Z_0-9]*)(?:\[\])?)$", path) is not None
