"""Тесты MaxEventObserver — observer для событий Max API."""

from __future__ import annotations

from typing import Any

import pytest

from maxogram.dispatcher.event.bases import UNHANDLED, SkipHandler
from maxogram.dispatcher.event.handler import HandlerObject
from maxogram.dispatcher.event.max import MaxEventObserver


class TestMaxEventObserverInit:
    """Тесты инициализации."""

    def test_default_event_name(self) -> None:
        observer = MaxEventObserver()
        assert observer.event_name == ""

    def test_custom_event_name(self) -> None:
        observer = MaxEventObserver(event_name="message_created")
        assert observer.event_name == "message_created"

    def test_router_stored(self) -> None:
        sentinel = object()
        observer = MaxEventObserver(router=sentinel)
        assert observer.router is sentinel

    def test_empty_handlers(self) -> None:
        observer = MaxEventObserver()
        assert observer.handlers == []

    def test_empty_middleware(self) -> None:
        observer = MaxEventObserver()
        assert observer.middleware == []
        assert observer.outer_middleware == []


class TestMaxEventObserverRegister:
    """Тесты регистрации хендлеров."""

    def test_register_adds_handler(self) -> None:
        observer = MaxEventObserver()

        async def callback(event: object) -> None: ...

        observer.register(callback)
        assert len(observer.handlers) == 1

    def test_register_returns_callback(self) -> None:
        observer = MaxEventObserver()

        async def callback(event: object) -> None: ...

        result = observer.register(callback)
        assert result is callback

    def test_register_with_filters(self) -> None:
        observer = MaxEventObserver()

        async def callback(event: object) -> None: ...
        async def my_filter(event: object) -> bool:
            return True

        observer.register(callback, my_filter)
        handler = observer.handlers[0]
        assert handler.filters is not None
        assert len(handler.filters) == 1

    def test_register_with_multiple_filters(self) -> None:
        observer = MaxEventObserver()

        async def callback(event: object) -> None: ...
        async def f1(event: object) -> bool:
            return True
        async def f2(event: object) -> bool:
            return True

        observer.register(callback, f1, f2)
        handler = observer.handlers[0]
        assert handler.filters is not None
        assert len(handler.filters) == 2

    def test_register_with_flags(self) -> None:
        observer = MaxEventObserver()

        async def callback(event: object) -> None: ...

        observer.register(callback, flags={"rate_limit": "default"})
        handler = observer.handlers[0]
        assert handler.flags == {"rate_limit": "default"}

    def test_register_no_filters_none(self) -> None:
        observer = MaxEventObserver()

        async def callback(event: object) -> None: ...

        observer.register(callback)
        handler = observer.handlers[0]
        assert handler.filters is None


class TestMaxEventObserverDecorator:
    """Тесты декоратора __call__."""

    def test_decorator_without_filters(self) -> None:
        observer = MaxEventObserver()

        @observer()
        async def callback(event: object) -> None: ...

        assert len(observer.handlers) == 1

    def test_decorator_with_filters(self) -> None:
        observer = MaxEventObserver()

        async def my_filter(event: object) -> bool:
            return True

        @observer(my_filter)
        async def callback(event: object) -> None: ...

        handler = observer.handlers[0]
        assert handler.filters is not None
        assert len(handler.filters) == 1

    def test_decorator_with_flags(self) -> None:
        observer = MaxEventObserver()

        @observer(flags={"throttle": True})
        async def callback(event: object) -> None: ...

        handler = observer.handlers[0]
        assert handler.flags == {"throttle": True}

    def test_decorator_returns_original_callback(self) -> None:
        observer = MaxEventObserver()

        async def callback(event: object) -> None: ...

        result = observer()(callback)
        assert result is callback


