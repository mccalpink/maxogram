"""CallbackAnswerMiddleware — авто-ответ на callback если хендлер не ответил."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from maxogram.dispatcher.middlewares.base import BaseMiddleware

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

__all__ = ["CallbackAnswerMiddleware"]

logger = logging.getLogger(__name__)


class CallbackAnswerMiddleware(BaseMiddleware):
    """Автоматический ответ на callback, если хендлер не вызвал его явно.

    Предотвращает «зависшие» кнопки в Max-клиенте.

    Использование::

        router.message_callback.middleware(CallbackAnswerMiddleware())

    Если хендлер хочет ответить сам, он должен вызвать
    ``await callback.answer(...)`` — при этом метод ``answer``
    должен выставить флаг ``data["_callback_answered"] = True``.

    Либо хендлер может вручную установить этот флаг.
    """

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        """Выполнить хендлер и отправить auto-answer при необходимости."""
        data["_callback_answered"] = False

        try:
            result = await handler(event, data)
        except Exception:
            await self._auto_answer_if_needed(event, data)
            raise

        await self._auto_answer_if_needed(event, data)
        return result

    @staticmethod
    async def _auto_answer_if_needed(event: Any, data: dict[str, Any]) -> None:
        """Отправить пустой answer если хендлер не ответил."""
        if data.get("_callback_answered"):
            return

        callback = getattr(event, "callback", None)
        if callback is None:
            return

        callback_id = getattr(callback, "callback_id", None)
        if callback_id is None:
            return

        bot = data.get("bot")
        if bot is None:
            return

        try:
            await bot.answer_on_callback(callback_id=callback_id)
        except Exception:
            logger.warning(
                "Failed to auto-answer callback %s",
                callback_id,
                exc_info=True,
            )
