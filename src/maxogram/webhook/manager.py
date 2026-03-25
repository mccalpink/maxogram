"""WebhookManager — lifecycle менеджер с auto-reconnect для Max webhook."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from aiohttp import web

from maxogram.webhook.handler import WebhookHandler

if TYPE_CHECKING:
    from maxogram.client.bot import Bot
    from maxogram.dispatcher.dispatcher import Dispatcher

logger = logging.getLogger(__name__)

__all__ = ["WebhookManager"]

# Max отписывает webhook через 8 часов без 200 OK.
# Переподписываемся каждые 7.5 часов для запаса.
_DEFAULT_RESUBSCRIBE_INTERVAL: float = 7.5 * 3600  # 27000 секунд


class WebhookManager:
    """Менеджер lifecycle webhook-сервера.

    Отвечает за:
    - Создание и запуск aiohttp web server
    - Подписку/отписку webhook через Bot API
    - Auto-reconnect: периодическая переподписка (Max отписывает через 8ч)
    - Graceful shutdown: отписка + остановка сервера + cleanup
    """

    def __init__(
        self,
        dispatcher: Dispatcher,
        bot: Bot,
        *,
        host: str = "0.0.0.0",
        port: int = 8080,
        path: str = "/webhook",
        allowed_updates: list[str] | None = None,
        resubscribe_interval: float = _DEFAULT_RESUBSCRIBE_INTERVAL,
        close_bot_session: bool = True,
        handle_signals: bool = True,
    ) -> None:
        self._dispatcher = dispatcher
        self._bot = bot
        self._host = host
        self._port = port
        self._path = path
        self._allowed_updates = allowed_updates
        self._resubscribe_interval = resubscribe_interval
        self._close_bot_session = close_bot_session
        self._handle_signals = handle_signals

        self._handler = WebhookHandler(dispatcher=dispatcher, bot=bot)
        self._runner: web.AppRunner | None = None
        self._resubscribe_task: asyncio.Task[None] | None = None
        self._webhook_url: str | None = None
        self._stop_event = asyncio.Event()

    async def _subscribe(self, webhook_url: str) -> None:
        """Подписаться на webhook через Bot API."""
        update_types = self._allowed_updates
        if update_types is None:
            update_types = self._dispatcher.resolve_used_update_types(
                skip_events={"update", "error"}
            )

        await self._bot.subscribe(
            url=webhook_url,
            update_types=update_types,
        )
        logger.info("Webhook подписка: url=%s, types=%s", webhook_url, update_types)

    async def _unsubscribe(self, webhook_url: str) -> None:
        """Отписаться от webhook."""
        await self._bot.unsubscribe(url=webhook_url)
        logger.info("Webhook отписка: url=%s", webhook_url)

    def _start_resubscribe_loop(self, webhook_url: str) -> None:
        """Запустить background task для периодической переподписки."""
        self._resubscribe_task = asyncio.create_task(
            self._resubscribe_loop(webhook_url),
            name="webhook-resubscribe",
        )

    async def _resubscribe_loop(self, webhook_url: str) -> None:
        """Переподписываться каждые resubscribe_interval секунд.

        Max автоматически отписывает webhook через 8 часов без 200 OK.
        Этот loop переподписывается заранее (по умолчанию каждые 7.5 часов).
        """
        try:
            while True:
                await asyncio.sleep(self._resubscribe_interval)
                try:
                    await self._subscribe(webhook_url)
                    logger.info("Webhook переподписка выполнена")
                except Exception:
                    logger.exception("Ошибка переподписки webhook")
        except asyncio.CancelledError:
            pass

    def _stop_resubscribe_loop(self) -> None:
        """Остановить background task переподписки."""
        if self._resubscribe_task is not None:
            self._resubscribe_task.cancel()
            self._resubscribe_task = None

    async def _setup(self, webhook_url: str) -> None:
        """Настроить и запустить webhook server.

        1. Создать aiohttp Application + handler route
        2. Запустить AppRunner + TCPSite
        3. Подписаться на webhook
        4. Запустить resubscribe loop
        5. Вызвать dispatcher.emit_startup()
        """
        self._webhook_url = webhook_url

        # Создаём aiohttp app
        app = web.Application()
        self._handler.register(app, path=self._path)

        # Запускаем web server
        self._runner = web.AppRunner(app)
        await self._runner.setup()

        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()

        logger.info(
            "Webhook server запущен: http://%s:%s%s",
            self._host,
            self._port,
            self._path,
        )

        # Подписка
        await self._subscribe(webhook_url)

        # Auto-reconnect
        self._start_resubscribe_loop(webhook_url)

        # Startup event
        await self._dispatcher.emit_startup(bot=self._bot)

    async def _shutdown(self) -> None:
        """Graceful shutdown.

        1. Остановить resubscribe loop
        2. Отписаться от webhook
        3. Остановить web server
        4. Вызвать dispatcher.emit_shutdown()
        5. Закрыть bot session (если close_bot_session=True)
        """
        # Остановить переподписку
        self._stop_resubscribe_loop()

        # Отписка
        if self._webhook_url:
            with contextlib.suppress(Exception):
                await self._unsubscribe(self._webhook_url)

        # Остановить web server
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

        # Shutdown event
        await self._dispatcher.emit_shutdown(bot=self._bot)

        # Закрыть bot session
        if self._close_bot_session:
            await self._bot.close()

        self._stop_event.set()

    async def start(
        self,
        webhook_url: str,
    ) -> None:
        """Запустить webhook server и ждать остановки.

        Args:
            webhook_url: Публичный URL, на который Max будет отправлять updates.
                         Должен быть HTTPS с CA-signed сертификатом, порт 443.
        """
        if self._handle_signals:
            try:
                loop = asyncio.get_running_loop()
                import signal

                for sig in (signal.SIGINT, signal.SIGTERM):
                    loop.add_signal_handler(sig, lambda: asyncio.create_task(self._shutdown()))
            except (NotImplementedError, AttributeError):
                pass

        try:
            await self._setup(webhook_url)
            # Ждём сигнала остановки
            await self._stop_event.wait()
        except Exception:
            logger.exception("Ошибка запуска webhook server")
            await self._shutdown()
            raise

    def run(self, webhook_url: str) -> None:
        """Синхронный запуск webhook server через asyncio.run()."""
        with contextlib.suppress(KeyboardInterrupt, SystemExit):
            asyncio.run(self.start(webhook_url))