class TestMaxEventObserverTrigger:
    """Тесты вызова trigger."""

    @pytest.mark.asyncio
    async def test_trigger_no_filters_first_handler_called(self) -> None:
        observer = MaxEventObserver()
        called = False

        async def callback(event: object) -> str:
            nonlocal called
            called = True
            return "ok"

        observer.register(callback)
        event = object()
        result = await observer.trigger(event)

        assert called is True
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_trigger_with_passing_filter(self) -> None:
        observer = MaxEventObserver()

        async def my_filter(event: object) -> bool:
            return True

        async def callback(event: object) -> str:
            return "handled"

        observer.register(callback, my_filter)
        result = await observer.trigger(object())
        assert result == "handled"

    @pytest.mark.asyncio
    async def test_trigger_with_failing_filter(self) -> None:
        observer = MaxEventObserver()

        async def my_filter(event: object) -> bool:
            return False

        async def callback(event: object) -> str:
            return "handled"

        observer.register(callback, my_filter)
        result = await observer.trigger(object())
        assert result is UNHANDLED

    @pytest.mark.asyncio
    async def test_trigger_all_rejected_returns_unhandled(self) -> None:
        observer = MaxEventObserver()

        async def reject_filter(event: object) -> bool:
            return False

        async def cb1(event: object) -> str:
            return "cb1"

        async def cb2(event: object) -> str:
            return "cb2"

        observer.register(cb1, reject_filter)
        observer.register(cb2, reject_filter)
        result = await observer.trigger(object())
        assert result is UNHANDLED

    @pytest.mark.asyncio
    async def test_trigger_skip_handler_goes_to_next(self) -> None:
        observer = MaxEventObserver()

        async def skipping_handler(event: object) -> None:
            raise SkipHandler

        async def fallback_handler(event: object) -> str:
            return "fallback"

        observer.register(skipping_handler)
        observer.register(fallback_handler)
        result = await observer.trigger(object())
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_trigger_skip_all_returns_unhandled(self) -> None:
        observer = MaxEventObserver()

        async def skipping(event: object) -> None:
            raise SkipHandler

        observer.register(skipping)
        result = await observer.trigger(object())
        assert result is UNHANDLED

    @pytest.mark.asyncio
    async def test_trigger_dict_enrichment_passed_to_handler(self) -> None:
        observer = MaxEventObserver()
        received_kwargs: dict[str, Any] = {}

        async def enriching_filter(event: object) -> dict[str, str]:
            return {"extra": "value"}

        async def callback(event: object, extra: str = "") -> str:
            received_kwargs["extra"] = extra
            return "ok"

        observer.register(callback, enriching_filter)
        await observer.trigger(object())
        assert received_kwargs["extra"] == "value"

    @pytest.mark.asyncio
    async def test_trigger_sets_handler_in_kwargs(self) -> None:
        observer = MaxEventObserver()
        received_handler: list[Any] = []

        async def callback(event: object, handler: HandlerObject = None) -> str:  # type: ignore[assignment]
            received_handler.append(handler)
            return "ok"

        observer.register(callback)
        await observer.trigger(object())
        assert len(received_handler) == 1
        assert isinstance(received_handler[0], HandlerObject)

    @pytest.mark.asyncio
    async def test_trigger_first_matching_handler_wins(self) -> None:
        observer = MaxEventObserver()

        async def pass_filter(event: object) -> bool:
            return True

        async def cb1(event: object) -> str:
            return "first"

        async def cb2(event: object) -> str:
            return "second"

        observer.register(cb1, pass_filter)
        observer.register(cb2, pass_filter)
        result = await observer.trigger(object())
        assert result == "first"

    @pytest.mark.asyncio
    async def test_trigger_empty_handlers_returns_unhandled(self) -> None:
        observer = MaxEventObserver()
        result = await observer.trigger(object())
        assert result is UNHANDLED


class TestMaxEventObserverRootFilter:
    """Тесты root filters."""

    def test_filter_adds_root_filters(self) -> None:
        observer = MaxEventObserver()

        async def my_filter(event: object) -> bool:
            return True

        observer.filter(my_filter)
        assert observer._handler.filters is not None
        assert len(observer._handler.filters) == 1

    @pytest.mark.asyncio
    async def test_root_filter_passes(self) -> None:
        observer = MaxEventObserver()

        async def allow(event: object) -> bool:
            return True

        async def callback(event: object) -> str:
            return "ok"

        observer.filter(allow)
        observer.register(callback)
        result = await observer.trigger(object())
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_root_filter_rejects_returns_unhandled(self) -> None:
        observer = MaxEventObserver()

        async def deny(event: object) -> bool:
            return False

        async def callback(event: object) -> str:
            return "ok"

        observer.filter(deny)
        observer.register(callback)
        result = await observer.trigger(object())
        assert result is UNHANDLED

    @pytest.mark.asyncio
    async def test_root_filter_enrichment_passed(self) -> None:
        observer = MaxEventObserver()
        received: dict[str, Any] = {}

        async def enriching_root(event: object) -> dict[str, str]:
            return {"root_extra": "from_root"}

        async def callback(event: object, root_extra: str = "") -> str:
            received["root_extra"] = root_extra
            return "ok"

        observer.filter(enriching_root)
        observer.register(callback)
        await observer.trigger(object())
        assert received["root_extra"] == "from_root"

    def test_filter_multiple_root_filters(self) -> None:
        observer = MaxEventObserver()

        async def f1(event: object) -> bool:
            return True
        async def f2(event: object) -> bool:
            return True

        observer.filter(f1, f2)
        assert observer._handler.filters is not None
        assert len(observer._handler.filters) == 2
