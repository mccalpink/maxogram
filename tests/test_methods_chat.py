"""Тесты для methods/chat.py."""

from __future__ import annotations

from maxogram.enums import SenderAction
from maxogram.methods.chat import (
    DeleteChat,
    EditChat,
    GetChat,
    GetChatByLink,
    GetChats,
    LeaveChat,
    SendAction,
)
from maxogram.types.chat import Chat, ChatList
from maxogram.types.misc import SimpleQueryResult

# ---------------------------------------------------------------------------
# GetChats
# ---------------------------------------------------------------------------


class TestGetChats:
    """Тесты GET /chats — список чатов бота."""

    def test_metadata(self) -> None:
        assert GetChats.__api_path__ == "/chats"
        assert GetChats.__http_method__ == "GET"
        assert GetChats.__returning__ is ChatList
        assert GetChats.__query_params__ == {"count", "marker"}
        assert GetChats.__path_params__ == {}

    def test_create_empty(self) -> None:
        m = GetChats()
        assert m.count is None
        assert m.marker is None

    def test_create_with_params(self) -> None:
        m = GetChats(count=50, marker=100)
        assert m.count == 50
        assert m.marker == 100

    def test_body_empty(self) -> None:
        """GET — query-поля исключаются из body."""
        m = GetChats(count=50, marker=100)
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}


# ---------------------------------------------------------------------------
# GetChat
# ---------------------------------------------------------------------------


class TestGetChat:
    """Тесты GET /chats/{chatId} — информация о чате."""

    def test_metadata(self) -> None:
        assert GetChat.__api_path__ == "/chats/{chatId}"
        assert GetChat.__http_method__ == "GET"
        assert GetChat.__returning__ is Chat
        assert GetChat.__path_params__ == {"chat_id": "chatId"}
        assert GetChat.__query_params__ == set()

    def test_create(self) -> None:
        m = GetChat(chat_id=12345)
        assert m.chat_id == 12345

    def test_body_empty(self) -> None:
        """GET с path_params — body пуст."""
        m = GetChat(chat_id=12345)
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}

    def test_path_mapping(self) -> None:
        """Маппинг python_field → API path param."""
        assert "chat_id" in GetChat.__path_params__
        assert GetChat.__path_params__["chat_id"] == "chatId"


# ---------------------------------------------------------------------------
# GetChatByLink
# ---------------------------------------------------------------------------


class TestGetChatByLink:
    """Тесты GET /chats/{chatLink} — чат по публичной ссылке."""

    def test_metadata(self) -> None:
        assert GetChatByLink.__api_path__ == "/chats/{chatLink}"
        assert GetChatByLink.__http_method__ == "GET"
        assert GetChatByLink.__returning__ is Chat
        assert GetChatByLink.__path_params__ == {"chat_link": "chatLink"}
        assert GetChatByLink.__query_params__ == set()

    def test_create(self) -> None:
        m = GetChatByLink(chat_link="my_public_chat")
        assert m.chat_link == "my_public_chat"

    def test_body_empty(self) -> None:
        """GET с path_params — body пуст."""
        m = GetChatByLink(chat_link="my_public_chat")
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}

    def test_path_mapping(self) -> None:
        assert GetChatByLink.__path_params__["chat_link"] == "chatLink"


# ---------------------------------------------------------------------------
# EditChat
# ---------------------------------------------------------------------------


