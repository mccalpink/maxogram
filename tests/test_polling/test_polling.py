"""Тесты Polling — long polling клиент для Max Bot API."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from maxogram.client.bot import Bot
from maxogram.enums import ChatType
from maxogram.polling.polling import Polling
from maxogram.types.message import Message, MessageBody, Recipient
from maxogram.types.update import GetUpdatesResult, MessageCreatedUpdate
from maxogram.types.user import User
from maxogram.utils.backoff import BackoffConfig


def _make_bot() -> AsyncMock:
    """Создать мок Bot."""
    bot = AsyncMock(spec=Bot)
    bot.token = "test-token"
    return bot


def _make_dispatcher() -> MagicMock:
    """Создать мок Dispatcher."""
    from maxogram.dispatcher.dispatcher import Dispatcher

    dp = MagicMock(spec=Dispatcher)
    dp.feed_update = AsyncMock()
    return dp


def _make_message_update(text: str = "test") -> MessageCreatedUpdate:
    """Создать реальный MessageCreatedUpdate."""
    user = User(user_id=1, name="Test", is_bot=False, last_activity_time=0)
    recipient = Recipient(chat_id=100, chat_type=ChatType.DIALOG)
    body = MessageBody(mid="mid1", seq=1, text=text)
    msg = Message(sender=user, recipient=recipient, timestamp=0, body=body)
    return MessageCreatedUpdate(timestamp=0, message=msg)


def _make_updates_result(
    updates: list[Any] | None = None,
    marker: int | None = None,
) -> GetUpdatesResult:
    """Создать GetUpdatesResult."""
    return GetUpdatesResult(updates=updates or [], marker=marker)


class TestPollingInit:
    """Тесты инициализации Polling."""

    def test_stores_parameters(self) -> None:
        bot = _make_bot()
        dp = _make_dispatcher()
        cfg = BackoffConfig(min_delay=2.0)

        polling = Polling(
            dispatcher=dp,
            bot=bot,
            polling_timeout=10,
            allowed_updates=["message_created"],
            backoff_config=cfg,
        )

        assert polling._dispatcher is dp
        assert polling._bot is bot
        assert polling._polling_timeout == 10
        assert polling._allowed_updates == ["message_created"]
        assert polling._backoff.config is cfg

    def test_default_parameters(self) -> None:
        bot = _make_bot()
        dp = _make_dispatcher()

        polling = Polling(dispatcher=dp, bot=bot)

        assert polling._polling_timeout == 30
        assert polling._allowed_updates is None
        assert polling._marker is None


class TestPollingStop:
    """Тесты остановки Polling."""

    def test_stop_sets_signal(self) -> None:
        bot = _make_bot()
        dp = _make_dispatcher()
        polling = Polling(dispatcher=dp, bot=bot)

        assert not polling._stop_signal.is_set()
        polling.stop()
        assert polling._stop_signal.is_set()


class TestPollingLoop:
    """Тесты polling loop."""

    @pytest.mark.asyncio
    async def test_feed_update_called_for_each_update(self) -> None:
        """GetUpdates возвращает updates -> feed_update для каждого."""
        bot = _make_bot()
        dp = _make_dispatcher()
        polling = Polling(dispatcher=dp, bot=bot)

        update1 = _make_message_update("hello")
        update2 = _make_message_update("world")

        call_count = 0

        async def bot_call(method: Any) -> GetUpdatesResult:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_updates_result(updates=[update1, update2], marker=100)
            # Остановить после первого цикла
            polling.stop()
            return _make_updates_result()

        bot.side_effect = bot_call

        await polling.start()

        assert dp.feed_update.await_count == 2
        dp.feed_update.assert_any_await(bot, update1)
        dp.feed_update.assert_any_await(bot, update2)

    @pytest.mark.asyncio
    async def test_marker_tracking(self) -> None:
        """Marker из ответа используется в следующем запросе."""
        bot = _make_bot()
        dp = _make_dispatcher()
        polling = Polling(dispatcher=dp, bot=bot)

        call_count = 0
        received_methods: list[Any] = []

        async def bot_call(method: Any) -> GetUpdatesResult:
            nonlocal call_count
            received_methods.append(method)
            call_count += 1
            if call_count == 1:
                return _make_updates_result(marker=42)
            if call_count == 2:
                return _make_updates_result(marker=99)
            polling.stop()
            return _make_updates_result()

        bot.side_effect = bot_call

        await polling.start()

        # Первый вызов — marker=None
        assert received_methods[0].marker is None
        # Второй вызов — marker=42
        assert received_methods[1].marker == 42
        # Третий вызов — marker=99
        assert received_methods[2].marker == 99

    @pytest.mark.asyncio
    async def test_backoff_on_error_and_reset_on_success(self) -> None:
        """При ошибке — backoff.wait(), при успехе — backoff.reset()."""
        bot = _make_bot()
        dp = _make_dispatcher()
        cfg = BackoffConfig(min_delay=0.01, factor=2.0, jitter=False)
        polling = Polling(dispatcher=dp, bot=bot, backoff_config=cfg)

        call_count = 0

        async def bot_call(method: Any) -> GetUpdatesResult:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("network error")
            if call_count == 2:
                return _make_updates_result()
            polling.stop()
            return _make_updates_result()

        bot.side_effect = bot_call

        with (
            patch.object(polling._backoff, "wait", new_callable=AsyncMock) as mock_wait,
            patch.object(polling._backoff, "reset") as mock_reset,
        ):
            await polling.start()

            # Ошибка на 1-м вызове — backoff.wait()
            assert mock_wait.await_count == 1
            # Успех на 2-м и 3-м — reset() вызван дважды
            assert mock_reset.call_count == 2

    @pytest.mark.asyncio
    async def test_update_processing_error_does_not_stop_polling(self) -> None:
        """Ошибка в feed_update не останавливает polling."""
        bot = _make_bot()
        dp = _make_dispatcher()
        polling = Polling(dispatcher=dp, bot=bot)

        update1 = _make_message_update("hello")
        update2 = _make_message_update("world")

        dp.feed_update.side_effect = [ValueError("boom"), None]

        call_count = 0

        async def bot_call(method: Any) -> GetUpdatesResult:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_updates_result(updates=[update1, update2])
            polling.stop()
            return _make_updates_result()

        bot.side_effect = bot_call

        await polling.start()

        # Оба update обработаны (первый с ошибкой, второй — нет)
        assert dp.feed_update.await_count == 2

    @pytest.mark.asyncio
    async def test_cancellation_stops_loop(self) -> None:
        """CancelledError прерывает цикл."""
        bot = _make_bot()
        dp = _make_dispatcher()
        polling = Polling(dispatcher=dp, bot=bot)

        bot.side_effect = asyncio.CancelledError()

        # Не должен зависнуть — CancelledError прерывает цикл
        await polling.start()

    @pytest.mark.asyncio
    async def test_allowed_updates_passed_to_get_updates(self) -> None:
        """allowed_updates передаётся в GetUpdates.types."""
        bot = _make_bot()
        dp = _make_dispatcher()
        polling = Polling(
            dispatcher=dp,
            bot=bot,
            allowed_updates=["message_created", "bot_started"],
        )

        received_methods: list[Any] = []

        async def bot_call(method: Any) -> GetUpdatesResult:
            received_methods.append(method)
            polling.stop()
            return _make_updates_result()

        bot.side_effect = bot_call

        await polling.start()

        assert received_methods[0].types == ["message_created", "bot_started"]

    @pytest.mark.asyncio
    async def test_polling_timeout_passed_to_get_updates(self) -> None:
        """polling_timeout передаётся в GetUpdates.timeout."""
        bot = _make_bot()
        dp = _make_dispatcher()
        polling = Polling(dispatcher=dp, bot=bot, polling_timeout=15)

        received_methods: list[Any] = []

        async def bot_call(method: Any) -> GetUpdatesResult:
            received_methods.append(method)
            polling.stop()
            return _make_updates_result()

        bot.side_effect = bot_call

        await polling.start()

        assert received_methods[0].timeout == 15


class TestDropPendingUpdates:
    """Тесты drop_pending_updates — пропуск старых обновлений при старте."""

    @pytest.mark.asyncio
    async def test_drop_pending_skips_old_updates(self) -> None:
        """drop_pending_updates=True зацикливает GetUpdates(timeout=0) до пустого ответа."""
        bot = _make_bot()
        dp = _make_dispatcher()
        polling = Polling(dispatcher=dp, bot=bot, drop_pending_updates=True)

        received_methods: list[Any] = []

        async def bot_call(method: Any) -> GetUpdatesResult:
            received_methods.append(method)
            if len(received_methods) == 1:
                # Первый flush — 2 старых update
                return _make_updates_result(
                    updates=[_make_message_update("old1"), _make_message_update("old2")],
                    marker=500,
                )
            if len(received_methods) == 2:
                # Второй flush — ещё 1 старый
                return _make_updates_result(
                    updates=[_make_message_update("old3")],
                    marker=600,
                )
            if len(received_methods) == 3:
                # Третий flush — пусто, flush завершён
                return _make_updates_result(marker=600)
            # Четвёртый — нормальный polling
            polling.stop()
            return _make_updates_result()

        bot.side_effect = bot_call

        await polling.start()

        # Первый flush — timeout=1 (даём серверу время), остальные — timeout=0
        assert received_methods[0].timeout == 1
        assert received_methods[1].timeout == 0
        assert received_methods[1].marker == 500  # marker от первого batch
        assert received_methods[2].timeout == 0
        assert received_methods[2].marker == 600
        # Четвёртый — нормальный polling
        assert received_methods[3].timeout == 30
        assert received_methods[3].marker == 600
        # Старые updates НЕ переданы в dispatcher
        assert dp.feed_update.await_count == 0

    @pytest.mark.asyncio
    async def test_drop_pending_false_by_default(self) -> None:
        """По умолчанию drop_pending_updates=False — все updates обрабатываются."""
        bot = _make_bot()
        dp = _make_dispatcher()
        polling = Polling(dispatcher=dp, bot=bot)

        async def bot_call(method: Any) -> GetUpdatesResult:
            polling.stop()
            return _make_updates_result(
                updates=[_make_message_update("msg")],
                marker=1,
            )

        bot.side_effect = bot_call

        await polling.start()

        # Update обработан
        assert dp.feed_update.await_count == 1

    @pytest.mark.asyncio
    async def test_drop_pending_logs_total_count(self) -> None:
        """drop_pending_updates логирует общее количество пропущенных обновлений."""
        bot = _make_bot()
        dp = _make_dispatcher()
        polling = Polling(dispatcher=dp, bot=bot, drop_pending_updates=True)

        call_count = 0

        async def bot_call(method: Any) -> GetUpdatesResult:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_updates_result(
                    updates=[_make_message_update("old1"), _make_message_update("old2")],
                    marker=10,
                )
            if call_count == 2:
                # Пустой ответ — flush завершён
                return _make_updates_result(marker=10)
            polling.stop()
            return _make_updates_result()

        bot.side_effect = bot_call

        with patch("maxogram.polling.polling.logger") as mock_logger:
            await polling.start()
            mock_logger.info.assert_any_call(
                "Dropped %d pending update(s), marker set to %s",
                2,
                10,
            )
