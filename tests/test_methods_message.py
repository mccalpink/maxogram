"""Тесты для methods/message.py."""

from __future__ import annotations

from maxogram.enums import MessageLinkType, TextFormat
from maxogram.methods.message import (
    DeleteMessage,
    EditMessage,
    GetMessageById,
    GetMessages,
    SendMessage,
)
from maxogram.types.message import Message, MessageList, NewMessageLink, SendMessageResult
from maxogram.types.misc import SimpleQueryResult


class TestSendMessage:
    """Тесты POST /messages — отправка сообщения."""

    def test_metadata(self) -> None:
        assert SendMessage.__api_path__ == "/messages"
        assert SendMessage.__http_method__ == "POST"
        assert SendMessage.__returning__ is SendMessageResult
        assert SendMessage.__query_params__ == {"chat_id", "user_id", "disable_link_preview"}
        assert SendMessage.__path_params__ == {}

    def test_create_minimal(self) -> None:
        """Создание с минимальными параметрами."""
        m = SendMessage(text="Привет")
        assert m.text == "Привет"
        assert m.chat_id is None
        assert m.user_id is None
        assert m.disable_link_preview is None
        assert m.notify is True
        assert m.format is None
        assert m.attachments is None
        assert m.link is None

    def test_create_with_all_fields(self) -> None:
        """Создание со всеми полями."""
        link = NewMessageLink(type=MessageLinkType.REPLY, mid="mid.abc")
        m = SendMessage(
            chat_id=123,
            user_id=456,
            disable_link_preview=True,
            text="Текст",
            link=link,
            notify=False,
            format=TextFormat.HTML,
        )
        assert m.chat_id == 123
        assert m.user_id == 456
        assert m.disable_link_preview is True
        assert m.text == "Текст"
        assert m.link is not None
        assert m.notify is False
        assert m.format == TextFormat.HTML

    def test_body_excludes_query_params(self) -> None:
        """Body содержит text, notify, format — но НЕ chat_id/user_id/disable_link_preview."""
        m = SendMessage(
            chat_id=1,
            user_id=2,
            disable_link_preview=True,
            text="Привет",
            notify=True,
            format=TextFormat.MARKDOWN,
        )
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        # Должны быть в body
        assert "text" in body
        assert "notify" in body
        assert "format" in body
        # НЕ должны быть в body
        assert "chat_id" not in body
        assert "user_id" not in body
        assert "disable_link_preview" not in body

    def test_body_excludes_none(self) -> None:
        """Поля со значением None не попадают в body."""
        m = SendMessage(text="Тест")
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert "text" in body
        assert "attachments" not in body
        assert "link" not in body
        assert "format" not in body


class TestEditMessage:
    """Тесты PUT /messages — редактирование сообщения."""

    def test_metadata(self) -> None:
        assert EditMessage.__api_path__ == "/messages"
        assert EditMessage.__http_method__ == "PUT"
        assert EditMessage.__returning__ is SimpleQueryResult
        assert EditMessage.__query_params__ == {"message_id"}
        assert EditMessage.__path_params__ == {}

    def test_create(self) -> None:
        m = EditMessage(message_id="mid.123", text="Новый текст")
        assert m.message_id == "mid.123"
        assert m.text == "Новый текст"

    def test_body_excludes_query_params(self) -> None:
        """message_id — query param, не попадает в body."""
        m = EditMessage(message_id="mid.123", text="Текст", format=TextFormat.HTML)
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert "message_id" not in body
        assert "text" in body
        assert "format" in body

    def test_defaults(self) -> None:
        """Проверка значений по умолчанию."""
        m = EditMessage(message_id="mid.1")
        assert m.text is None
        assert m.attachments is None
        assert m.link is None
        assert m.notify is True
        assert m.format is None


class TestDeleteMessage:
    """Тесты DELETE /messages — удаление сообщения."""

    def test_metadata(self) -> None:
        assert DeleteMessage.__api_path__ == "/messages"
        assert DeleteMessage.__http_method__ == "DELETE"
        assert DeleteMessage.__returning__ is SimpleQueryResult
        assert DeleteMessage.__query_params__ == {"message_id"}
        assert DeleteMessage.__path_params__ == {}

    def test_create(self) -> None:
        m = DeleteMessage(message_id="mid.999")
        assert m.message_id == "mid.999"

    def test_body_empty(self) -> None:
        """DELETE — body пуст (message_id уходит в query)."""
        m = DeleteMessage(message_id="mid.999")
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}


class TestGetMessages:
    """Тесты GET /messages — получение сообщений."""

    def test_metadata(self) -> None:
        assert GetMessages.__api_path__ == "/messages"
        assert GetMessages.__http_method__ == "GET"
        assert GetMessages.__returning__ is MessageList
        assert GetMessages.__query_params__ == {
            "chat_id",
            "message_ids",
            "from_",
            "to",
            "count",
        }
        assert GetMessages.__path_params__ == {}

    def test_create_empty(self) -> None:
        """Все поля опциональны."""
        m = GetMessages()
        assert m.chat_id is None
        assert m.message_ids is None
        assert m.from_ is None
        assert m.to is None
        assert m.count is None

    def test_create_with_from(self) -> None:
        """Поле from_ (зарезервированное слово Python)."""
        m = GetMessages(from_=1000, to=2000, count=50)
        assert m.from_ == 1000
        assert m.to == 2000
        assert m.count == 50

    def test_from_alias_dump(self) -> None:
        """model_dump(by_alias=True) даёт ключ 'from', а не 'from_'."""
        m = GetMessages(from_=1000)
        data = m.model_dump(by_alias=True)
        assert "from" in data
        assert "from_" not in data
        assert data["from"] == 1000

    def test_from_alias_populate(self) -> None:
        """Можно создать через alias: GetMessages(**{'from': 1000})."""
        m = GetMessages(**{"from": 1000})  # type: ignore[arg-type]
        assert m.from_ == 1000

    def test_body_empty(self) -> None:
        """GET — все поля в query, body пуст."""
        m = GetMessages(chat_id=1, from_=100, to=200, count=10)
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}


class TestGetMessageById:
    """Тесты GET /messages/{messageId} — сообщение по ID."""

    def test_metadata(self) -> None:
        assert GetMessageById.__api_path__ == "/messages/{messageId}"
        assert GetMessageById.__http_method__ == "GET"
        assert GetMessageById.__returning__ is Message
        assert GetMessageById.__query_params__ == set()
        assert GetMessageById.__path_params__ == {"message_id": "messageId"}

    def test_create(self) -> None:
        m = GetMessageById(message_id="mid.abc123")
        assert m.message_id == "mid.abc123"

    def test_body_excludes_path_params(self) -> None:
        """message_id — path param, не попадает в body."""
        m = GetMessageById(message_id="mid.abc123")
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}
