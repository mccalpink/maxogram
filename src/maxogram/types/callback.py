"""Типы callback Max API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from maxogram.types.base import MaxObject
from maxogram.types.message import NewMessageBody
from maxogram.types.user import User

if TYPE_CHECKING:
    from maxogram.client.bot import Bot
    from maxogram.types.misc import SimpleQueryResult


class Callback(MaxObject):
    """Callback от нажатия inline-кнопки."""

    timestamp: int
    callback_id: str
    payload: str | None = None
    user: User

    def _get_bot(self) -> Bot:
        """Получить Bot или поднять RuntimeError."""
        if self._bot is None:
            msg = "Callback is not bound to a Bot."
            raise RuntimeError(msg)
        return self._bot  # type: ignore[no-any-return]

    async def answer(
        self,
        *,
        notification: str | None = None,
        message: NewMessageBody | None = None,
    ) -> SimpleQueryResult:
        """Ответить на callback.

        Если не указаны ни notification, ни message — отправляет пустой
        notification (Max API требует хотя бы одно из полей).
        """
        bot = self._get_bot()
        # Max API требует хотя бы notification или message
        if notification is None and message is None:
            notification = ""
        return await bot.answer_on_callback(
            callback_id=self.callback_id,
            notification=notification,
            message=message,
        )


class CallbackAnswer(MaxObject):
    """Ответ на callback (POST /answers)."""

    message: NewMessageBody | None = None
    notification: str | None = None
