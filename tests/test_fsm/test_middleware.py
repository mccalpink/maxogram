"""Тесты FSMContextMiddleware."""

from __future__ import annotations

from typing import Any

import pytest

from maxogram.dispatcher.middlewares.base import BaseMiddleware
from maxogram.dispatcher.middlewares.context import EventChat
from maxogram.fsm.context import FSMContext
from maxogram.fsm.middleware import FSMContextMiddleware
from maxogram.fsm.storage.base import StorageKey
from maxogram.fsm.storage.memory import DisabledEventIsolation, MemoryStorage
from maxogram.fsm.strategy import FSMStrategy
from maxogram.types.user import User


def _make_user(user_id: int = 42) -> User:
    """Создать тестового пользователя."""
    return User(user_id=user_id, name="Test", is_bot=False, last_activity_time=0)


async def _capture_handler(event: Any, data: dict[str, Any]) -> dict[str, Any]:
    """Хендлер-заглушка, возвращающий data для проверки."""
    return dict(data)


class _FakeBot:
    """Мок Bot для тестов."""

    def __init__(self, bot_id: int = 1) -> None:
        self._me = type("BotInfo", (), {"user_id": bot_id})()


class TestFSMContextMiddlewareIsBaseMiddleware:
    """FSMContextMiddleware наследует BaseMiddleware."""

    def test_is_subclass(self) -> None:
        assert issubclass(FSMContextMiddleware, BaseMiddleware)


class TestFSMContextMiddlewareInjection:
    """FSMContextMiddleware — инъекция FSMContext в data."""

    @pytest.mark.asyncio
    async def test_injects_state_and_raw_state(self) -> None:
        """data содержит state, raw_state, fsm_storage."""
        storage = MemoryStorage()
        mw = FSMContextMiddleware(storage=storage)

        data: dict[str, Any] = {
            "bot": _FakeBot(bot_id=1),
            "event_from_user": _make_user(user_id=42),
            "event_chat": EventChat(chat_id=100),
        }
        result = await mw(_capture_handler, object(), data)

        assert isinstance(result["state"], FSMContext)
        assert result["raw_state"] is None
        assert result["fsm_storage"] is storage

    @pytest.mark.asyncio
    async def test_raw_state_reflects_current(self) -> None:
        """raw_state отражает текущее состояние из storage."""
        storage = MemoryStorage()
        key = StorageKey(bot_id=1, chat_id=100, user_id=42)
        await storage.set_state(key, "Form:name")

        mw = FSMContextMiddleware(storage=storage)
        data: dict[str, Any] = {
            "bot": _FakeBot(bot_id=1),
            "event_from_user": _make_user(user_id=42),
            "event_chat": EventChat(chat_id=100),
        }
        result = await mw(_capture_handler, object(), data)

        assert result["raw_state"] == "Form:name"


class TestFSMContextMiddlewareWithoutContext:
    """FSMContextMiddleware — без user или chat."""

    @pytest.mark.asyncio
    async def test_no_user_passes_through(self) -> None:
        """Без event_from_user — handler вызывается без FSM."""
        storage = MemoryStorage()
        mw = FSMContextMiddleware(storage=storage)

        data: dict[str, Any] = {
            "bot": _FakeBot(),
            "event_from_user": None,
            "event_chat": EventChat(chat_id=100),
        }
        result = await mw(_capture_handler, object(), data)

        assert "state" not in result

    @pytest.mark.asyncio
    async def test_no_chat_passes_through(self) -> None:
        """Без event_chat — handler вызывается без FSM."""
        storage = MemoryStorage()
        mw = FSMContextMiddleware(storage=storage)

        data: dict[str, Any] = {
            "bot": _FakeBot(),
            "event_from_user": _make_user(),
            "event_chat": None,
        }
        result = await mw(_capture_handler, object(), data)

        assert "state" not in result

    @pytest.mark.asyncio
    async def test_no_context_at_all(self) -> None:
        """Без event_from_user и event_chat — passes through."""
        storage = MemoryStorage()
        mw = FSMContextMiddleware(storage=storage)

        result = await mw(_capture_handler, object(), {})

        assert "state" not in result


