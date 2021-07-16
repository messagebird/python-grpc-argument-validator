import abc
import re
import typing
import uuid

from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message

from .validation_result import ValidationResult


class AbstractStreamingArgumentValidator(abc.ABC):
    """
    An abstract class that is the base for all streaming argument validators
    """

    @abc.abstractmethod
    def check(
        self, message_index: int, name: str, value: typing.Any, field_descriptor: FieldDescriptor
    ) -> ValidationResult:
        """
        Returns a validation bool of the given value and field_descriptor

            Parameters:
                message_index: The index of the message in the streaming request
                name (str): Name for the field to be used in invalid reason messages.
                value (typing.Any): The value to be validated
                field_descriptor (FieldDescriptor): The protobuf field descriptor of the given value

            Returns:
                result (ValidationResult): validation bool for the given value
        """
        pass


class StreamingHasFieldValidator(AbstractStreamingArgumentValidator):
    """
    Checks if all input values in the stream have the specified fields

    Parameters:
        field name (str): field name to check.
    """

    def __init__(self, field_name: str) -> None:
        self._field_name = field_name

    def check(
        self, message_index: int, name: str, value: typing.Any, field_descriptor: FieldDescriptor
    ) -> ValidationResult:
        try:
            getattr(value, self._field_name)
        except AttributeError:
            raise Exception(f"{name} doesn't have a field {self._field_name}")
        if isinstance(value, Message) and not value.HasField(self._field_name):
            return ValidationResult(False, f"{self._field_name} must be set in message request index {message_index}")
        return ValidationResult(True)


class StreamingUUIDBytesValidator(AbstractStreamingArgumentValidator):
    """Ensures all the provided values in the stream are valid UUIDs"""

    def check(
        self, message_index: int, name: str, value: typing.Any, field_descriptor: FieldDescriptor
    ) -> ValidationResult:
        try:
            uuid.UUID(bytes=value)
        except (ValueError, TypeError):
            return ValidationResult(False, f"{name} must be a valid UUID in message request index {message_index}",)
        return ValidationResult(True)


class StreamingNonDefaultValidator(AbstractStreamingArgumentValidator):
    """Ensures all the provided values in the stream are non-empty not the default value for this field type"""

    def check(
        self, message_index: int, name: str, value: typing.Any, field_descriptor: FieldDescriptor
    ) -> ValidationResult:
        if value != field_descriptor.default_value:
            return ValidationResult(True)
        return ValidationResult(False, f"{name} must have non-default value in message request index {message_index}")


class StreamingNonEmptyValidator(AbstractStreamingArgumentValidator):
    """Ensures all the provided values in the stream are non-empty"""

    def check(
        self, message_index: int, name: str, value: typing.Any, field_descriptor: FieldDescriptor
    ) -> ValidationResult:
        if len(value) > 0:
            return ValidationResult(True)
        return ValidationResult(False, f"{name} must be non-empty in message request index {message_index}",)


class StreamingRegexpValidator(AbstractStreamingArgumentValidator):
    """
    Matches all input values in the stream against the provided regex.

    Parameters:
        pattern (str): Regexp pattern to match.
    """

    def __init__(self, pattern: str):
        self._pattern = pattern

    def check(
        self, message_index: int, name: str, value: typing.Any, field_descriptor: FieldDescriptor
    ) -> ValidationResult:
        if re.match(self._pattern, value) is not None:
            return ValidationResult(True)
        return ValidationResult(
            False, f"{name} must match regexp pattern: {self._pattern} in message request index {message_index}"
        )
