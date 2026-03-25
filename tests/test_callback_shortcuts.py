"""Тесты shortcut-методов Callback (answer)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from maxogram.types.callback import Callback
from maxogram.types.message import NewMessageBody

CALLBACK_JSON = {
    "timestamp": 1711000000000,
    "callback_id": "cb_12345",
    "payload": "btn_action",
    "user": {
        "user_id": 111,
        "name": "Иван",
        "is_bot": False,
        "last_activity_time": 1711000000000,
    },
}


def _make_callback(*, with_bot: bool = True) -> Callback:
    """Создать Callback, опционально привязав mock Bot."""
    cb = Callback.model_validate(CALLBACK_JSON)
    if with_bot:
        bot = AsyncMock()
        bot.answer_on_callback = AsyncMock()
        cb.set_bot(bot)
    return cb


class TestCallbackAnswer:
    """Callback.answer() — ответ на callback."""

    @pytest.mark.asyncio
    async def test_answer_empty(self) -> None:
        """answer() без аргументов подставляет notification="" (Max API требует)."""
        cb = _make_callback()
        await cb.answer()
        cb.bot.answer_on_callback.assert_called_once_with(
            callback_id="cb_12345",
            notification="",
            message=None,
        )

    @pytest.mark.asyncio
    async def test_answer_with_notification(self) -> None:
        cb = _make_callback()
        await cb.answer(notification="Готово!")
        cb.bot.answer_on_callback.assert_called_once_with(
            callback_id="cb_12345",
            notification="Готово!",
            message=None,
        )

    @pytest.mark.asyncio
    async def test_answer_with_message(self) -> None:
        cb = _make_callback()
        body = NewMessageBody(text="Обновлено")
        await cb.answer(message=body)
        cb.bot.answer_on_callback.assert_called_once_with(
            callback_id="cb_12345",
            notification=None,
            message=body,
        )


class TestCallbackGetBotError:
    """Ошибка при отсутствии Bot."""

    @pytest.mark.asyncio
    async def test_answer_without_bot(self) -> None:
        cb = _make_callback(with_bot=False)
        with pytest.raises(RuntimeError, match="not bound to a Bot"):
            await cb.answer()
