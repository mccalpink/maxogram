"""Тесты MiddlewareManager — управление и onion wrapping middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Any

import pytest

from maxogram.dispatcher.middlewares.base import BaseMiddleware
from maxogram.dispatcher.middlewares.manager import MiddlewareManager


class TestMiddlewareManagerRegister:
    """Тесты регистрации middleware."""

    def test_register_adds_middleware(self) -> None:
        manager = MiddlewareManager()

        async def mw(
            handler: Callable[..., Awaitable[Any]], event: Any, data: dict[str, Any]
        ) -> Any:
            return await handler(event, data)

        manager.register(mw)
        assert len(manager) == 1
        assert manager[0] is mw

    def test_register_returns_middleware(self) -> None:
        manager = MiddlewareManager()

        async def mw(
            handler: Callable[..., Awaitable[Any]], event: Any, data: dict[str, Any]
        ) -> Any:
            return await handler(event, data)

        result = manager.register(mw)
        assert result is mw

    def test_register_multiple(self) -> None:
        manager = MiddlewareManager()

        async def mw1(
            handler: Callable[..., Awaitable[Any]], event: Any, data: dict[str, Any]
        ) -> Any:
            return await handler(event, data)

        async def mw2(
            handler: Callable[..., Awaitable[Any]], event: Any, data: dict[str, Any]
        ) -> Any:
            return await handler(event, data)

        manager.register(mw1)
        manager.register(mw2)
        assert len(manager) == 2
        assert manager[0] is mw1
        assert manager[1] is mw2

    def test_register_class_based(self) -> None:
        manager = MiddlewareManager()

        class MyMW(BaseMiddleware):
            async def __call__(
                self,
                handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
                event: Any,
                data: dict[str, Any],
            ) -> Any:
                return await handler(event, data)

        mw = MyMW()
        manager.register(mw)
        assert len(manager) == 1
        assert manager[0] is mw


class TestMiddlewareManagerUnregister:
    """Тесты удаления middleware."""

    def test_unregister_removes_middleware(self) -> None:
        manager = MiddlewareManager()

        async def mw(
            handler: Callable[..., Awaitable[Any]], event: Any, data: dict[str, Any]
        ) -> Any:
            return await handler(event, data)

        manager.register(mw)
        manager.unregister(mw)
        assert len(manager) == 0

    def test_unregister_not_found_raises(self) -> None:
        manager = MiddlewareManager()

        async def mw(
            handler: Callable[..., Awaitable[Any]], event: Any, data: dict[str, Any]
        ) -> Any:
            return await handler(event, data)

        with pytest.raises(ValueError):
            manager.unregister(mw)


class TestMiddlewareManagerDecorator:
    """Тесты __call__ — декоратор и прямая регистрация."""

    def test_call_direct_registration(self) -> None:
        manager = MiddlewareManager()

        async def mw(
            handler: Callable[..., Awaitable[Any]], event: Any, data: dict[str, Any]
        ) -> Any:
            return await handler(event, data)

        result = manager(mw)
        assert result is mw
        assert len(manager) == 1

    def test_call_as_decorator_without_args(self) -> None:
        manager = MiddlewareManager()

        @manager()
        async def mw(
            handler: Callable[..., Awaitable[Any]], event: Any, data: dict[str, Any]
        ) -> Any:
            return await handler(event, data)

        assert len(manager) == 1
        assert manager[0] is mw

    def test_call_as_decorator_with_direct_pass(self) -> None:
        manager = MiddlewareManager()

        @manager
        async def mw(
            handler: Callable[..., Awaitable[Any]], event: Any, data: dict[str, Any]
        ) -> Any:
            return await handler(event, data)

        assert len(manager) == 1
        assert manager[0] is mw


class TestMiddlewareManagerSequence:
    """MiddlewareManager как Sequence."""

    def test_is_sequence(self) -> None:
        manager = MiddlewareManager()
        assert isinstance(manager, Sequence)

    def test_len_empty(self) -> None:
        manager = MiddlewareManager()
        assert len(manager) == 0

    def test_getitem(self) -> None:
        manager = MiddlewareManager()

        async def mw(
            handler: Callable[..., Awaitable[Any]], event: Any, data: dict[str, Any]
        ) -> Any:
            return await handler(event, data)

        manager.register(mw)
        assert manager[0] is mw

    def test_iteration(self) -> None:
        manager = MiddlewareManager()

        async def mw1(
            handler: Callable[..., Awaitable[Any]], event: Any, data: dict[str, Any]
        ) -> Any:
            return await handler(event, data)

        async def mw2(
            handler: Callable[..., Awaitable[Any]], event: Any, data: dict[str, Any]
        ) -> Any:
            return await handler(event, data)

        manager.register(mw1)
        manager.register(mw2)
        items = list(manager)
        assert items == [mw1, mw2]

    def test_contains(self) -> None:
        manager = MiddlewareManager()

        async def mw(
            handler: Callable[..., Awaitable[Any]], event: Any, data: dict[str, Any]
        ) -> Any:
            return await handler(event, data)

        manager.register(mw)
        assert mw in manager

    def test_eq_empty(self) -> None:
        """Пустой MiddlewareManager сравнивается с пустым списком."""
        manager = MiddlewareManager()
        assert manager == []


class TestWrapMiddlewares:
    """wrap_middlewares — построение onion chain."""

    @pytest.mark.asyncio
    async def test_no_middlewares_calls_handler_directly(self) -> None:
        called_with: dict[str, Any] = {}

        async def handler(event: Any, **kwargs: Any) -> str:
            called_with.update(kwargs)
            return "direct"

        wrapped = MiddlewareManager.wrap_middlewares([], handler)
        result = await wrapped("event", {"key": "val"})
        assert result == "direct"
        assert called_with["key"] == "val"

    @pytest.mark.asyncio
    async def test_single_middleware_wraps_handler(self) -> None:
        order: list[str] = []

        async def mw(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            order.append("mw_before")
            result = await handler(event, data)
            order.append("mw_after")
            return result

        async def handler(event: Any, **kwargs: Any) -> str:
            order.append("handler")
            return "ok"

        wrapped = MiddlewareManager.wrap_middlewares([mw], handler)
        result = await wrapped("event", {})
        assert result == "ok"
        assert order == ["mw_before", "handler", "mw_after"]

    @pytest.mark.asyncio
    async def test_multiple_middlewares_onion_order(self) -> None:
        """Порядок: mw1 → mw2 → handler → mw2 → mw1."""
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

        async def handler(event: Any, **kwargs: Any) -> str:
            order.append("handler")
            return "ok"

        wrapped = MiddlewareManager.wrap_middlewares([mw1, mw2], handler)
        result = await wrapped("event", {})
        assert result == "ok"
        assert order == [
            "mw1_before",
            "mw2_before",
            "handler",
            "mw2_after",
            "mw1_after",
        ]

    @pytest.mark.asyncio
    async def test_middleware_can_interrupt_chain(self) -> None:
        handler_called = False

        async def blocking_mw(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            return "blocked"

        async def handler(event: Any, **kwargs: Any) -> str:
            nonlocal handler_called
            handler_called = True
            return "ok"

        wrapped = MiddlewareManager.wrap_middlewares([blocking_mw], handler)
        result = await wrapped("event", {})
        assert result == "blocked"
        assert handler_called is False

    @pytest.mark.asyncio
    async def test_middleware_can_modify_data(self) -> None:
        received_kwargs: dict[str, Any] = {}

        async def enriching_mw(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            data["injected"] = "from_mw"
            return await handler(event, data)

        async def handler(event: Any, **kwargs: Any) -> str:
            received_kwargs.update(kwargs)
            return "ok"

        wrapped = MiddlewareManager.wrap_middlewares([enriching_mw], handler)
        await wrapped("event", {})
        assert received_kwargs["injected"] == "from_mw"

    @pytest.mark.asyncio
    async def test_middleware_can_modify_result(self) -> None:
        async def modifying_mw(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            result = await handler(event, data)
            return f"modified_{result}"

        async def handler(event: Any, **kwargs: Any) -> str:
            return "original"

        wrapped = MiddlewareManager.wrap_middlewares([modifying_mw], handler)
        result = await wrapped("event", {})
        assert result == "modified_original"

    @pytest.mark.asyncio
    async def test_class_based_middleware_in_chain(self) -> None:
        order: list[str] = []

        class MyMW(BaseMiddleware):
            async def __call__(
                self,
                handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
                event: Any,
                data: dict[str, Any],
            ) -> Any:
                order.append("class_mw")
                return await handler(event, data)

        async def handler(event: Any, **kwargs: Any) -> str:
            order.append("handler")
            return "ok"

        wrapped = MiddlewareManager.wrap_middlewares([MyMW()], handler)
        result = await wrapped("event", {})
        assert result == "ok"
        assert order == ["class_mw", "handler"]
