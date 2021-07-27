import typing
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """
    Contains results for validation check.
    """

    valid: bool
    """Whether the argument was valid."""

    invalid_reason: typing.Optional[str] = None
    """Reason for invalidity of the argument. Will be ``None`` if valid."""
