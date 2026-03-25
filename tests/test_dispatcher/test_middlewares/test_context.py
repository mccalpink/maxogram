"""Тесты MaxContextMiddleware — извлечение контекста из событий."""

from __future__ import annotations

from typing import Any

import pytest

from maxogram.dispatcher.middlewares.context import EventChat, MaxContextMiddleware
from maxogram.enums import ChatType
from maxogram.types.callback import Callback
from maxogram.types.message import Message, MessageBody, Recipient
from maxogram.types.update import (
    BotAddedUpdate,
    BotRemovedUpdate,
    BotStartedUpdate,
    ChatTitleChangedUpdate,
    MessageCallbackUpdate,
    MessageChatCreatedUpdate,
    MessageConstructedUpdate,
    MessageConstructionRequestUpdate,
    MessageCreatedUpdate,
    MessageEditedUpdate,
    MessageRemovedUpdate,
    UserAddedUpdate,
    UserRemovedUpdate,
)
from maxogram.types.user import User


def _make_user(user_id: int = 1) -> User:
    """Создать тестового пользователя."""
    return User(user_id=user_id, name="Test", is_bot=False, last_activity_time=0)


def _make_message(
    *,
    sender: User | None = None,
    chat_id: int = 100,
) -> Message:
    """Создать тестовое сообщение."""
    return Message(
        sender=sender,
        recipient=Recipient(chat_id=chat_id, chat_type=ChatType.DIALOG),
        timestamp=0,
        body=MessageBody(mid="mid1", seq=1, text="hello"),
    )


async def _capture_handler(event: Any, data: dict[str, Any]) -> dict[str, Any]:
    """Хендлер-заглушка, возвращающий data для проверки."""
    return dict(data)


class TestMaxContextMiddlewareIsBaseMiddleware:
    """MaxContextMiddleware наследует BaseMiddleware."""

    def test_is_subclass(self) -> None:
        from maxogram.dispatcher.middlewares.base import BaseMiddleware

        assert issubclass(MaxContextMiddleware, BaseMiddleware)

    def test_instantiates(self) -> None:
        mw = MaxContextMiddleware()
        assert mw is not None


class TestEventChat:
    """EventChat — frozen dataclass с chat_id."""

    def test_create(self) -> None:
        ec = EventChat(chat_id=42)
        assert ec.chat_id == 42

    def test_frozen(self) -> None:
        ec = EventChat(chat_id=42)
        with pytest.raises(AttributeError):
            ec.chat_id = 99  # type: ignore[misc]


class TestMessageCreated:
    """message_created: user=sender, chat_id=recipient.chat_id."""

    @pytest.mark.asyncio
    async def test_extracts_user_and_chat(self) -> None:
        user = _make_user(user_id=10)
        message = _make_message(sender=user, chat_id=200)
        update = MessageCreatedUpdate(timestamp=0, message=message)

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is user
        assert isinstance(result["event_chat"], EventChat)
        assert result["event_chat"].chat_id == 200


class TestMessageCallback:
    """message_callback: user=callback.user, chat_id от message."""

    @pytest.mark.asyncio
    async def test_with_message(self) -> None:
        user = _make_user(user_id=20)
        callback = Callback(timestamp=0, callback_id="cb1", payload="data", user=user)
        message = _make_message(chat_id=300)
        update = MessageCallbackUpdate(timestamp=0, callback=callback, message=message)

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is user
        assert result["event_chat"].chat_id == 300

    @pytest.mark.asyncio
    async def test_without_message(self) -> None:
        user = _make_user(user_id=21)
        callback = Callback(timestamp=0, callback_id="cb2", user=user)
        update = MessageCallbackUpdate(timestamp=0, callback=callback, message=None)

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is user
        assert result["event_chat"] is None


class TestMessageEdited:
    """message_edited: user=sender, chat_id=recipient.chat_id."""

    @pytest.mark.asyncio
    async def test_extracts_user_and_chat(self) -> None:
        user = _make_user(user_id=30)
        message = _make_message(sender=user, chat_id=400)
        update = MessageEditedUpdate(timestamp=0, message=message)

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is user
        assert result["event_chat"].chat_id == 400


class TestMessageRemoved:
    """message_removed: user=None, chat_id=update.chat_id."""

    @pytest.mark.asyncio
    async def test_extracts_chat_no_user(self) -> None:
        update = MessageRemovedUpdate(timestamp=0, message_id="msg1", chat_id=500, user_id=99)

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is None
        assert result["event_chat"].chat_id == 500

    @pytest.mark.asyncio
    async def test_no_chat_id(self) -> None:
        update = MessageRemovedUpdate(timestamp=0, message_id="msg2", chat_id=None)

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is None
        assert result["event_chat"] is None


