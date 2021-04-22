import abc
import re
import typing
import uuid

from google.protobuf.descriptor import FieldDescriptor


class AbstractArgumentValidator(abc.ABC):
    """
    An abstract class that is the base for all argument validators
    """

    @abc.abstractmethod
    def is_valid(self, value: typing.Any, field_descriptor: FieldDescriptor) -> bool:
        """
        Returns a validation bool of the given value and field_descriptor

            Parameters:
                value (typing.Any): The value to be validated
                field_descriptor (FieldDescriptor): The protobuf field descriptor of the given value

            Returns:
                is_valid (bool): validation bool for the given value
        """
        pass

    @abc.abstractmethod
    def invalid_message(self, name: str) -> str:
        """
        Returns a validation message for the given field name

            Parameters:
                name (str): Name of the validated field

            Returns:
                message (str): message describing the constraints of the validator
        """
        pass


class UUIDBytesValidator(AbstractArgumentValidator):
    """Class that ensures the provided value is a valid UUID"""

    def is_valid(self, value: typing.Any, field_descriptor: FieldDescriptor) -> bool:
        try:
            uuid.UUID(bytes=value)
        except (ValueError, TypeError):
            return False
        return True

    def invalid_message(self, name: str) -> str:
        return f"{name} must be a valid UUID"


class NonDefaultValidator(AbstractArgumentValidator):
    """Ensures the provided value is not the default value for this field type"""

    def is_valid(self, value: typing.Any, field_descriptor: FieldDescriptor) -> bool:
        return value != field_descriptor.default_value

    def invalid_message(self, name: str) -> str:
        return f"{name} must have non-default value"


class NonEmptyValidator(AbstractArgumentValidator):
    """Ensures the provided value is non-empty"""

    def is_valid(self, value: typing.Any, field_descriptor: FieldDescriptor) -> bool:
        return len(value) > 0

    def invalid_message(self, name: str) -> str:
        return f"{name} must be non-empty"


class RegexpValidator(AbstractArgumentValidator):
    """Matches the input value against the provided regex"""

    def __init__(self, pattern: str):
        self._pattern = pattern

    def is_valid(self, value: typing.Any, field_descriptor: FieldDescriptor) -> bool:
        return re.match(self._pattern, value) is not None

    def invalid_message(self, name: str) -> str:
        return f"{name} must match regexp pattern: {self._pattern}"
