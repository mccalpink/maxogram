"""Тесты WebhookManager — lifecycle, auto-reconnect, graceful shutdown."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from maxogram.client.bot import Bot


def _make_bot() -> AsyncMock:
    """Создать мок Bot."""
    bot = AsyncMock(spec=Bot)
    bot.token = "test-token"
    bot.subscribe = AsyncMock()
    bot.unsubscribe = AsyncMock()
    return bot


def _make_dispatcher() -> MagicMock:
    """Создать мок Dispatcher."""
    from maxogram.dispatcher.dispatcher import Dispatcher

    dp = MagicMock(spec=Dispatcher)
    dp.feed_update = AsyncMock()
    dp.emit_startup = AsyncMock()
    dp.emit_shutdown = AsyncMock()
    dp.resolve_used_update_types = MagicMock(
        return_value=["message_created", "bot_started"]
    )
    return dp


@pytest.fixture
def bot() -> AsyncMock:
    return _make_bot()


@pytest.fixture
def dispatcher() -> MagicMock:
    return _make_dispatcher()


class TestWebhookManagerInit:
    """Тесты инициализации WebhookManager."""

    def test_stores_parameters(self, dispatcher: MagicMock, bot: AsyncMock) -> None:
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(
            dispatcher=dispatcher,
            bot=bot,
            host="0.0.0.0",
            port=8080,
            path="/webhook",
        )

        assert manager._dispatcher is dispatcher
        assert manager._bot is bot
        assert manager._host == "0.0.0.0"
        assert manager._port == 8080
        assert manager._path == "/webhook"

    def test_default_parameters(self, dispatcher: MagicMock, bot: AsyncMock) -> None:
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(
            dispatcher=dispatcher,
            bot=bot,
        )

        assert manager._host == "0.0.0.0"
        assert manager._port == 8080
        assert manager._path == "/webhook"

    def test_custom_resubscribe_interval(self, dispatcher: MagicMock, bot: AsyncMock) -> None:
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(
            dispatcher=dispatcher,
            bot=bot,
            resubscribe_interval=3600.0,
        )

        assert manager._resubscribe_interval == 3600.0

    def test_default_resubscribe_interval(self, dispatcher: MagicMock, bot: AsyncMock) -> None:
        """По умолчанию переподписка каждые 7.5 часов (Max отписывает через 8)."""
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(dispatcher=dispatcher, bot=bot)

        # 7.5 часов = 27000 секунд
        assert manager._resubscribe_interval == 27000.0


class TestWebhookManagerSubscription:
    """Тесты подписки/отписки webhook."""

    @pytest.mark.asyncio
    async def test_subscribe_called_with_url_and_types(
        self, dispatcher: MagicMock, bot: AsyncMock
    ) -> None:
        """При старте вызывается bot.subscribe() с правильными параметрами."""
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(
            dispatcher=dispatcher,
            bot=bot,
            path="/webhook",
        )

        await manager._subscribe(webhook_url="https://example.com/webhook")

        bot.subscribe.assert_awaited_once()
        call_kwargs = bot.subscribe.call_args
        assert call_kwargs.kwargs["url"] == "https://example.com/webhook"

    @pytest.mark.asyncio
    async def test_unsubscribe_called(
        self, dispatcher: MagicMock, bot: AsyncMock
    ) -> None:
        """При остановке вызывается bot.unsubscribe()."""
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(
            dispatcher=dispatcher,
            bot=bot,
        )

        await manager._unsubscribe(webhook_url="https://example.com/webhook")

        bot.unsubscribe.assert_awaited_once_with(url="https://example.com/webhook")

    @pytest.mark.asyncio
    async def test_subscribe_with_allowed_updates(
        self, dispatcher: MagicMock, bot: AsyncMock
    ) -> None:
        """Если указаны allowed_updates, они передаются в subscribe."""
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(
            dispatcher=dispatcher,
            bot=bot,
            allowed_updates=["message_created"],
        )

        await manager._subscribe(webhook_url="https://example.com/webhook")

        call_kwargs = bot.subscribe.call_args
        assert call_kwargs.kwargs["update_types"] == ["message_created"]

    @pytest.mark.asyncio
    async def test_subscribe_resolves_update_types_from_dispatcher(
        self, dispatcher: MagicMock, bot: AsyncMock
    ) -> None:
        """Если allowed_updates не указаны, берутся из dispatcher."""
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(
            dispatcher=dispatcher,
            bot=bot,
        )

        await manager._subscribe(webhook_url="https://example.com/webhook")

        dispatcher.resolve_used_update_types.assert_called_once()
        call_kwargs = bot.subscribe.call_args
        assert call_kwargs.kwargs["update_types"] == ["message_created", "bot_started"]


class TestWebhookManagerAutoReconnect:
    """Тесты auto-reconnect (переподписка по таймеру)."""

    @pytest.mark.asyncio
    async def test_resubscribe_task_created(
        self, dispatcher: MagicMock, bot: AsyncMock
    ) -> None:
        """_start_resubscribe_loop создаёт background task."""
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(
            dispatcher=dispatcher,
            bot=bot,
            resubscribe_interval=0.05,  # 50ms для теста
        )

        manager._start_resubscribe_loop(webhook_url="https://example.com/webhook")

        assert manager._resubscribe_task is not None
        assert not manager._resubscribe_task.done()

        # Cleanup
        manager._stop_resubscribe_loop()
        # Даём задаче завершиться
        await asyncio.sleep(0.01)

    @pytest.mark.asyncio
    async def test_resubscribe_loop_calls_subscribe_periodically(
        self, dispatcher: MagicMock, bot: AsyncMock
    ) -> None:
        """Переподписка вызывает subscribe() периодически."""
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(
            dispatcher=dispatcher,
            bot=bot,
            resubscribe_interval=0.05,  # 50ms
        )

        manager._start_resubscribe_loop(webhook_url="https://example.com/webhook")

        # Ждём 2+ интервала
        await asyncio.sleep(0.15)

        manager._stop_resubscribe_loop()
        await asyncio.sleep(0.01)

        # subscribe вызван минимум 2 раза (переподписки)
        assert bot.subscribe.await_count >= 2

    @pytest.mark.asyncio
    async def test_resubscribe_loop_survives_error(
        self, dispatcher: MagicMock, bot: AsyncMock
    ) -> None:
        """Ошибка при переподписке не убивает loop."""
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(
            dispatcher=dispatcher,
            bot=bot,
            resubscribe_interval=0.05,
        )

        call_count = 0

        async def failing_subscribe(**kwargs: Any) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("network error")

        bot.subscribe = AsyncMock(side_effect=failing_subscribe)

        manager._start_resubscribe_loop(webhook_url="https://example.com/webhook")

        await asyncio.sleep(0.15)

        manager._stop_resubscribe_loop()
        await asyncio.sleep(0.01)

        # Loop продолжил работать после ошибки
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_stop_resubscribe_loop_cancels_task(
        self, dispatcher: MagicMock, bot: AsyncMock
    ) -> None:
        """_stop_resubscribe_loop отменяет background task."""
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(
            dispatcher=dispatcher,
            bot=bot,
            resubscribe_interval=100.0,
        )

        manager._start_resubscribe_loop(webhook_url="https://example.com/webhook")
        task = manager._resubscribe_task
        assert task is not None

        manager._stop_resubscribe_loop()
        await asyncio.sleep(0.01)

        assert task.cancelled() or task.done()
        assert manager._resubscribe_task is None


class TestWebhookManagerGracefulShutdown:
    """Тесты graceful shutdown."""

    @pytest.mark.asyncio
    async def test_stop_unsubscribes_and_stops_resubscribe(
        self, dispatcher: MagicMock, bot: AsyncMock
    ) -> None:
        """stop() отписывает webhook и останавливает resubscribe loop."""
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(
            dispatcher=dispatcher,
            bot=bot,
            resubscribe_interval=100.0,
        )

        manager._webhook_url = "https://example.com/webhook"
        manager._start_resubscribe_loop(webhook_url="https://example.com/webhook")

        await manager._shutdown()

        bot.unsubscribe.assert_awaited_once_with(url="https://example.com/webhook")
        assert manager._resubscribe_task is None

    @pytest.mark.asyncio
    async def test_stop_without_running_does_not_fail(
        self, dispatcher: MagicMock, bot: AsyncMock
    ) -> None:
        """Вызов stop() без запущенного manager не вызывает ошибок."""
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(
            dispatcher=dispatcher,
            bot=bot,
        )

        # Не должен вызвать исключений
        await manager._shutdown()


class TestWebhookManagerLifecycle:
    """Тесты полного lifecycle (start → stop)."""

    @pytest.mark.asyncio
    async def test_start_creates_app_and_subscribes(
        self, dispatcher: MagicMock, bot: AsyncMock
    ) -> None:
        """start() создаёт aiohttp app, подписывается на webhook, запускает resubscribe."""
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(
            dispatcher=dispatcher,
            bot=bot,
            host="127.0.0.1",
            port=0,  # Автоматический порт
            resubscribe_interval=100.0,
        )

        # Мокаем запуск web server
        with patch("aiohttp.web.AppRunner") as mock_runner_cls:
            mock_runner = AsyncMock()
            mock_runner_cls.return_value = mock_runner
            mock_site = AsyncMock()

            with patch("aiohttp.web.TCPSite") as mock_site_cls:
                mock_site_cls.return_value = mock_site

                await manager._setup(webhook_url="https://example.com/webhook")

                bot.subscribe.assert_awaited_once()
                assert manager._resubscribe_task is not None

                # Cleanup
                await manager._shutdown()

    @pytest.mark.asyncio
    async def test_dispatcher_startup_shutdown_emitted(
        self, dispatcher: MagicMock, bot: AsyncMock
    ) -> None:
        """emit_startup/emit_shutdown вызываются при lifecycle."""
        from maxogram.webhook.manager import WebhookManager

        manager = WebhookManager(
            dispatcher=dispatcher,
            bot=bot,
            host="127.0.0.1",
            port=0,
        )

        with patch("aiohttp.web.AppRunner") as mock_runner_cls:
            mock_runner = AsyncMock()
            mock_runner_cls.return_value = mock_runner

            with patch("aiohttp.web.TCPSite") as mock_site_cls:
                mock_site_cls.return_value = AsyncMock()

                await manager._setup(webhook_url="https://example.com/webhook")
                dispatcher.emit_startup.assert_awaited_once()

                await manager._shutdown()
                dispatcher.emit_shutdown.assert_awaited_once()
