"""ChatActionSender — периодическая отправка chat actions (typing и т.д.)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Self

from maxogram.enums import SenderAction

if TYPE_CHECKING:
    from maxogram.client.bot import Bot

__all__ = ["ChatActionSender"]

logger = logging.getLogger(__name__)

_DEFAULT_INTERVAL: float = 5.0


class ChatActionSender:
    """Async context manager для периодической отправки chat actions.

    Отправляет action сразу при входе и затем каждые ``interval`` секунд,
    пока пользовательский код работает внутри ``async with``.

    Использование::

        async with ChatActionSender(bot=bot, chat_id=chat_id, action=SenderAction.TYPING_ON):
            result = await heavy_computation()
            await bot.send_message(chat_id=chat_id, text=result)

    Shortcut-методы::

        async with ChatActionSender.typing(bot=bot, chat_id=chat_id):
            ...
    """

    def __init__(
        self,
        *,
        bot: Bot,
        chat_id: int,
        action: SenderAction,
        interval: float = _DEFAULT_INTERVAL,
    ) -> None:
        self.bot = bot
        self.chat_id = chat_id
        self.action = action
        self.interval = interval
        self._task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> Self:
        """Запустить периодическую отправку action."""
        self._task = asyncio.create_task(self._worker())
        return self

    async def __aexit__(self, *args: object) -> None:
        """Остановить периодическую отправку."""
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _worker(self) -> None:
        """Фоновая задача: отправка action с интервалом."""
        try:
            while True:
                await self._send_action()
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            return

    async def _send_action(self) -> None:
        """Одна отправка action, ошибки подавляются."""
        try:
            await self.bot.send_action(chat_id=self.chat_id, action=self.action)
        except Exception:
            logger.warning(
                "Failed to send action %s to chat %s",
                self.action,
                self.chat_id,
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # Shortcut class methods
    # ------------------------------------------------------------------

    @classmethod
    def typing(cls, *, bot: Bot, chat_id: int, interval: float = _DEFAULT_INTERVAL) -> Self:
        """Shortcut для TYPING_ON."""
        return cls(bot=bot, chat_id=chat_id, action=SenderAction.TYPING_ON, interval=interval)

    @classmethod
    def upload_photo(cls, *, bot: Bot, chat_id: int, interval: float = _DEFAULT_INTERVAL) -> Self:
        """Shortcut для SENDING_PHOTO."""
        return cls(bot=bot, chat_id=chat_id, action=SenderAction.SENDING_PHOTO, interval=interval)

    @classmethod
    def upload_video(cls, *, bot: Bot, chat_id: int, interval: float = _DEFAULT_INTERVAL) -> Self:
        """Shortcut для SENDING_VIDEO."""
        return cls(bot=bot, chat_id=chat_id, action=SenderAction.SENDING_VIDEO, interval=interval)

    @classmethod
    def upload_audio(cls, *, bot: Bot, chat_id: int, interval: float = _DEFAULT_INTERVAL) -> Self:
        """Shortcut для SENDING_AUDIO."""
        return cls(bot=bot, chat_id=chat_id, action=SenderAction.SENDING_AUDIO, interval=interval)

    @classmethod
    def upload_file(cls, *, bot: Bot, chat_id: int, interval: float = _DEFAULT_INTERVAL) -> Self:
        """Shortcut для SENDING_FILE."""
        return cls(bot=bot, chat_id=chat_id, action=SenderAction.SENDING_FILE, interval=interval)
