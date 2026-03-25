"""Типы обновлений (updates) Max API — 13 типов."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from maxogram.types.base import MaxObject
from maxogram.types.callback import Callback
from maxogram.types.message import Message
from maxogram.types.user import User


class MessageCreatedUpdate(MaxObject):
    """Update: новое сообщение."""

    update_type: Literal["message_created"] = "message_created"
    timestamp: int
    message: Message
    user_locale: str | None = None


class MessageCallbackUpdate(MaxObject):
    """Update: нажатие inline-кнопки."""

    update_type: Literal["message_callback"] = "message_callback"
    timestamp: int
    callback: Callback
    message: Message | None = None
    user_locale: str | None = None


class MessageEditedUpdate(MaxObject):
    """Update: сообщение отредактировано."""

    update_type: Literal["message_edited"] = "message_edited"
    timestamp: int
    message: Message
    user_locale: str | None = None


class MessageRemovedUpdate(MaxObject):
    """Update: сообщение удалено."""

    update_type: Literal["message_removed"] = "message_removed"
    timestamp: int
    message_id: str
    chat_id: int | None = None
    user_id: int | None = None
    user_locale: str | None = None


class MessageChatCreatedUpdate(MaxObject):
    """Update: создан чат через ChatButton."""

    update_type: Literal["message_chat_created"] = "message_chat_created"
    timestamp: int
    chat: dict[str, object]
    message_id: str | None = None
    start_payload: str | None = None
    user_locale: str | None = None


class MessageConstructionRequestUpdate(MaxObject):
    """Update: запрос конструктора сообщений."""

    update_type: Literal["message_construction_request"] = "message_construction_request"
    timestamp: int
    user: User
    session_id: str
    data: str | None = None
    input: str | None = None
    user_locale: str | None = None


class MessageConstructedUpdate(MaxObject):
    """Update: конструктор завершил работу."""

    update_type: Literal["message_constructed"] = "message_constructed"
    timestamp: int
    session_id: str
    message: Message | None = None
    user_locale: str | None = None


class BotStartedUpdate(MaxObject):
    """Update: пользователь начал диалог с ботом."""

    update_type: Literal["bot_started"] = "bot_started"
    timestamp: int
    chat_id: int
    user: User
    payload: str | None = None
    user_locale: str | None = None


class BotAddedUpdate(MaxObject):
    """Update: бот добавлен в чат."""

    update_type: Literal["bot_added"] = "bot_added"
    timestamp: int
    chat_id: int
    user: User
    is_channel: bool = False
    user_locale: str | None = None


class BotRemovedUpdate(MaxObject):
    """Update: бот удалён из чата."""

    update_type: Literal["bot_removed"] = "bot_removed"
    timestamp: int
    chat_id: int
    user: User
    is_channel: bool = False
    user_locale: str | None = None


class UserAddedUpdate(MaxObject):
    """Update: пользователь добавлен в чат."""

    update_type: Literal["user_added"] = "user_added"
    timestamp: int
    chat_id: int
    user: User
    inviter_id: int | None = None
    user_locale: str | None = None


class UserRemovedUpdate(MaxObject):
    """Update: пользователь удалён из чата."""

    update_type: Literal["user_removed"] = "user_removed"
    timestamp: int
    chat_id: int
    user: User
    admin_id: int | None = None
    user_locale: str | None = None


class ChatTitleChangedUpdate(MaxObject):
    """Update: изменено название чата."""

    update_type: Literal["chat_title_changed"] = "chat_title_changed"
    timestamp: int
    chat_id: int
    user: User
    title: str
    user_locale: str | None = None


Update = Annotated[
    Union[
        MessageCreatedUpdate,
        MessageCallbackUpdate,
        MessageEditedUpdate,
        MessageRemovedUpdate,
        MessageChatCreatedUpdate,
        MessageConstructionRequestUpdate,
        MessageConstructedUpdate,
        BotStartedUpdate,
        BotAddedUpdate,
        BotRemovedUpdate,
        UserAddedUpdate,
        UserRemovedUpdate,
        ChatTitleChangedUpdate,
    ],
    Field(discriminator="update_type"),
]


class GetUpdatesResult(MaxObject):
    """Результат long polling (GET /updates)."""

    updates: list[Update]
    marker: int | None = None
