import abc
import re
import typing
import uuid

from google.protobuf.descriptor import FieldDescriptor

from .validation_result import ValidationResult


class AbstractStreamingArgumentValidator(abc.ABC):
    """
    An abstract class that is the base for all argument validators
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


class StreamingUUIDBytesValidator(AbstractStreamingArgumentValidator):
    """Class that ensures the provided value is a valid UUID"""

    def check(
        self, message_index: int, name: str, value: typing.Any, field_descriptor: FieldDescriptor
    ) -> ValidationResult:
        try:
            uuid.UUID(bytes=value)
        except (ValueError, TypeError):
            return ValidationResult(False, f"in message request {message_index} {name} must be a valid UUID")
        return ValidationResult(True)


class StreamingNonDefaultValidator(AbstractStreamingArgumentValidator):
    """Ensures the provided value is not the default value for this field type"""

    def check(
        self, message_index: int, name: str, value: typing.Any, field_descriptor: FieldDescriptor
    ) -> ValidationResult:
        if value != field_descriptor.default_value:
            return ValidationResult(True)
        return ValidationResult(False, f"in message request {message_index} {name} must have non-default value")


class StreamingNonEmptyValidator(AbstractStreamingArgumentValidator):
    """Ensures the provided value is non-empty"""

    def check(
        self, message_index: int, name: str, value: typing.Any, field_descriptor: FieldDescriptor
    ) -> ValidationResult:
        if len(value) > 0:
            return ValidationResult(True)
        return ValidationResult(False, f"in message request {message_index} {name} must be non-empty")


class StreamingRegexpValidator(AbstractStreamingArgumentValidator):
    """
    Matches the input value against the provided regex.

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
            False, f"in message request {message_index} {name} must match regexp pattern: {self._pattern}"
        )
