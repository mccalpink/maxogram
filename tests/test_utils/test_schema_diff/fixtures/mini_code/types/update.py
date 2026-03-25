from __future__ import annotations

from typing import Annotated, Union

from pydantic import Field

from .base import MaxObject


class MessageCreatedUpdate(MaxObject):
    update_type: str = "message_created"
    timestamp: int
    message: Message  # noqa: F821


class BotStartedUpdate(MaxObject):
    update_type: str = "bot_started"
    timestamp: int
    user: User  # noqa: F821


Update = Annotated[
    Union[MessageCreatedUpdate, BotStartedUpdate],
    Field(discriminator="update_type"),
]
