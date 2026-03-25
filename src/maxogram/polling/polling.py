"""Long polling клиент для Max Bot API."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from maxogram.client.bot import Bot
from maxogram.methods.update import GetUpdates
from maxogram.utils.backoff import Backoff, BackoffConfig

if TYPE_CHECKING:
    from maxogram.dispatcher.dispatcher import Dispatcher

logger = logging.getLogger(__name__)

__all__ = ["Polling"]


class Polling:
    """Long polling клиент для Max Bot API.

    Отвечает за:
    - Цикл GetUpdates с marker tracking
    - Exponential backoff при ошибках
    - Graceful shutdown через stop()
    """

    def __init__(
        self,
        dispatcher: Dispatcher,
        bot: Bot,
        polling_timeout: int = 30,
        allowed_updates: list[str] | None = None,
        backoff_config: BackoffConfig | None = None,
        drop_pending_updates: bool = False,
    ) -> None:
        self._dispatcher = dispatcher
        self._bot = bot
        self._polling_timeout = polling_timeout
        self._allowed_updates = allowed_updates
        self._backoff = Backoff(backoff_config)
        self._stop_signal = asyncio.Event()
        self._marker: int | None = None
        self._drop_pending = drop_pending_updates

    async def _skip_pending(self) -> None:
        """Пропустить накопленные обновления (flush).

        Max API при timeout=0 может вернуть пустой ответ даже при наличии
        pending updates. Используем timeout=1 для первого вызова (даём серверу
        время доставить backlog), затем timeout=0 для проверки что очередь пуста.
        """
        total_dropped = 0
        first_call = True
        while True:
            # Первый вызов с timeout=1, остальные с timeout=0
            timeout = 1 if first_call else 0
            first_call = False
            result = await self._bot(
                GetUpdates(
                    timeout=timeout,
                    marker=self._marker,
                    types=self._allowed_updates or None,
                )
            )
            if result.marker is not None:
                self._marker = result.marker
            batch = len(result.updates)
            total_dropped += batch
            if batch == 0:
                break
        logger.info(
            "Dropped %d pending update(s), marker set to %s",
            total_dropped,
            self._marker,
        )

    async def start(self) -> None:
        """Запустить polling loop.

        Выполняет GetUpdates в цикле, передаёт каждый update
        в dispatcher.feed_update(). При ошибках — exponential backoff.
        Объект нельзя переиспользовать после stop() — создайте новый.
        """
        if self._drop_pending:
            await self._skip_pending()

        while not self._stop_signal.is_set():
            try:
                result = await self._bot(
                    GetUpdates(
                        timeout=self._polling_timeout,
                        marker=self._marker,
                        types=self._allowed_updates or None,
                    )
                )

                for update in result.updates:
                    try:
                        await self._dispatcher.feed_update(self._bot, update)
                    except Exception:
                        logger.exception("Error processing update")

                if result.marker is not None:
                    self._marker = result.marker

                self._backoff.reset()

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Polling error, backing off")
                await self._backoff.wait()

    def stop(self) -> None:
        """Остановить polling."""
        self._stop_signal.set()