class TestMessageChatCreated:
    """message_chat_created: user=None, chat_id из dict."""

    @pytest.mark.asyncio
    async def test_extracts_chat_id_from_dict(self) -> None:
        update = MessageChatCreatedUpdate(
            timestamp=0,
            chat={"chat_id": 600, "type": "dialog"},
        )

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is None
        assert result["event_chat"].chat_id == 600

    @pytest.mark.asyncio
    async def test_chat_dict_without_chat_id(self) -> None:
        update = MessageChatCreatedUpdate(
            timestamp=0,
            chat={"type": "dialog"},
        )

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is None
        assert result["event_chat"] is None


class TestMessageConstructionRequest:
    """message_construction_request: user=update.user, chat_id=None."""

    @pytest.mark.asyncio
    async def test_extracts_user_no_chat(self) -> None:
        user = _make_user(user_id=70)
        update = MessageConstructionRequestUpdate(timestamp=0, user=user, session_id="sess1")

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is user
        assert result["event_chat"] is None


class TestMessageConstructed:
    """message_constructed: user=None, chat_id=None."""

    @pytest.mark.asyncio
    async def test_no_user_no_chat(self) -> None:
        update = MessageConstructedUpdate(timestamp=0, session_id="sess2")

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is None
        assert result["event_chat"] is None


class TestBotStarted:
    """bot_started: user=update.user, chat_id=update.chat_id."""

    @pytest.mark.asyncio
    async def test_extracts_user_and_chat(self) -> None:
        user = _make_user(user_id=80)
        update = BotStartedUpdate(timestamp=0, chat_id=800, user=user)

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is user
        assert result["event_chat"].chat_id == 800


class TestBotAdded:
    """bot_added: user=update.user, chat_id=update.chat_id."""

    @pytest.mark.asyncio
    async def test_extracts_user_and_chat(self) -> None:
        user = _make_user(user_id=81)
        update = BotAddedUpdate(timestamp=0, chat_id=810, user=user)

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is user
        assert result["event_chat"].chat_id == 810


class TestBotRemoved:
    """bot_removed: user=update.user, chat_id=update.chat_id."""

    @pytest.mark.asyncio
    async def test_extracts_user_and_chat(self) -> None:
        user = _make_user(user_id=82)
        update = BotRemovedUpdate(timestamp=0, chat_id=820, user=user)

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is user
        assert result["event_chat"].chat_id == 820


class TestUserAdded:
    """user_added: user=update.user, chat_id=update.chat_id."""

    @pytest.mark.asyncio
    async def test_extracts_user_and_chat(self) -> None:
        user = _make_user(user_id=83)
        update = UserAddedUpdate(timestamp=0, chat_id=830, user=user)

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is user
        assert result["event_chat"].chat_id == 830


class TestUserRemoved:
    """user_removed: user=update.user, chat_id=update.chat_id."""

    @pytest.mark.asyncio
    async def test_extracts_user_and_chat(self) -> None:
        user = _make_user(user_id=84)
        update = UserRemovedUpdate(timestamp=0, chat_id=840, user=user)

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is user
        assert result["event_chat"].chat_id == 840


class TestChatTitleChanged:
    """chat_title_changed: user=update.user, chat_id=update.chat_id."""

    @pytest.mark.asyncio
    async def test_extracts_user_and_chat(self) -> None:
        user = _make_user(user_id=85)
        update = ChatTitleChangedUpdate(timestamp=0, chat_id=850, user=user, title="New Title")

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, update, {})

        assert result["event_from_user"] is user
        assert result["event_chat"].chat_id == 850


class TestUnknownUpdateType:
    """Неизвестный тип: graceful degradation — user=None, chat_id=None."""

    @pytest.mark.asyncio
    async def test_unknown_event_graceful(self) -> None:
        """Объект без update_type — возвращает None, None."""

        class FakeEvent:
            pass

        mw = MaxContextMiddleware()
        result = await mw(_capture_handler, FakeEvent(), {})

        assert result["event_from_user"] is None
        assert result["event_chat"] is None


class TestMiddlewarePassesThrough:
    """Middleware вызывает handler и возвращает его результат."""

    @pytest.mark.asyncio
    async def test_returns_handler_result(self) -> None:
        async def handler(event: Any, data: dict[str, Any]) -> str:
            return "handler_result"

        user = _make_user()
        update = BotStartedUpdate(timestamp=0, chat_id=1, user=user)

        mw = MaxContextMiddleware()
        result = await mw(handler, update, {})

        assert result == "handler_result"

    @pytest.mark.asyncio
    async def test_preserves_existing_data(self) -> None:
        """Middleware не затирает уже существующие ключи в data."""

        async def handler(event: Any, data: dict[str, Any]) -> dict[str, Any]:
            return dict(data)

        user = _make_user()
        update = BotStartedUpdate(timestamp=0, chat_id=1, user=user)

        mw = MaxContextMiddleware()
        result = await mw(handler, update, {"existing_key": "value"})

        assert result["existing_key"] == "value"
        assert result["event_from_user"] is user