class TestFSMContextMiddlewareStrategy:
    """FSMContextMiddleware — стратегии."""

    @pytest.mark.asyncio
    async def test_chat_strategy(self) -> None:
        """CHAT: user_id заменяется на chat_id в StorageKey."""
        storage = MemoryStorage()
        mw = FSMContextMiddleware(storage=storage, strategy=FSMStrategy.CHAT)

        data: dict[str, Any] = {
            "bot": _FakeBot(bot_id=1),
            "event_from_user": _make_user(user_id=42),
            "event_chat": EventChat(chat_id=100),
        }
        result = await mw(_capture_handler, object(), data)

        ctx: FSMContext = result["state"]
        assert ctx.key.chat_id == 100
        assert ctx.key.user_id == 100  # user_id == chat_id

    @pytest.mark.asyncio
    async def test_global_user_strategy(self) -> None:
        """GLOBAL_USER: chat_id заменяется на user_id в StorageKey."""
        storage = MemoryStorage()
        mw = FSMContextMiddleware(storage=storage, strategy=FSMStrategy.GLOBAL_USER)

        data: dict[str, Any] = {
            "bot": _FakeBot(bot_id=1),
            "event_from_user": _make_user(user_id=42),
            "event_chat": EventChat(chat_id=100),
        }
        result = await mw(_capture_handler, object(), data)

        ctx: FSMContext = result["state"]
        assert ctx.key.chat_id == 42  # chat_id == user_id
        assert ctx.key.user_id == 42


class TestFSMContextMiddlewareEventIsolation:
    """FSMContextMiddleware — event isolation."""

    @pytest.mark.asyncio
    async def test_with_disabled_isolation(self) -> None:
        """DisabledEventIsolation — handler выполняется нормально."""
        storage = MemoryStorage()
        isolation = DisabledEventIsolation()
        mw = FSMContextMiddleware(
            storage=storage, events_isolation=isolation
        )

        data: dict[str, Any] = {
            "bot": _FakeBot(bot_id=1),
            "event_from_user": _make_user(user_id=42),
            "event_chat": EventChat(chat_id=100),
        }
        result = await mw(_capture_handler, object(), data)

        assert isinstance(result["state"], FSMContext)

    @pytest.mark.asyncio
    async def test_handler_result_returned(self) -> None:
        """Middleware возвращает результат handler."""
        storage = MemoryStorage()
        mw = FSMContextMiddleware(storage=storage)

        async def handler(event: Any, data: dict[str, Any]) -> str:
            return "result"

        data: dict[str, Any] = {
            "bot": _FakeBot(),
            "event_from_user": _make_user(),
            "event_chat": EventChat(chat_id=100),
        }
        result = await mw(handler, object(), data)

        assert result == "result"


class TestFSMContextMiddlewareBotId:
    """FSMContextMiddleware — получение bot_id."""

    @pytest.mark.asyncio
    async def test_bot_id_from_me(self) -> None:
        """bot_id берётся из bot._me.user_id."""
        storage = MemoryStorage()
        mw = FSMContextMiddleware(storage=storage)

        data: dict[str, Any] = {
            "bot": _FakeBot(bot_id=99),
            "event_from_user": _make_user(user_id=42),
            "event_chat": EventChat(chat_id=100),
        }
        result = await mw(_capture_handler, object(), data)

        ctx: FSMContext = result["state"]
        assert ctx.key.bot_id == 99

    @pytest.mark.asyncio
    async def test_bot_id_default_zero(self) -> None:
        """Без bot — bot_id=0."""
        storage = MemoryStorage()
        mw = FSMContextMiddleware(storage=storage)

        data: dict[str, Any] = {
            "event_from_user": _make_user(user_id=42),
            "event_chat": EventChat(chat_id=100),
        }
        result = await mw(_capture_handler, object(), data)

        ctx: FSMContext = result["state"]
        assert ctx.key.bot_id == 0
