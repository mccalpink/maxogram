"""Методы сообщений — /messages."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from maxogram.enums import TextFormat
from maxogram.methods.base import MaxMethod
from maxogram.types.attachment import AttachmentRequest
from maxogram.types.message import Message, MessageList, NewMessageLink, SendMessageResult
from maxogram.types.misc import SimpleQueryResult


class SendMessage(MaxMethod["SendMessageResult"]):
    """POST /messages — Отправка сообщения."""

    __api_path__: ClassVar[str] = "/messages"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = SendMessageResult
    __query_params__: ClassVar[frozenset[str]] = frozenset(
        {"chat_id", "user_id", "disable_link_preview"},
    )

    chat_id: int | None = None
    user_id: int | None = None
    disable_link_preview: bool | None = None
    text: str | None = None
    attachments: list[AttachmentRequest] | None = None
    link: NewMessageLink | None = None
    notify: bool = True
    format: TextFormat | None = None


class EditMessage(MaxMethod["SimpleQueryResult"]):
    """PUT /messages — Редактирование сообщения."""

    __api_path__: ClassVar[str] = "/messages"
    __http_method__: ClassVar[str] = "PUT"
    __returning__: ClassVar[type] = SimpleQueryResult
    __query_params__: ClassVar[frozenset[str]] = frozenset({"message_id"})

    message_id: str
    text: str | None = None
    attachments: list[AttachmentRequest] | None = None
    link: NewMessageLink | None = None
    notify: bool = True
    format: TextFormat | None = None


class DeleteMessage(MaxMethod["SimpleQueryResult"]):
    """DELETE /messages — Удаление сообщения."""

    __api_path__: ClassVar[str] = "/messages"
    __http_method__: ClassVar[str] = "DELETE"
    __returning__: ClassVar[type] = SimpleQueryResult
    __query_params__: ClassVar[frozenset[str]] = frozenset({"message_id"})

    message_id: str


class GetMessages(MaxMethod["MessageList"]):
    """GET /messages — Получение сообщений."""

    __api_path__: ClassVar[str] = "/messages"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = MessageList
    __query_params__: ClassVar[frozenset[str]] = frozenset(
        {"chat_id", "message_ids", "from_", "to", "count"},
    )

    chat_id: int | None = None
    message_ids: list[str] | None = None
    from_: int | None = Field(None, alias="from")
    to: int | None = None
    count: int | None = None


class GetMessageById(MaxMethod["Message"]):
    """GET /messages/{messageId} — Сообщение по ID."""

    __api_path__: ClassVar[str] = "/messages/{messageId}"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = Message
    __path_params__: ClassVar[dict[str, str]] = {"message_id": "messageId"}

    message_id: str
