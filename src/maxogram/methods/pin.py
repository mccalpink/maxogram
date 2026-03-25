"""Методы закреплённых сообщений — /chats/{chatId}/pin."""

from __future__ import annotations

from typing import ClassVar

from maxogram.methods.base import MaxMethod
from maxogram.types.misc import GetPinnedMessageResult, SimpleQueryResult


class GetPinnedMessage(MaxMethod["GetPinnedMessageResult"]):
    """GET /chats/{chatId}/pin — Закреплённое сообщение."""

    __api_path__: ClassVar[str] = "/chats/{chatId}/pin"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = GetPinnedMessageResult
    __path_params__: ClassVar[dict[str, str]] = {"chat_id": "chatId"}

    chat_id: int


class PinMessage(MaxMethod["SimpleQueryResult"]):
    """PUT /chats/{chatId}/pin — Закрепить сообщение."""

    __api_path__: ClassVar[str] = "/chats/{chatId}/pin"
    __http_method__: ClassVar[str] = "PUT"
    __returning__: ClassVar[type] = SimpleQueryResult
    __path_params__: ClassVar[dict[str, str]] = {"chat_id": "chatId"}

    chat_id: int
    message_id: str
    notify: bool = True


class UnpinMessage(MaxMethod["SimpleQueryResult"]):
    """DELETE /chats/{chatId}/pin — Открепить сообщение."""

    __api_path__: ClassVar[str] = "/chats/{chatId}/pin"
    __http_method__: ClassVar[str] = "DELETE"
    __returning__: ClassVar[type] = SimpleQueryResult
    __path_params__: ClassVar[dict[str, str]] = {"chat_id": "chatId"}

    chat_id: int
