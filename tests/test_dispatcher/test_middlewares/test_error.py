"""Тесты ErrorsMiddleware и ErrorEvent — перехват ошибок в хендлерах."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from maxogram.dispatcher.event.bases import UNHANDLED, CancelHandler, SkipHandler
from maxogram.dispatcher.middlewares.error import ErrorEvent, ErrorsMiddleware


class TestErrorEvent:
    """ErrorEvent — обёртка над исключением и оригинальным событием."""

    def test_stores_update_and_exception(self) -> None:
        update = {"type": "message_created"}
        exc = ValueError("test error")
        error_event = ErrorEvent(update=update, exception=exc)
        assert error_event.update is update
        assert error_event.exception is exc

    def test_stores_different_exception_types(self) -> None:
        exc = RuntimeError("runtime")
        error_event = ErrorEvent(update="some_event", exception=exc)
        assert isinstance(error_event.exception, RuntimeError)

    def test_repr(self) -> None:
        exc = ValueError("boom")
        error_event = ErrorEvent(update="ev", exception=exc)
        r = repr(error_event)
        assert "ErrorEvent" in r
        assert "ValueError" in r


class TestErrorsMiddlewareNoError:
    """Handler без ошибок — ErrorsMiddleware прозрачно пропускает."""

    @pytest.mark.asyncio
    async def test_passthrough_on_success(self) -> None:
        router = AsyncMock()
        mw = ErrorsMiddleware(router=router)

        async def handler(event: Any, data: dict[str, Any]) -> str:
            return "ok"

        result = await mw(handler, "event", {})
        assert result == "ok"
        router.propagate_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_passthrough_preserves_return_value(self) -> None:
        router = AsyncMock()
        mw = ErrorsMiddleware(router=router)

        async def handler(event: Any, data: dict[str, Any]) -> dict[str, int]:
            return {"count": 42}

        result = await mw(handler, "event", {})
        assert result == {"count": 42}


class TestErrorsMiddlewareFlowControl:
    """SkipHandler и CancelHandler пробрасываются без обработки."""

    @pytest.mark.asyncio
    async def test_skip_handler_propagates(self) -> None:
        router = AsyncMock()
        mw = ErrorsMiddleware(router=router)

        async def handler(event: Any, data: dict[str, Any]) -> None:
            raise SkipHandler

        with pytest.raises(SkipHandler):
            await mw(handler, "event", {})
        router.propagate_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_handler_propagates(self) -> None:
        router = AsyncMock()
        mw = ErrorsMiddleware(router=router)

        async def handler(event: Any, data: dict[str, Any]) -> None:
            raise CancelHandler

        with pytest.raises(CancelHandler):
            await mw(handler, "event", {})
        router.propagate_event.assert_not_called()


class TestErrorsMiddlewareErrorHandling:
    """Перехват исключений и перенаправление к error handlers."""

    @pytest.mark.asyncio
    async def test_error_calls_propagate_event(self) -> None:
        """ValueError → propagate_event('error', ErrorEvent(...))."""
        router = AsyncMock()
        router.propagate_event.return_value = "handled"
        mw = ErrorsMiddleware(router=router)

        async def handler(event: Any, data: dict[str, Any]) -> None:
            raise ValueError("test error")

        result = await mw(handler, "test_event", {"key": "val"})
        assert result == "handled"

        router.propagate_event.assert_called_once()
        call_kwargs = router.propagate_event.call_args
        assert call_kwargs.kwargs["update_type"] == "error"
        error_event = call_kwargs.kwargs["event"]
        assert isinstance(error_event, ErrorEvent)
        assert error_event.update == "test_event"
        assert isinstance(error_event.exception, ValueError)
        assert str(error_event.exception) == "test error"

    @pytest.mark.asyncio
    async def test_error_passes_data_to_propagate(self) -> None:
        """Данные из data передаются в propagate_event как **kwargs."""
        router = AsyncMock()
        router.propagate_event.return_value = "handled"
        mw = ErrorsMiddleware(router=router)

        async def handler(event: Any, data: dict[str, Any]) -> None:
            raise RuntimeError("fail")

        await mw(handler, "ev", {"bot": "bot_obj", "state": "some_state"})

        call_kwargs = router.propagate_event.call_args
        assert call_kwargs.kwargs["bot"] == "bot_obj"
        assert call_kwargs.kwargs["state"] == "some_state"

    @pytest.mark.asyncio
    async def test_no_error_handler_reraises(self) -> None:
        """Нет error handler → re-raise оригинального исключения."""
        router = AsyncMock()
        router.propagate_event.return_value = UNHANDLED
        mw = ErrorsMiddleware(router=router)

        async def handler(event: Any, data: dict[str, Any]) -> None:
            raise ValueError("unhandled error")

        with pytest.raises(ValueError, match="unhandled error"):
            await mw(handler, "event", {})

    @pytest.mark.asyncio
    async def test_error_handler_returns_result(self) -> None:
        """Error handler может вернуть результат вместо повторного raise."""
        router = AsyncMock()
        router.propagate_event.return_value = {"fallback": True}
        mw = ErrorsMiddleware(router=router)

        async def handler(event: Any, data: dict[str, Any]) -> None:
            raise TypeError("type error")

        result = await mw(handler, "event", {})
        assert result == {"fallback": True}

    @pytest.mark.asyncio
    async def test_error_handler_returns_none_is_handled(self) -> None:
        """Error handler возвращает None — это валидный результат (не UNHANDLED)."""
        router = AsyncMock()
        router.propagate_event.return_value = None
        mw = ErrorsMiddleware(router=router)

        async def handler(event: Any, data: dict[str, Any]) -> None:
            raise ValueError("err")

        result = await mw(handler, "event", {})
        assert result is None

    @pytest.mark.asyncio
    async def test_keyboard_interrupt_not_caught(self) -> None:
        """BaseException (KeyboardInterrupt) не перехватывается."""
        router = AsyncMock()
        mw = ErrorsMiddleware(router=router)

        async def handler(event: Any, data: dict[str, Any]) -> None:
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            await mw(handler, "event", {})
        router.propagate_event.assert_not_called()


class TestErrorsMiddlewareIntegrationWithRouter:
    """Интеграция ErrorsMiddleware с реальным Router."""

    @pytest.mark.asyncio
    async def test_router_error_observer_exists(self) -> None:
        """Router имеет error observer."""
        from maxogram.dispatcher.router import Router

        router = Router(name="test")
        assert hasattr(router, "error")
        assert hasattr(router, "errors")
        assert router.error is router.errors
        assert "error" in router.observers

    @pytest.mark.asyncio
    async def test_router_error_decorator(self) -> None:
        """router.error() работает как декоратор для error handlers."""
        from maxogram.dispatcher.router import Router

        router = Router(name="test")

        @router.error()
        async def on_error(event: ErrorEvent) -> str:
            return f"caught: {event.exception}"

        assert len(router.error.handlers) == 1

    @pytest.mark.asyncio
    async def test_full_flow_with_router(self) -> None:
        """Полный цикл: handler бросает → ErrorsMiddleware → error handler."""
        from maxogram.dispatcher.router import Router

        router = Router(name="test")
        mw = ErrorsMiddleware(router=router)

        # Регистрируем error handler
        @router.error()
        async def on_error(event: ErrorEvent) -> str:
            return f"handled: {type(event.exception).__name__}"

        # Handler бросает исключение
        async def failing_handler(event: Any, data: dict[str, Any]) -> None:
            raise ValueError("boom")

        result = await mw(failing_handler, "test_event", {})
        assert result == "handled: ValueError"
