import abc
import re
import typing
import uuid
from dataclasses import dataclass

from google.protobuf.descriptor import FieldDescriptor


@dataclass
class ValidationResult:
    """
    Contains results for validation check.
    """

    valid: bool
    """Whether the argument was valid."""

    invalid_reason: typing.Optional[str] = None
    """Reason for invalidity of the argument. Will be ``None`` if valid."""


class AbstractArgumentValidator(abc.ABC):
    """
    An abstract class that is the base for all argument validators
    """

    @abc.abstractmethod
    def check(self, name: str, value: typing.Any, field_descriptor: FieldDescriptor) -> ValidationResult:
        """
        Returns a validation bool of the given value and field_descriptor

            Parameters:
                name (str): Name for the field to be used in invalid reason messages.
                value (typing.Any): The value to be validated
                field_descriptor (FieldDescriptor): The protobuf field descriptor of the given value

            Returns:
                result (ValidationResult): validation bool for the given value
        """
        pass


class UUIDBytesValidator(AbstractArgumentValidator):
    """Class that ensures the provided value is a valid UUID"""

    def check(self, name: str, value: typing.Any, field_descriptor: FieldDescriptor) -> ValidationResult:
        try:
            uuid.UUID(bytes=value)
        except (ValueError, TypeError):
            return ValidationResult(False, f"{name} must be a valid UUID")
        return ValidationResult(True)


class NonDefaultValidator(AbstractArgumentValidator):
    """Ensures the provided value is not the default value for this field type"""

    def check(self, name: str, value: typing.Any, field_descriptor: FieldDescriptor) -> ValidationResult:
        if value != field_descriptor.default_value:
            return ValidationResult(True)
        return ValidationResult(False, f"{name} must have non-default value")


class NonEmptyValidator(AbstractArgumentValidator):
    """Ensures the provided value is non-empty"""

    def check(self, name: str, value: typing.Any, field_descriptor: FieldDescriptor) -> ValidationResult:
        if len(value) > 0:
            return ValidationResult(True)
        return ValidationResult(False, f"{name} must be non-empty")


class RegexpValidator(AbstractArgumentValidator):
    """
    Matches the input value against the provided regex.

    Parameters:
        pattern (str): Regexp pattern to match.
    """

    def __init__(self, pattern: str):
        self._pattern = pattern

    def check(self, name: str, value: typing.Any, field_descriptor: FieldDescriptor) -> ValidationResult:
        if re.match(self._pattern, value) is not None:
            return ValidationResult(True)
        return ValidationResult(False, f"{name} must match regexp pattern: {self._pattern}")
