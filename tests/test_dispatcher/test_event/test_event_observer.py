"""Тесты EventObserver — простой observer для lifecycle-событий."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from maxogram.dispatcher.event.event import EventObserver


class TestEventObserverRegister:
    """Тесты регистрации хендлеров."""

    def test_register_adds_handler(self) -> None:
        observer = EventObserver()

        async def callback() -> None: ...

        observer.register(callback)
        assert len(observer.handlers) == 1

    def test_register_returns_callback(self) -> None:
        observer = EventObserver()

        async def callback() -> None: ...

        result = observer.register(callback)
        assert result is callback

    def test_register_multiple_handlers(self) -> None:
        observer = EventObserver()

        async def cb1() -> None: ...
        async def cb2() -> None: ...
        async def cb3() -> None: ...

        observer.register(cb1)
        observer.register(cb2)
        observer.register(cb3)
        assert len(observer.handlers) == 3


class TestEventObserverDecorator:
    """Тесты декоратора __call__."""

    def test_call_as_decorator(self) -> None:
        observer = EventObserver()

        @observer
        async def callback() -> None: ...

        assert len(observer.handlers) == 1
        assert callback is not None  # декоратор вернул оригинал

    def test_call_returns_original_callback(self) -> None:
        observer = EventObserver()

        async def callback() -> None: ...

        result = observer(callback)
        assert result is callback


class TestEventObserverTrigger:
    """Тесты вызова trigger."""

    @pytest.mark.asyncio
    async def test_trigger_calls_all_handlers(self) -> None:
        observer = EventObserver()
        mock1 = AsyncMock()
        mock2 = AsyncMock()
        mock3 = AsyncMock()
        observer.register(mock1)
        observer.register(mock2)
        observer.register(mock3)

        await observer.trigger()

        mock1.assert_awaited_once()
        mock2.assert_awaited_once()
        mock3.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_trigger_passes_args_and_kwargs(self) -> None:
        observer = EventObserver()
        received: list[tuple[Any, ...]] = []

        async def callback(a: int, b: str) -> None:
            received.append((a, b))

        observer.register(callback)
        await observer.trigger(a=1, b="hello")

        assert received == [(1, "hello")]

    @pytest.mark.asyncio
    async def test_trigger_empty_no_error(self) -> None:
        observer = EventObserver()
        await observer.trigger()  # не падает

    @pytest.mark.asyncio
    async def test_trigger_calls_in_order(self) -> None:
        observer = EventObserver()
        order: list[int] = []

        async def cb1() -> None:
            order.append(1)

        async def cb2() -> None:
            order.append(2)

        async def cb3() -> None:
            order.append(3)

        observer.register(cb1)
        observer.register(cb2)
        observer.register(cb3)

        await observer.trigger()
        assert order == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_trigger_with_positional_args(self) -> None:
        observer = EventObserver()
        received: list[Any] = []

        async def callback(app: object) -> None:
            received.append(app)

        observer.register(callback)
        sentinel = object()
        await observer.trigger(sentinel)

        assert received == [sentinel]
