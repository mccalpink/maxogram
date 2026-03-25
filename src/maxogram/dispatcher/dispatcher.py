"""Dispatcher — центральный координатор фреймворка."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from maxogram.client.bot import Bot
from maxogram.dispatcher.event.bases import UNHANDLED
from maxogram.dispatcher.event.max import MaxEventObserver
from maxogram.dispatcher.middlewares.context import MaxContextMiddleware
from maxogram.dispatcher.middlewares.error import ErrorsMiddleware
from maxogram.dispatcher.router import Router
from maxogram.polling.polling import Polling
from maxogram.utils.backoff import BackoffConfig

logger = logging.getLogger(__name__)

__all__ = ["Dispatcher"]


class Dispatcher(Router):
    """Центральный координатор: наследует Router, добавляет orchestration.

    Связывает: Router tree + Bot + Middleware pipeline + Update parsing.
    """

    def __init__(
        self,
        *,
        name: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name)

        # workflow_data — глобальный контекст, доступный в хендлерах
        self.workflow_data: dict[str, Any] = kwargs

        # Специальный update observer — точка входа для всех Update
        self.update = MaxEventObserver(router=self, event_name="update")
        self.update.register(self._listen_update)
        self.observers["update"] = self.update

        # Встроенные outer middleware на update observer (порядок важен!)
        self.update.outer_middleware.register(ErrorsMiddleware(router=self))
        self.update.outer_middleware.register(MaxContextMiddleware())

        # Polling instances (multi-bot support)
        self._pollings: list[Polling] = []
        self._running_lock = asyncio.Lock()

    @property
    def parent_router(self) -> Router | None:
        """Родительский роутер."""
        return self._parent_router

    @parent_router.setter
    def parent_router(self, value: Router) -> None:
        """Dispatcher не может быть вложен в другой Router."""
        raise RuntimeError("Dispatcher cannot be attached to another Router")

    async def feed_update(self, bot: Bot, update: Any, **kwargs: Any) -> Any:
        """Главная точка входа — подать Update для обработки.

        1. Собирает data = workflow_data + kwargs + bot
        2. Оборачивает в outer middleware chain update observer
        3. Логирует результат
        """
        data = {
            **self.workflow_data,
            **kwargs,
            "bot": bot,
            "event_update": update,
        }

        result = await self.update.wrap_outer_middleware(
            self.update.trigger,
            update,
            data,
        )

        if result is UNHANDLED:
            logger.debug(
                "Update %s is not handled",
                getattr(update, "update_type", "unknown"),
            )

        return result

    # Маппинг update_type → поле с event-объектом для извлечения.
    # Если update_type нет в маппинге или значение None — передаётся весь Update.
    _EVENT_FIELD_MAP: dict[str, str | None] = {
        "message_created": "message",
        "message_edited": "message",
        "message_callback": "callback",
    }

    async def _listen_update(self, update: Any, **kwargs: Any) -> Any:
        """Разделить Update на тип и извлечь event-объект.

        Для message_created/message_edited извлекается Message,
        для message_callback — Callback. Остальные update'ы передаются целиком.
        Оригинальный Update всегда доступен через kwargs["event_update"]
        (устанавливается в feed_update).
        """
        update_type = getattr(update, "update_type", None)

        if update_type is None:
            logger.warning("Update без update_type: %s", update)
            return UNHANDLED

        # Извлечь event-объект из Update (если есть маппинг)
        field = self._EVENT_FIELD_MAP.get(update_type)
        event = getattr(update, field, update) if field is not None else update

        return await self.propagate_event(
            update_type=update_type,
            event=event,
            **kwargs,
        )

    async def start_polling(
        self,
        *bots: Bot,
        polling_timeout: int = 30,
        allowed_updates: list[str] | None = None,
        handle_signals: bool = True,
        close_bot_session: bool = True,
        backoff_config: BackoffConfig | None = None,
        drop_pending_updates: bool = False,
    ) -> None:
        """Запуск long polling для одного или нескольких ботов.

        Каждый бот получает свой Polling instance.
        Все polling loops работают параллельно через asyncio.gather.

        1. Acquire running lock (предотвращает двойной запуск)
        2. Resolve allowed_updates из зарегистрированных хендлеров
        3. emit_startup
        4. Параллельный polling loop для каждого бота
        5. emit_shutdown
        6. Закрыть bot sessions

        Warning:
            При multi-bot сценарии (несколько Dispatcher в одном event loop
            через ``asyncio.gather``) используйте ``handle_signals=False``
            для всех dispatcher и обрабатывайте сигналы вручную::

                async def main():
                    try:
                        await asyncio.gather(
                            dp1.start_polling(bot1, handle_signals=False),
                            dp2.start_polling(bot2, handle_signals=False),
                        )
                    except KeyboardInterrupt:
                        dp1.stop()
                        dp2.stop()
        """
        if not bots:
            msg = "At least one Bot instance is required"
            raise ValueError(msg)

        async with self._running_lock:
            if allowed_updates is None:
                allowed_updates = self.resolve_used_update_types(
                    skip_events={"update", "error"}
                )

            self._pollings = [
                Polling(
                    dispatcher=self,
                    bot=bot,
                    polling_timeout=polling_timeout,
                    allowed_updates=allowed_updates,
                    backoff_config=backoff_config,
                    drop_pending_updates=drop_pending_updates,
                )
                for bot in bots
            ]

            if handle_signals:
                try:
                    loop = asyncio.get_running_loop()
                    import signal

                    for sig in (signal.SIGINT, signal.SIGTERM):
                        # Не перезаписывать если handler уже установлен
                        # (multi-bot: второй dispatcher не должен затирать первого)
                        try:
                            current = signal.getsignal(sig)
                            if current in (signal.SIG_DFL, signal.SIG_IGN, None):
                                loop.add_signal_handler(sig, self.stop)
                        except (OSError, ValueError):
                            loop.add_signal_handler(sig, self.stop)
                except (NotImplementedError, AttributeError):
                    pass

            try:
                await self.emit_startup()
                await asyncio.gather(*(p.start() for p in self._pollings))
            finally:
                await self.emit_shutdown()
                if close_bot_session:
                    for bot in bots:
                        await bot.close()

    def run_polling(self, *bots: Bot, **kwargs: Any) -> None:
        """Синхронный запуск polling через asyncio.run()."""
        import contextlib

        with contextlib.suppress(KeyboardInterrupt, SystemExit):
            asyncio.run(self.start_polling(*bots, **kwargs))

    def stop(self) -> None:
        """Остановить polling для всех ботов."""
        for polling in self._pollings:
            polling.stop()

    # Dict-like доступ к workflow_data
    def __getitem__(self, key: str) -> Any:
        return self.workflow_data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.workflow_data[key] = value

    def __delitem__(self, key: str) -> None:
        del self.workflow_data[key]

    def __contains__(self, key: object) -> bool:
        return key in self.workflow_data

    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение из workflow_data."""
        return self.workflow_data.get(key, default)