class TestEditChat:
    """Тесты PATCH /chats/{chatId} — редактирование чата."""

    def test_metadata(self) -> None:
        assert EditChat.__api_path__ == "/chats/{chatId}"
        assert EditChat.__http_method__ == "PATCH"
        assert EditChat.__returning__ is Chat
        assert EditChat.__path_params__ == {"chat_id": "chatId"}
        assert EditChat.__query_params__ == set()

    def test_create_minimal(self) -> None:
        """Только обязательное поле chat_id."""
        m = EditChat(chat_id=999)
        assert m.chat_id == 999
        assert m.icon is None
        assert m.title is None
        assert m.pin is None
        assert m.notify is None

    def test_create_with_all(self) -> None:
        m = EditChat(
            chat_id=999,
            title="Новый чат",
            pin="msg_123",
            notify=True,
        )
        assert m.title == "Новый чат"
        assert m.pin == "msg_123"
        assert m.notify is True

    def test_body_excludes_path_params(self) -> None:
        """chat_id не попадает в body (он в path)."""
        m = EditChat(chat_id=999, title="Новый чат")
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert "chat_id" not in body
        assert body == {"title": "Новый чат"}

    def test_body_none_excluded(self) -> None:
        """None-поля не попадают в body."""
        m = EditChat(chat_id=999)
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}

    def test_path_mapping(self) -> None:
        assert EditChat.__path_params__["chat_id"] == "chatId"


# ---------------------------------------------------------------------------
# DeleteChat
# ---------------------------------------------------------------------------


class TestDeleteChat:
    """Тесты DELETE /chats/{chatId} — удаление чата."""

    def test_metadata(self) -> None:
        assert DeleteChat.__api_path__ == "/chats/{chatId}"
        assert DeleteChat.__http_method__ == "DELETE"
        assert DeleteChat.__returning__ is SimpleQueryResult
        assert DeleteChat.__path_params__ == {"chat_id": "chatId"}
        assert DeleteChat.__query_params__ == set()

    def test_create(self) -> None:
        m = DeleteChat(chat_id=555)
        assert m.chat_id == 555

    def test_body_empty(self) -> None:
        """DELETE с path_params — body пуст."""
        m = DeleteChat(chat_id=555)
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}

    def test_path_mapping(self) -> None:
        assert DeleteChat.__path_params__["chat_id"] == "chatId"


# ---------------------------------------------------------------------------
# SendAction
# ---------------------------------------------------------------------------


class TestSendAction:
    """Тесты POST /chats/{chatId}/actions — отправка действия."""

    def test_metadata(self) -> None:
        assert SendAction.__api_path__ == "/chats/{chatId}/actions"
        assert SendAction.__http_method__ == "POST"
        assert SendAction.__returning__ is SimpleQueryResult
        assert SendAction.__path_params__ == {"chat_id": "chatId"}
        assert SendAction.__query_params__ == set()

    def test_create(self) -> None:
        m = SendAction(chat_id=123, action=SenderAction.TYPING_ON)
        assert m.chat_id == 123
        assert m.action == SenderAction.TYPING_ON

    def test_body_contains_action(self) -> None:
        """Body содержит action, но не chat_id."""
        m = SendAction(chat_id=123, action=SenderAction.SENDING_PHOTO)
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert "chat_id" not in body
        assert body == {"action": "sending_photo"}

    def test_action_values(self) -> None:
        """Все типы действий корректно сериализуются."""
        for action in SenderAction:
            m = SendAction(chat_id=1, action=action)
            exclude = m.__query_params__ | set(m.__path_params__)
            body = m.model_dump(exclude=exclude, exclude_none=True)
            assert body["action"] == action.value

    def test_path_mapping(self) -> None:
        assert SendAction.__path_params__["chat_id"] == "chatId"


# ---------------------------------------------------------------------------
# LeaveChat
# ---------------------------------------------------------------------------


class TestLeaveChat:
    """Тесты DELETE /chats/{chatId}/members/me — выход бота."""

    def test_metadata(self) -> None:
        assert LeaveChat.__api_path__ == "/chats/{chatId}/members/me"
        assert LeaveChat.__http_method__ == "DELETE"
        assert LeaveChat.__returning__ is SimpleQueryResult
        assert LeaveChat.__path_params__ == {"chat_id": "chatId"}
        assert LeaveChat.__query_params__ == set()

    def test_create(self) -> None:
        m = LeaveChat(chat_id=777)
        assert m.chat_id == 777

    def test_body_empty(self) -> None:
        """DELETE — body пуст."""
        m = LeaveChat(chat_id=777)
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}

    def test_path_mapping(self) -> None:
        assert LeaveChat.__path_params__["chat_id"] == "chatId"
