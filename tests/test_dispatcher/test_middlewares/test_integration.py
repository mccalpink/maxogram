"""Интеграционные тесты: middleware + MaxEventObserver."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

import pytest

from maxogram.dispatcher.event.bases import UNHANDLED, SkipHandler
from maxogram.dispatcher.event.max import MaxEventObserver
from maxogram.dispatcher.middlewares.base import BaseMiddleware
from maxogram.dispatcher.middlewares.manager import MiddlewareManager


class TestMaxEventObserverInnerMiddleware:
    """Inner middleware вызывается при trigger."""

    @pytest.mark.asyncio
    async def test_inner_middleware_called_on_trigger(self) -> None:
        observer = MaxEventObserver()
        mw_called = False

        async def my_mw(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            nonlocal mw_called
            mw_called = True
            return await handler(event, data)

        observer.middleware.register(my_mw)

        async def callback(event: object) -> str:
            return "ok"

        observer.register(callback)
        result = await observer.trigger(object())
        assert result == "ok"
        assert mw_called is True

    @pytest.mark.asyncio
    async def test_inner_middleware_onion_order(self) -> None:
        """Inner middleware выполняется в правильном onion-порядке."""
        observer = MaxEventObserver()
        order: list[str] = []

        async def mw1(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            order.append("mw1_before")
            result = await handler(event, data)
            order.append("mw1_after")
            return result

        async def mw2(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            order.append("mw2_before")
            result = await handler(event, data)
            order.append("mw2_after")
            return result

        observer.middleware.register(mw1)
        observer.middleware.register(mw2)

        async def callback(event: object) -> str:
            order.append("handler")
            return "ok"

        observer.register(callback)
        await observer.trigger(object())
        assert order == [
            "mw1_before",
            "mw2_before",
            "handler",
            "mw2_after",
            "mw1_after",
        ]

    @pytest.mark.asyncio
    async def test_inner_middleware_can_inject_data(self) -> None:
        """Inner middleware может добавлять данные в kwargs хендлера."""
        observer = MaxEventObserver()

        async def injecting_mw(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            data["service"] = "injected_service"
            return await handler(event, data)

        observer.middleware.register(injecting_mw)
        received: dict[str, Any] = {}

        async def callback(event: object, service: str = "") -> str:
            received["service"] = service
            return "ok"

        observer.register(callback)
        await observer.trigger(object())
        assert received["service"] == "injected_service"

    @pytest.mark.asyncio
    async def test_inner_middleware_can_block_handler(self) -> None:
        """Inner middleware может прервать цепочку (не вызывать handler)."""
        observer = MaxEventObserver()
        handler_called = False

        async def blocking_mw(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            return "blocked_by_mw"

        observer.middleware.register(blocking_mw)

        async def callback(event: object) -> str:
            nonlocal handler_called
            handler_called = True
            return "ok"

        observer.register(callback)
        result = await observer.trigger(object())
        assert result == "blocked_by_mw"
        assert handler_called is False

    @pytest.mark.asyncio
    async def test_inner_middleware_not_called_when_no_handler_matches(self) -> None:
        """Inner middleware не вызывается если ни один хендлер не подошёл."""
        observer = MaxEventObserver()
        mw_called = False

        async def my_mw(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            nonlocal mw_called
            mw_called = True
            return await handler(event, data)

        observer.middleware.register(my_mw)

        async def reject_filter(event: object) -> bool:
            return False

        async def callback(event: object) -> str:
            return "ok"

        observer.register(callback, reject_filter)
        result = await observer.trigger(object())
        assert result is UNHANDLED
        assert mw_called is False

    @pytest.mark.asyncio
    async def test_inner_middleware_skip_handler_goes_to_next(self) -> None:
        """SkipHandler внутри middleware chain переходит к следующему хендлеру."""
        observer = MaxEventObserver()

        async def skip_mw(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            raise SkipHandler

        observer.middleware.register(skip_mw)

        async def cb1(event: object) -> str:
            return "first"

        async def cb2(event: object) -> str:
            return "second"

        observer.register(cb1)
        observer.register(cb2)
        # mw выбрасывает SkipHandler для обоих хендлеров
        result = await observer.trigger(object())
        assert result is UNHANDLED

    @pytest.mark.asyncio
    async def test_class_based_inner_middleware(self) -> None:
        """Class-based middleware работает с MaxEventObserver."""
        observer = MaxEventObserver()
        order: list[str] = []

        class LogMW(BaseMiddleware):
            async def __call__(
                self,
                handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
                event: Any,
                data: dict[str, Any],
            ) -> Any:
                order.append("log_before")
                result = await handler(event, data)
                order.append("log_after")
                return result

        observer.middleware.register(LogMW())

        async def callback(event: object) -> str:
            order.append("handler")
            return "ok"

        observer.register(callback)
        result = await observer.trigger(object())
        assert result == "ok"
        assert order == ["log_before", "handler", "log_after"]


class TestMaxEventObserverOuterMiddleware:
    """Outer middleware — wrap_outer_middleware."""

    @pytest.mark.asyncio
    async def test_wrap_outer_middleware_no_middlewares(self) -> None:
        observer = MaxEventObserver()

        async def callback(event: Any, **kwargs: Any) -> str:
            return "direct"

        result = await observer.wrap_outer_middleware(callback, "event", {"k": "v"})
        assert result == "direct"

    @pytest.mark.asyncio
    async def test_wrap_outer_middleware_with_middleware(self) -> None:
        observer = MaxEventObserver()
        order: list[str] = []

        async def outer_mw(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            order.append("outer_before")
            result = await handler(event, data)
            order.append("outer_after")
            return result

        observer.outer_middleware.register(outer_mw)

        async def callback(event: Any, **kwargs: Any) -> str:
            order.append("callback")
            return "ok"

        result = await observer.wrap_outer_middleware(callback, "event", {})
        assert result == "ok"
        assert order == ["outer_before", "callback", "outer_after"]


class TestMiddlewareManagerOnObserver:
    """MiddlewareManager как атрибут MaxEventObserver."""

    def test_middleware_is_middleware_manager(self) -> None:
        observer = MaxEventObserver()
        assert isinstance(observer.middleware, MiddlewareManager)
        assert isinstance(observer.outer_middleware, MiddlewareManager)

    def test_middleware_register_via_decorator(self) -> None:
        observer = MaxEventObserver()

        @observer.middleware
        async def my_mw(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            return await handler(event, data)

        assert len(observer.middleware) == 1

    def test_outer_middleware_register_via_call(self) -> None:
        observer = MaxEventObserver()

        async def my_mw(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            return await handler(event, data)

        observer.outer_middleware(my_mw)
        assert len(observer.outer_middleware) == 1
