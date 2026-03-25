"""Тесты multi-bot polling — поддержка нескольких ботов в одном Dispatcher."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from maxogram.client.bot import Bot
from maxogram.dispatcher.dispatcher import Dispatcher
from maxogram.enums import ChatType
from maxogram.types.message import Message, MessageBody, Recipient
from maxogram.types.update import GetUpdatesResult, MessageCreatedUpdate
from maxogram.types.user import User


def _make_bot(token: str = "test-token") -> AsyncMock:
    """Создать мок Bot с заданным токеном."""
    bot = AsyncMock(spec=Bot)
    bot.token = token
    return bot


def _make_message_update(
    *,
    user_id: int = 1,
    chat_id: int = 100,
    text: str = "hello",
) -> MessageCreatedUpdate:
    """Создать MessageCreatedUpdate для тестов."""
    user = User(user_id=user_id, name="Test", is_bot=False, last_activity_time=0)
    recipient = Recipient(chat_id=chat_id, chat_type=ChatType.DIALOG)
    body = MessageBody(mid="mid1", seq=1, text=text)
    msg = Message(sender=user, recipient=recipient, timestamp=0, body=body)
    return MessageCreatedUpdate(timestamp=0, message=msg)


def _make_updates_result(
    updates: list[Any] | None = None,
    marker: int | None = None,
) -> GetUpdatesResult:
    """Создать GetUpdatesResult."""
    return GetUpdatesResult(updates=updates or [], marker=marker)


class TestStartPollingMultiBot:
    """Тесты start_polling с несколькими ботами."""

    @pytest.mark.asyncio
    async def test_single_bot_backward_compatible(self) -> None:
        """Один бот работает как раньше — обратная совместимость."""
        dp = Dispatcher()
        bot = _make_bot("bot-1")

        async def handler(event: Any) -> str:
            return "ok"

        dp.message_created.register(handler)

        update = _make_message_update()
        call_count = 0

        async def bot_call(method: Any) -> GetUpdatesResult:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_updates_result(updates=[update])
            dp.stop()
            return _make_updates_result()

        bot.side_effect = bot_call

        await dp.start_polling(bot, handle_signals=False)

        bot.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_two_bots_both_receive_updates(self) -> None:
        """Два бота — каждый получает свои updates через feed_update."""
        dp = Dispatcher()
        bot1 = _make_bot("bot-1")
        bot2 = _make_bot("bot-2")

        received_bots: list[str] = []

        async def handler(event: Any, bot: Any = None) -> str:
            received_bots.append(bot.token)
            return "ok"

        dp.message_created.register(handler)

        update1 = _make_message_update(text="from bot1")
        update2 = _make_message_update(text="from bot2")

        async def bot1_call(method: Any) -> GetUpdatesResult:
            if not hasattr(bot1_call, "_count"):
                bot1_call._count = 0  # type: ignore[attr-defined]
            bot1_call._count += 1  # type: ignore[attr-defined]
            if bot1_call._count == 1:  # type: ignore[attr-defined]
                return _make_updates_result(updates=[update1])
            # Ждём пока оба получат updates, потом stop
            await asyncio.sleep(0.05)
            dp.stop()
            return _make_updates_result()

        async def bot2_call(method: Any) -> GetUpdatesResult:
            if not hasattr(bot2_call, "_count"):
                bot2_call._count = 0  # type: ignore[attr-defined]
            bot2_call._count += 1  # type: ignore[attr-defined]
            if bot2_call._count == 1:  # type: ignore[attr-defined]
                return _make_updates_result(updates=[update2])
            await asyncio.sleep(0.1)
            return _make_updates_result()

        bot1.side_effect = bot1_call
        bot2.side_effect = bot2_call

        await dp.start_polling(bot1, bot2, handle_signals=False)

        # Оба бота получили updates
        assert "bot-1" in received_bots
        assert "bot-2" in received_bots

    @pytest.mark.asyncio
    async def test_two_bots_sessions_closed(self) -> None:
        """При остановке — сессии обоих ботов закрываются."""
        dp = Dispatcher()
        bot1 = _make_bot("bot-1")
        bot2 = _make_bot("bot-2")

        async def bot_call(method: Any) -> GetUpdatesResult:
            dp.stop()
            return _make_updates_result()

        bot1.side_effect = bot_call
        bot2.side_effect = bot_call

        await dp.start_polling(bot1, bot2, handle_signals=False)

        bot1.close.assert_awaited_once()
        bot2.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_bot_session_false(self) -> None:
        """close_bot_session=False — сессии не закрываются."""
        dp = Dispatcher()
        bot1 = _make_bot("bot-1")
        bot2 = _make_bot("bot-2")

        async def bot_call(method: Any) -> GetUpdatesResult:
            dp.stop()
            return _make_updates_result()

        bot1.side_effect = bot_call
        bot2.side_effect = bot_call

        await dp.start_polling(
            bot1,
            bot2,
            handle_signals=False,
            close_bot_session=False,
        )

        bot1.close.assert_not_awaited()
        bot2.close.assert_not_awaited()


class TestStartPollingLifecycle:
    """Тесты lifecycle events при multi-bot polling."""

    @pytest.mark.asyncio
    async def test_startup_emitted_before_polling(self) -> None:
        """startup event вызывается до начала polling."""
        dp = Dispatcher()
        bot1 = _make_bot("bot-1")
        bot2 = _make_bot("bot-2")
        events: list[str] = []

        @dp.startup.register
        async def on_startup(**kwargs: Any) -> None:
            events.append("startup")

        async def bot_call(method: Any) -> GetUpdatesResult:
            events.append("polling")
            dp.stop()
            return _make_updates_result()

        bot1.side_effect = bot_call
        bot2.side_effect = bot_call

        await dp.start_polling(bot1, bot2, handle_signals=False)

        assert events[0] == "startup"

    @pytest.mark.asyncio
    async def test_shutdown_emitted_after_stop(self) -> None:
        """shutdown event вызывается после остановки polling."""
        dp = Dispatcher()
        bot1 = _make_bot("bot-1")
        bot2 = _make_bot("bot-2")
        events: list[str] = []

        @dp.shutdown.register
        async def on_shutdown(**kwargs: Any) -> None:
            events.append("shutdown")

        async def bot_call(method: Any) -> GetUpdatesResult:
            dp.stop()
            return _make_updates_result()

        bot1.side_effect = bot_call
        bot2.side_effect = bot_call

        await dp.start_polling(bot1, bot2, handle_signals=False)

        assert "shutdown" in events


class TestStopMultiBot:
    """Тесты graceful shutdown для multi-bot."""

    @pytest.mark.asyncio
    async def test_stop_halts_all_bots(self) -> None:
        """stop() останавливает polling для всех ботов."""
        dp = Dispatcher()
        bot1 = _make_bot("bot-1")
        bot2 = _make_bot("bot-2")
        call_counts = {"bot1": 0, "bot2": 0}

        async def bot1_call(method: Any) -> GetUpdatesResult:
            call_counts["bot1"] += 1
            if call_counts["bot1"] >= 2:
                dp.stop()
            return _make_updates_result()

        async def bot2_call(method: Any) -> GetUpdatesResult:
            call_counts["bot2"] += 1
            return _make_updates_result()

        bot1.side_effect = bot1_call
        bot2.side_effect = bot2_call

        await dp.start_polling(bot1, bot2, handle_signals=False)

        # Оба бота остановлены — polling завершился
        assert call_counts["bot1"] >= 2
        # bot2 тоже остановился (не бесконечный цикл)


class TestFeedUpdateMultiBot:
    """Тесты feed_update с разными ботами."""

    @pytest.mark.asyncio
    async def test_handler_receives_correct_bot(self) -> None:
        """Handler получает бот, через которого пришёл update."""
        dp = Dispatcher()
        bot1 = _make_bot("bot-1")
        bot2 = _make_bot("bot-2")

        received: list[tuple[str, str]] = []

        async def handler(event: Any, bot: Any = None) -> str:
            received.append((bot.token, event.body.text))
            return "ok"

        dp.message_created.register(handler)

        update1 = _make_message_update(text="hello from bot1")
        update2 = _make_message_update(text="hello from bot2")

        await dp.feed_update(bot1, update1)
        await dp.feed_update(bot2, update2)

        assert ("bot-1", "hello from bot1") in received
        assert ("bot-2", "hello from bot2") in received

    @pytest.mark.asyncio
    async def test_workflow_data_shared_between_bots(self) -> None:
        """workflow_data доступна хендлерам от обоих ботов."""
        dp = Dispatcher(db="shared_db")
        bot1 = _make_bot("bot-1")
        bot2 = _make_bot("bot-2")

        db_values: list[str] = []

        async def handler(event: Any, db: Any = None) -> str:
            db_values.append(db)
            return "ok"

        dp.message_created.register(handler)

        update = _make_message_update()
        await dp.feed_update(bot1, update)
        await dp.feed_update(bot2, update)

        assert db_values == ["shared_db", "shared_db"]


class TestRunPollingMultiBot:
    """Тесты run_polling с несколькими ботами."""

    def test_run_polling_accepts_multiple_bots(self) -> None:
        """run_polling принимает *bots — не падает на сигнатуре."""
        dp = Dispatcher()
        bot1 = _make_bot("bot-1")
        bot2 = _make_bot("bot-2")

        async def bot_call(method: Any) -> GetUpdatesResult:
            dp.stop()
            return _make_updates_result()

        bot1.side_effect = bot_call
        bot2.side_effect = bot_call

        # run_polling запускает asyncio.run, поэтому не можем вызывать
        # из async-контекста. Проверяем через patch.
        with patch.object(dp, "start_polling", new_callable=AsyncMock) as mock_start:
            dp.run_polling(bot1, bot2, polling_timeout=5)
            mock_start.assert_awaited_once_with(bot1, bot2, polling_timeout=5)


class TestMultiBotResolveUpdates:
    """Тесты resolve_used_update_types при multi-bot."""

    @pytest.mark.asyncio
    async def test_allowed_updates_resolved_from_handlers(self) -> None:
        """allowed_updates определяется из зарегистрированных хендлеров."""
        dp = Dispatcher()
        bot1 = _make_bot("bot-1")

        async def msg_handler(event: Any) -> str:
            return "ok"

        async def bot_handler(event: Any) -> str:
            return "ok"

        dp.message_created.register(msg_handler)
        dp.bot_started.register(bot_handler)

        async def bot_call(method: Any) -> GetUpdatesResult:
            dp.stop()
            return _make_updates_result()

        bot1.side_effect = bot_call

        await dp.start_polling(bot1, handle_signals=False)

        # allowed_updates должен содержать зарегистрированные типы
        types = dp.resolve_used_update_types(skip_events={"update", "error"})
        assert "message_created" in types
        assert "bot_started" in types
