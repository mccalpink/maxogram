"""Тесты CallbackAnswerMiddleware — авто-ответ на callback."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from maxogram.dispatcher.middlewares.callback_answer import CallbackAnswerMiddleware
from maxogram.types.callback import Callback
from maxogram.types.update import MessageCallbackUpdate


def _make_callback_update(callback_id: str = "cb-1") -> MessageCallbackUpdate:
    """Создать MessageCallbackUpdate с замоканным callback."""
    user_data = {
        "user_id": 1,
        "name": "Test User",
        "username": "test",
        "is_bot": False,
        "last_activity_time": 1000,
    }
    cb = Callback(timestamp=1000, callback_id=callback_id, user=user_data)
    bot = AsyncMock()
    bot.answer_on_callback = AsyncMock()
    cb.set_bot(bot)
    update = MessageCallbackUpdate(timestamp=1000, callback=cb)
    return update


class TestAutoAnswer:
    """Middleware отправляет auto-answer если хендлер не ответил."""

    @pytest.mark.asyncio
    async def test_auto_answer_when_handler_does_not_answer(self) -> None:
        """Если хендлер не вызвал callback.answer(), middleware отправляет пустой answer."""
        mw = CallbackAnswerMiddleware()
        update = _make_callback_update()
        bot = update.callback._bot

        async def handler(event: Any, data: dict[str, Any]) -> None:
            pass  # Не вызываем callback.answer()

        await mw(handler, update, {"bot": bot})

        bot.answer_on_callback.assert_awaited_once_with(callback_id="cb-1")

    @pytest.mark.asyncio
    async def test_no_auto_answer_when_handler_answered(self) -> None:
        """Если хендлер вызвал callback.answer(), middleware НЕ отправляет повторный answer."""
        mw = CallbackAnswerMiddleware()
        update = _make_callback_update()
        bot = update.callback._bot

        async def handler(event: Any, data: dict[str, Any]) -> None:
            data["_callback_answered"] = True

        await mw(handler, update, {"bot": bot})

        bot.answer_on_callback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_flag_injected_into_data(self) -> None:
        """Middleware добавляет _callback_answered=False в data перед хендлером."""
        mw = CallbackAnswerMiddleware()
        update = _make_callback_update()
        bot = update.callback._bot
        captured_data: dict[str, Any] = {}

        async def handler(event: Any, data: dict[str, Any]) -> None:
            captured_data.update(data)

        await mw(handler, update, {"bot": bot})

        assert "_callback_answered" in captured_data
        assert captured_data["_callback_answered"] is False


class TestHandlerResult:
    """Middleware корректно возвращает результат хендлера."""

    @pytest.mark.asyncio
    async def test_returns_handler_result(self) -> None:
        """Результат хендлера прокидывается наверх."""
        mw = CallbackAnswerMiddleware()
        update = _make_callback_update()
        bot = update.callback._bot

        async def handler(event: Any, data: dict[str, Any]) -> str:
            return "handler_result"

        result = await mw(handler, update, {"bot": bot})
        assert result == "handler_result"


class TestHandlerError:
    """Middleware корректно обрабатывает ошибки хендлера."""

    @pytest.mark.asyncio
    async def test_auto_answer_on_handler_error(self) -> None:
        """При ошибке хендлера — auto-answer всё равно отправляется, ошибка пробрасывается."""
        mw = CallbackAnswerMiddleware()
        update = _make_callback_update()
        bot = update.callback._bot

        async def handler(event: Any, data: dict[str, Any]) -> None:
            msg = "handler failed"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="handler failed"):
            await mw(handler, update, {"bot": bot})

        bot.answer_on_callback.assert_awaited_once_with(callback_id="cb-1")

    @pytest.mark.asyncio
    async def test_no_double_answer_on_error(self) -> None:
        """Если хендлер ответил, а потом упал — повторный answer не отправляется."""
        mw = CallbackAnswerMiddleware()
        update = _make_callback_update()
        bot = update.callback._bot

        async def handler(event: Any, data: dict[str, Any]) -> None:
            data["_callback_answered"] = True
            msg = "handler failed after answer"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="handler failed after answer"):
            await mw(handler, update, {"bot": bot})

        bot.answer_on_callback.assert_not_awaited()


class TestCustomCallbackId:
    """Middleware работает с разными callback_id."""

    @pytest.mark.asyncio
    async def test_uses_correct_callback_id(self) -> None:
        """Auto-answer использует callback_id из события."""
        mw = CallbackAnswerMiddleware()
        update = _make_callback_update(callback_id="custom-id-42")
        bot = update.callback._bot

        async def handler(event: Any, data: dict[str, Any]) -> None:
            pass

        await mw(handler, update, {"bot": bot})

        bot.answer_on_callback.assert_awaited_once_with(callback_id="custom-id-42")


class TestAutoAnswerSilentOnApiError:
    """Ошибка auto-answer не маскирует результат хендлера."""

    @pytest.mark.asyncio
    async def test_api_error_during_auto_answer_is_suppressed(self) -> None:
        """Если API вернул ошибку на auto-answer, она подавляется (логируется)."""
        mw = CallbackAnswerMiddleware()
        update = _make_callback_update()
        bot = update.callback._bot
        bot.answer_on_callback.side_effect = Exception("API error")

        async def handler(event: Any, data: dict[str, Any]) -> str:
            return "ok"

        # Не должно бросать исключение
        result = await mw(handler, update, {"bot": bot})
        assert result == "ok"
