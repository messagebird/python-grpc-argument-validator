import re
import typing


def is_valid_field_path(path: str) -> bool:
    """
    Validates that a field path adheres to the Protobuf 3 language specification

        Parameters
            path (typing.Iterable[str])
                Field path that should be validated
    """
    return re.match(r"^(?:\.|\.?(?:[a-zA-Z][a-zA-Z_0-9]*\.)*(?:[a-zA-Z][a-zA-Z_0-9]*)(?:\[\])?)$", path) is not None


def validate_field_names(field_names: typing.Iterable[str]):
    """
    Validates that all field names adhere to the Protobuf 3 language specification

        Parameters
            field_names (typing.Iterable[str])
                All field names that should be validated
        Raises
            ValueError: when a field name is not valid
    """
    for field_name in field_names:
        if not is_valid_field_path(field_name):
            raise ValueError(
                f"Field name {field_name} does not adhere to Protobuf 3 language specification, "
                f"may be prepended with '.' or appended with '[]'. Alternatively, '.' should be used for "
                f"performing validations on the 'root' proto."
            )
