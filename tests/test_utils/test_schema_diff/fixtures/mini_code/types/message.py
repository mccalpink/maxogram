from __future__ import annotations

from pydantic import Field

from .base import MaxObject


class Message(MaxObject):
    sender: User  # noqa: F821
    text: str | None = None
    timestamp: int
    from_: int | None = Field(default=None, alias="from")
