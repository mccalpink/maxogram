"""Методы Chat API — /chats."""

from __future__ import annotations

from typing import ClassVar

from maxogram.enums import SenderAction
from maxogram.methods.base import MaxMethod
from maxogram.types.chat import Chat, ChatList
from maxogram.types.misc import PhotoAttachmentRequestPayload, SimpleQueryResult


class GetChats(MaxMethod["ChatList"]):
    """GET /chats — Список чатов бота."""

    __api_path__: ClassVar[str] = "/chats"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = ChatList
    __query_params__: ClassVar[frozenset[str]] = frozenset({"count", "marker"})

    count: int | None = None
    marker: int | None = None


class GetChat(MaxMethod["Chat"]):
    """GET /chats/{chatId} — Информация о чате."""

    __api_path__: ClassVar[str] = "/chats/{chatId}"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = Chat
    __path_params__: ClassVar[dict[str, str]] = {"chat_id": "chatId"}

    chat_id: int


class GetChatByLink(MaxMethod["Chat"]):
    """GET /chats/{chatLink} — Чат по публичной ссылке."""

    __api_path__: ClassVar[str] = "/chats/{chatLink}"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = Chat
    __path_params__: ClassVar[dict[str, str]] = {"chat_link": "chatLink"}

    chat_link: str


class EditChat(MaxMethod["Chat"]):
    """PATCH /chats/{chatId} — Редактирование чата."""

    __api_path__: ClassVar[str] = "/chats/{chatId}"
    __http_method__: ClassVar[str] = "PATCH"
    __returning__: ClassVar[type] = Chat
    __path_params__: ClassVar[dict[str, str]] = {"chat_id": "chatId"}

    chat_id: int
    icon: PhotoAttachmentRequestPayload | None = None
    title: str | None = None
    pin: str | None = None
    notify: bool | None = None


class DeleteChat(MaxMethod["SimpleQueryResult"]):
    """DELETE /chats/{chatId} — Удаление чата."""

    __api_path__: ClassVar[str] = "/chats/{chatId}"
    __http_method__: ClassVar[str] = "DELETE"
    __returning__: ClassVar[type] = SimpleQueryResult
    __path_params__: ClassVar[dict[str, str]] = {"chat_id": "chatId"}

    chat_id: int


class SendAction(MaxMethod["SimpleQueryResult"]):
    """POST /chats/{chatId}/actions — Отправка действия в чат."""

    __api_path__: ClassVar[str] = "/chats/{chatId}/actions"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = SimpleQueryResult
    __path_params__: ClassVar[dict[str, str]] = {"chat_id": "chatId"}

    chat_id: int
    action: SenderAction


class LeaveChat(MaxMethod["SimpleQueryResult"]):
    """DELETE /chats/{chatId}/members/me — Выход бота из чата."""

    __api_path__: ClassVar[str] = "/chats/{chatId}/members/me"
    __http_method__: ClassVar[str] = "DELETE"
    __returning__: ClassVar[type] = SimpleQueryResult
    __path_params__: ClassVar[dict[str, str]] = {"chat_id": "chatId"}

    chat_id: int
