"""Тесты для methods/member.py — методы участников чата."""

from __future__ import annotations

from maxogram.methods.member import (
    AddAdmins,
    AddMembers,
    GetAdmins,
    GetMembers,
    GetMembership,
    RemoveMember,
)
from maxogram.types.chat import ChatMember, ChatMembersList
from maxogram.types.misc import SimpleQueryResult


class TestGetMembers:
    """Тесты GET /chats/{chatId}/members."""

    def test_metadata(self) -> None:
        assert GetMembers.__api_path__ == "/chats/{chatId}/members"
        assert GetMembers.__http_method__ == "GET"
        assert GetMembers.__returning__ is ChatMembersList
        assert GetMembers.__path_params__ == {"chat_id": "chatId"}
        assert GetMembers.__query_params__ == {"user_ids", "marker", "count"}

    def test_create(self) -> None:
        method = GetMembers(chat_id=10)
        assert method.chat_id == 10
        assert method.user_ids is None
        assert method.marker is None
        assert method.count is None

    def test_create_with_optionals(self) -> None:
        method = GetMembers(chat_id=10, user_ids=[1, 2], marker=5, count=20)
        assert method.user_ids == [1, 2]
        assert method.marker == 5
        assert method.count == 20

    def test_body_serialization(self) -> None:
        """Body не содержит query_params и path_params."""
        method = GetMembers(chat_id=10, user_ids=[1, 2], marker=5, count=20)
        body = method.model_dump(
            exclude=method.__query_params__ | set(method.__path_params__),
            exclude_none=True,
        )
        assert body == {}
        assert "chat_id" not in body
        assert "user_ids" not in body
        assert "marker" not in body
        assert "count" not in body

    def test_body_serialization_defaults(self) -> None:
        """При None-полях и exclude_none body тоже пуст."""
        method = GetMembers(chat_id=10)
        body = method.model_dump(
            exclude=method.__query_params__ | set(method.__path_params__),
            exclude_none=True,
        )
        assert body == {}


class TestAddMembers:
    """Тесты POST /chats/{chatId}/members."""

    def test_metadata(self) -> None:
        assert AddMembers.__api_path__ == "/chats/{chatId}/members"
        assert AddMembers.__http_method__ == "POST"
        assert AddMembers.__returning__ is SimpleQueryResult
        assert AddMembers.__path_params__ == {"chat_id": "chatId"}
        assert AddMembers.__query_params__ == set()

    def test_create(self) -> None:
        method = AddMembers(chat_id=10, user_ids=[100, 200])
        assert method.chat_id == 10
        assert method.user_ids == [100, 200]

    def test_body_serialization(self) -> None:
        """Body содержит user_ids, но НЕ chat_id."""
        method = AddMembers(chat_id=10, user_ids=[100, 200])
        body = method.model_dump(
            exclude=method.__query_params__ | set(method.__path_params__),
            exclude_none=True,
        )
        assert body == {"user_ids": [100, 200]}
        assert "chat_id" not in body


class TestRemoveMember:
    """Тесты DELETE /chats/{chatId}/members."""

    def test_metadata(self) -> None:
        assert RemoveMember.__api_path__ == "/chats/{chatId}/members"
        assert RemoveMember.__http_method__ == "DELETE"
        assert RemoveMember.__returning__ is SimpleQueryResult
        assert RemoveMember.__path_params__ == {"chat_id": "chatId"}
        assert RemoveMember.__query_params__ == {"user_id", "block"}

    def test_create(self) -> None:
        method = RemoveMember(chat_id=10, user_id=999)
        assert method.chat_id == 10
        assert method.user_id == 999
        assert method.block is None

    def test_create_with_block(self) -> None:
        method = RemoveMember(chat_id=10, user_id=999, block=True)
        assert method.block is True

    def test_body_serialization(self) -> None:
        """Body не содержит query_params (user_id, block) и path_params (chat_id)."""
        method = RemoveMember(chat_id=10, user_id=999, block=True)
        body = method.model_dump(
            exclude=method.__query_params__ | set(method.__path_params__),
            exclude_none=True,
        )
        assert body == {}
        assert "chat_id" not in body
        assert "user_id" not in body
        assert "block" not in body


class TestGetMembership:
    """Тесты GET /chats/{chatId}/members/me."""

    def test_metadata(self) -> None:
        assert GetMembership.__api_path__ == "/chats/{chatId}/members/me"
        assert GetMembership.__http_method__ == "GET"
        assert GetMembership.__returning__ is ChatMember
        assert GetMembership.__path_params__ == {"chat_id": "chatId"}
        assert GetMembership.__query_params__ == set()

    def test_create(self) -> None:
        method = GetMembership(chat_id=42)
        assert method.chat_id == 42

    def test_body_serialization(self) -> None:
        """Body пуст — только path-параметры."""
        method = GetMembership(chat_id=42)
        body = method.model_dump(
            exclude=method.__query_params__ | set(method.__path_params__),
            exclude_none=True,
        )
        assert body == {}


class TestGetAdmins:
    """Тесты GET /chats/{chatId}/members/admins."""

    def test_metadata(self) -> None:
        assert GetAdmins.__api_path__ == "/chats/{chatId}/members/admins"
        assert GetAdmins.__http_method__ == "GET"
        assert GetAdmins.__returning__ is ChatMembersList
        assert GetAdmins.__path_params__ == {"chat_id": "chatId"}
        assert GetAdmins.__query_params__ == set()

    def test_create(self) -> None:
        method = GetAdmins(chat_id=77)
        assert method.chat_id == 77

    def test_body_serialization(self) -> None:
        """Body пуст — только path-параметры."""
        method = GetAdmins(chat_id=77)
        body = method.model_dump(
            exclude=method.__query_params__ | set(method.__path_params__),
            exclude_none=True,
        )
        assert body == {}


class TestAddAdmins:
    """Тесты POST /chats/{chatId}/members/admins."""

    def test_metadata(self) -> None:
        assert AddAdmins.__api_path__ == "/chats/{chatId}/members/admins"
        assert AddAdmins.__http_method__ == "POST"
        assert AddAdmins.__returning__ is SimpleQueryResult
        assert AddAdmins.__path_params__ == {"chat_id": "chatId"}
        assert AddAdmins.__query_params__ == set()

    def test_create(self) -> None:
        method = AddAdmins(chat_id=77, user_ids=[10, 20])
        assert method.chat_id == 77
        assert method.user_ids == [10, 20]

    def test_body_serialization(self) -> None:
        """Body содержит user_ids, но НЕ chat_id."""
        method = AddAdmins(chat_id=77, user_ids=[10, 20])
        body = method.model_dump(
            exclude=method.__query_params__ | set(method.__path_params__),
            exclude_none=True,
        )
        assert body == {"user_ids": [10, 20]}
        assert "chat_id" not in body
