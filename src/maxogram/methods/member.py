"""Методы участников чата — /chats/{chatId}/members."""

from __future__ import annotations

from typing import ClassVar

from maxogram.methods.base import MaxMethod
from maxogram.types.chat import ChatMember, ChatMembersList
from maxogram.types.misc import SimpleQueryResult


class GetMembers(MaxMethod["ChatMembersList"]):
    """GET /chats/{chatId}/members — Список участников."""

    __api_path__: ClassVar[str] = "/chats/{chatId}/members"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = ChatMembersList
    __path_params__: ClassVar[dict[str, str]] = {"chat_id": "chatId"}
    __query_params__: ClassVar[frozenset[str]] = frozenset({"user_ids", "marker", "count"})

    chat_id: int
    user_ids: list[int] | None = None
    marker: int | None = None
    count: int | None = None


class AddMembers(MaxMethod["SimpleQueryResult"]):
    """POST /chats/{chatId}/members — Добавить участников."""

    __api_path__: ClassVar[str] = "/chats/{chatId}/members"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = SimpleQueryResult
    __path_params__: ClassVar[dict[str, str]] = {"chat_id": "chatId"}

    chat_id: int
    user_ids: list[int]


class RemoveMember(MaxMethod["SimpleQueryResult"]):
    """DELETE /chats/{chatId}/members — Удалить участника."""

    __api_path__: ClassVar[str] = "/chats/{chatId}/members"
    __http_method__: ClassVar[str] = "DELETE"
    __returning__: ClassVar[type] = SimpleQueryResult
    __path_params__: ClassVar[dict[str, str]] = {"chat_id": "chatId"}
    __query_params__: ClassVar[frozenset[str]] = frozenset({"user_id", "block"})

    chat_id: int
    user_id: int
    block: bool | None = None


class GetMembership(MaxMethod["ChatMember"]):
    """GET /chats/{chatId}/members/me — Членство бота."""

    __api_path__: ClassVar[str] = "/chats/{chatId}/members/me"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = ChatMember
    __path_params__: ClassVar[dict[str, str]] = {"chat_id": "chatId"}

    chat_id: int


class GetAdmins(MaxMethod["ChatMembersList"]):
    """GET /chats/{chatId}/members/admins — Администраторы."""

    __api_path__: ClassVar[str] = "/chats/{chatId}/members/admins"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = ChatMembersList
    __path_params__: ClassVar[dict[str, str]] = {"chat_id": "chatId"}

    chat_id: int


class AddAdmins(MaxMethod["SimpleQueryResult"]):
    """POST /chats/{chatId}/members/admins — Назначить администраторов."""

    __api_path__: ClassVar[str] = "/chats/{chatId}/members/admins"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = SimpleQueryResult
    __path_params__: ClassVar[dict[str, str]] = {"chat_id": "chatId"}

    chat_id: int
    user_ids: list[int]
