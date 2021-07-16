import re


def is_valid_field_path(path: str):
    return re.match(r"^(?:\.|\.?(?:[a-zA-Z][a-zA-Z_0-9]*\.)*(?:[a-zA-Z][a-zA-Z_0-9]*)(?:\[\])?)$", path) is not None
