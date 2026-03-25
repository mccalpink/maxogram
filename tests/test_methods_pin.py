"""Тесты для methods/pin.py — методы закреплённых сообщений."""

from __future__ import annotations

from maxogram.methods.pin import GetPinnedMessage, PinMessage, UnpinMessage
from maxogram.types.misc import GetPinnedMessageResult, SimpleQueryResult


class TestGetPinnedMessage:
    """Тесты GET /chats/{chatId}/pin."""

    def test_metadata(self) -> None:
        assert GetPinnedMessage.__api_path__ == "/chats/{chatId}/pin"
        assert GetPinnedMessage.__http_method__ == "GET"
        assert GetPinnedMessage.__returning__ is GetPinnedMessageResult
        assert GetPinnedMessage.__path_params__ == {"chat_id": "chatId"}
        assert GetPinnedMessage.__query_params__ == set()

    def test_create(self) -> None:
        method = GetPinnedMessage(chat_id=123)
        assert method.chat_id == 123

    def test_body_serialization(self) -> None:
        """Body не должен содержать path-параметры."""
        method = GetPinnedMessage(chat_id=123)
        body = method.model_dump(
            exclude=method.__query_params__ | set(method.__path_params__),
            exclude_none=True,
        )
        assert body == {}
        assert "chat_id" not in body


class TestPinMessage:
    """Тесты PUT /chats/{chatId}/pin."""

    def test_metadata(self) -> None:
        assert PinMessage.__api_path__ == "/chats/{chatId}/pin"
        assert PinMessage.__http_method__ == "PUT"
        assert PinMessage.__returning__ is SimpleQueryResult
        assert PinMessage.__path_params__ == {"chat_id": "chatId"}
        assert PinMessage.__query_params__ == set()

    def test_create(self) -> None:
        method = PinMessage(chat_id=100, message_id="mid_abc")
        assert method.chat_id == 100
        assert method.message_id == "mid_abc"
        assert method.notify is True

    def test_create_no_notify(self) -> None:
        method = PinMessage(chat_id=100, message_id="mid_abc", notify=False)
        assert method.notify is False

    def test_body_serialization(self) -> None:
        """Body содержит message_id и notify, но НЕ chat_id."""
        method = PinMessage(chat_id=100, message_id="mid_abc", notify=False)
        body = method.model_dump(
            exclude=method.__query_params__ | set(method.__path_params__),
            exclude_none=True,
        )
        assert body == {"message_id": "mid_abc", "notify": False}
        assert "chat_id" not in body

    def test_body_default_notify(self) -> None:
        """При notify=True значение присутствует в body."""
        method = PinMessage(chat_id=100, message_id="mid_abc")
        body = method.model_dump(
            exclude=method.__query_params__ | set(method.__path_params__),
            exclude_none=True,
        )
        assert body == {"message_id": "mid_abc", "notify": True}


class TestUnpinMessage:
    """Тесты DELETE /chats/{chatId}/pin."""

    def test_metadata(self) -> None:
        assert UnpinMessage.__api_path__ == "/chats/{chatId}/pin"
        assert UnpinMessage.__http_method__ == "DELETE"
        assert UnpinMessage.__returning__ is SimpleQueryResult
        assert UnpinMessage.__path_params__ == {"chat_id": "chatId"}
        assert UnpinMessage.__query_params__ == set()

    def test_create(self) -> None:
        method = UnpinMessage(chat_id=456)
        assert method.chat_id == 456

    def test_body_serialization(self) -> None:
        """Body не должен содержать path-параметры."""
        method = UnpinMessage(chat_id=456)
        body = method.model_dump(
            exclude=method.__query_params__ | set(method.__path_params__),
            exclude_none=True,
        )
        assert body == {}
        assert "chat_id" not in body
