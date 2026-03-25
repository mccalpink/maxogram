"""Тесты BaseMiddleware — абстрактный базовый класс middleware."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

import pytest

from maxogram.dispatcher.middlewares.base import BaseMiddleware


class TestBaseMiddlewareAbstract:
    """BaseMiddleware — абстрактный, нельзя инстанцировать напрямую."""

    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            BaseMiddleware()  # type: ignore[abstract]

    def test_is_abstract(self) -> None:
        import abc

        assert abc.ABC in BaseMiddleware.__mro__


class TestBaseMiddlewareSubclass:
    """Подкласс BaseMiddleware — работает корректно."""

    def test_subclass_instantiates(self) -> None:
        class MyMiddleware(BaseMiddleware):
            async def __call__(
                self,
                handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
                event: Any,
                data: dict[str, Any],
            ) -> Any:
                return await handler(event, data)

        mw = MyMiddleware()
        assert isinstance(mw, BaseMiddleware)

    @pytest.mark.asyncio
    async def test_subclass_passes_through(self) -> None:
        class PassthroughMiddleware(BaseMiddleware):
            async def __call__(
                self,
                handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
                event: Any,
                data: dict[str, Any],
            ) -> Any:
                return await handler(event, data)

        called = False

        async def fake_handler(event: Any, data: dict[str, Any]) -> str:
            nonlocal called
            called = True
            return "result"

        mw = PassthroughMiddleware()
        result = await mw(fake_handler, "event", {})
        assert called is True
        assert result == "result"

    @pytest.mark.asyncio
    async def test_subclass_can_modify_data(self) -> None:
        class EnrichMiddleware(BaseMiddleware):
            async def __call__(
                self,
                handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
                event: Any,
                data: dict[str, Any],
            ) -> Any:
                data["injected"] = "value"
                return await handler(event, data)

        received_data: dict[str, Any] = {}

        async def fake_handler(event: Any, data: dict[str, Any]) -> str:
            received_data.update(data)
            return "ok"

        mw = EnrichMiddleware()
        await mw(fake_handler, "event", {})
        assert received_data["injected"] == "value"

    @pytest.mark.asyncio
    async def test_subclass_can_interrupt_chain(self) -> None:
        class BlockingMiddleware(BaseMiddleware):
            async def __call__(
                self,
                handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
                event: Any,
                data: dict[str, Any],
            ) -> Any:
                return "blocked"  # Не вызываем handler

        called = False

        async def fake_handler(event: Any, data: dict[str, Any]) -> str:
            nonlocal called
            called = True
            return "result"

        mw = BlockingMiddleware()
        result = await mw(fake_handler, "event", {})
        assert called is False
        assert result == "blocked"


class TestFunctionalMiddleware:
    """Функциональный middleware — callable без наследования."""

    @pytest.mark.asyncio
    async def test_functional_middleware_works(self) -> None:
        async def my_middleware(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            data["from_mw"] = True
            return await handler(event, data)

        received_data: dict[str, Any] = {}

        async def fake_handler(event: Any, data: dict[str, Any]) -> str:
            received_data.update(data)
            return "ok"

        result = await my_middleware(fake_handler, "event", {})
        assert result == "ok"
        assert received_data["from_mw"] is True

    @pytest.mark.asyncio
    async def test_functional_middleware_not_instance_of_base(self) -> None:
        async def my_middleware(
            handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
            event: Any,
            data: dict[str, Any],
        ) -> Any:
            return await handler(event, data)

        assert not isinstance(my_middleware, BaseMiddleware)
