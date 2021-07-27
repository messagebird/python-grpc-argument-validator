import typing
from dataclasses import dataclass


@dataclass
class ValidationContext:
    """
    Contains extra information about the request while validating.
    """

    is_streaming: bool = False
    """Whether the request is part of a streaming request."""

    streaming_message_index: typing.Optional[int] = None
    """If the request is a streaming request, the index of the current streamed message"""
