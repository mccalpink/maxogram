"""Тесты типа Callback — shortcuts и сериализация."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from maxogram.types.callback import Callback
from maxogram.types.message import NewMessageBody


def _make_callback(**kwargs: object) -> Callback:
    """Создать Callback с минимальными полями."""
    defaults = {
        "timestamp": 1700000000,
        "callback_id": "cb_123",
        "payload": "test",
        "user": {"user_id": 1, "name": "Test", "is_bot": False, "last_activity_time": 0},
    }
    defaults.update(kwargs)
    return Callback.model_validate(defaults)


class TestCallbackAnswer:
    """Callback.answer() — shortcut для bot.answer_on_callback()."""

    @pytest.mark.asyncio
    async def test_answer_without_args_sends_empty_notification(self) -> None:
        """answer() без аргументов отправляет notification="" (Max API требует)."""
        cb = _make_callback()
        bot = MagicMock()
        bot.answer_on_callback = AsyncMock(return_value=MagicMock())
        cb.set_bot(bot)

        await cb.answer()

        bot.answer_on_callback.assert_called_once_with(
            callback_id="cb_123",
            notification="",
            message=None,
        )

    @pytest.mark.asyncio
    async def test_answer_with_notification(self) -> None:
        """answer(notification="text") передаёт notification as-is."""
        cb = _make_callback()
        bot = MagicMock()
        bot.answer_on_callback = AsyncMock(return_value=MagicMock())
        cb.set_bot(bot)

        await cb.answer(notification="Готово!")

        bot.answer_on_callback.assert_called_once_with(
            callback_id="cb_123",
            notification="Готово!",
            message=None,
        )

    @pytest.mark.asyncio
    async def test_answer_with_message(self) -> None:
        """answer(message=...) передаёт message, notification остаётся None."""
        cb = _make_callback()
        bot = MagicMock()
        bot.answer_on_callback = AsyncMock(return_value=MagicMock())
        cb.set_bot(bot)

        msg = NewMessageBody(text="Response")
        await cb.answer(message=msg)

        bot.answer_on_callback.assert_called_once_with(
            callback_id="cb_123",
            notification=None,
            message=msg,
        )

    @pytest.mark.asyncio
    async def test_answer_without_bot_raises(self) -> None:
        """answer() без привязанного Bot — RuntimeError."""
        cb = _make_callback()

        with pytest.raises(RuntimeError, match="not bound"):
            await cb.answer()
