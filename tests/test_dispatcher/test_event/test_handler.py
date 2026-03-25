"""Тесты CallableObject, FilterObject, HandlerObject."""

from __future__ import annotations

from typing import Any

import pytest
from magic_filter import MagicFilter

from maxogram.dispatcher.event.handler import (
    CallableObject,
    FilterObject,
    HandlerObject,
)
from maxogram.filters.base import Filter

# -- Вспомогательные callable-классы для тестов --


class AsyncCallableNoFilter:
    """Callable-класс с async __call__, НЕ наследующий Filter."""

    async def __call__(self, event: object, **kwargs: Any) -> bool:
        return True


class SyncCallableNoFilter:
    """Callable-класс с sync __call__, НЕ наследующий Filter."""

    def __call__(self, event: object, **kwargs: Any) -> bool:
        return True


class AsyncCallableFilter(Filter):
    """Callable-класс с async __call__, наследующий Filter."""

    async def __call__(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:
        return {"from_async_callable_filter": True}


# -- Вспомогательные функции для тестов --


async def async_func(a: int, b: str) -> str:
    return f"{a}-{b}"


def sync_func(a: int, b: str) -> str:
    return f"{a}-{b}"


async def func_with_varkw(a: int, **kwargs: Any) -> dict[str, Any]:
    return {"a": a, **kwargs}


async def func_keyword_only(a: int, *, c: str) -> str:
    return f"{a}-{c}"


async def func_positional_only(a: int, b: str, /) -> str:
    return f"{a}-{b}"


# -- Тесты CallableObject --


class TestCallableObject:
    """Тесты для CallableObject."""

    def test_async_function_detected(self) -> None:
        obj = CallableObject(callback=async_func)
        assert obj.awaitable is True

    def test_sync_function_detected(self) -> None:
        obj = CallableObject(callback=sync_func)
        assert obj.awaitable is False

    def test_params_extracted(self) -> None:
        obj = CallableObject(callback=async_func)
        assert obj.params == frozenset({"a", "b"})

    def test_varkw_false_by_default(self) -> None:
        obj = CallableObject(callback=async_func)
        assert obj.varkw is False

    def test_varkw_true_when_present(self) -> None:
        obj = CallableObject(callback=func_with_varkw)
        assert obj.varkw is True

    def test_keyword_only_params(self) -> None:
        obj = CallableObject(callback=func_keyword_only)
        assert "c" in obj.params
        assert "a" in obj.params

    def test_positional_only_params(self) -> None:
        obj = CallableObject(callback=func_positional_only)
        assert "a" in obj.params
        assert "b" in obj.params

    def test_prepare_kwargs_filters(self) -> None:
        obj = CallableObject(callback=async_func)
        result = obj._prepare_kwargs({"a": 1, "b": "x", "extra": 99})
        assert result == {"a": 1, "b": "x"}

    def test_prepare_kwargs_passes_all_with_varkw(self) -> None:
        obj = CallableObject(callback=func_with_varkw)
        kwargs = {"a": 1, "b": "x", "extra": 99}
        result = obj._prepare_kwargs(kwargs)
        assert result == kwargs

    def test_prepare_kwargs_missing_param_skipped(self) -> None:
        obj = CallableObject(callback=async_func)
        result = obj._prepare_kwargs({"a": 1})
        assert result == {"a": 1}

    @pytest.mark.asyncio
    async def test_call_async(self) -> None:
        obj = CallableObject(callback=async_func)
        result = await obj.call(a=1, b="hello")
        assert result == "1-hello"

    @pytest.mark.asyncio
    async def test_call_sync_via_thread(self) -> None:
        obj = CallableObject(callback=sync_func)
        result = await obj.call(a=2, b="world")
        assert result == "2-world"

    @pytest.mark.asyncio
    async def test_call_filters_kwargs(self) -> None:
        obj = CallableObject(callback=async_func)
        result = await obj.call(a=1, b="ok", extra=42)
        assert result == "1-ok"

    @pytest.mark.asyncio
    async def test_call_with_positional_args(self) -> None:
        async def handler(event: object, value: int = 0) -> int:
            return value

        obj = CallableObject(callback=handler)
        result = await obj.call("event_obj", value=42)
        assert result == 42

    def test_async_callable_instance_detected(self) -> None:
        """Callable-экземпляр с async __call__ — awaitable=True."""
        obj = CallableObject(callback=AsyncCallableNoFilter())
        assert obj.awaitable is True

    def test_sync_callable_instance_detected(self) -> None:
        """Callable-экземпляр с sync __call__ — awaitable=False."""
        obj = CallableObject(callback=SyncCallableNoFilter())
        assert obj.awaitable is False

    @pytest.mark.asyncio
    async def test_async_callable_instance_call(self) -> None:
        """Callable-экземпляр с async __call__ — корректный вызов."""
        obj = CallableObject(callback=AsyncCallableNoFilter())
        result = await obj.call("event")
        assert result is True

    @pytest.mark.asyncio
    async def test_sync_callable_instance_call(self) -> None:
        """Callable-экземпляр с sync __call__ — вызов через to_thread."""
        obj = CallableObject(callback=SyncCallableNoFilter())
        result = await obj.call("event")
        assert result is True


# -- Тесты FilterObject --


class TestFilterObject:
    """Тесты для FilterObject."""

    def test_regular_callable_no_magic(self) -> None:
        async def my_filter(event: object) -> bool:
            return True

        obj = FilterObject(callback=my_filter)
        assert obj.magic is None
        assert obj.awaitable is True

    def test_magic_filter_detected(self) -> None:
        mf = MagicFilter()
        f = mf.name == "test"
        obj = FilterObject(callback=f)
        assert obj.magic is not None
        assert obj.magic is f

    @pytest.mark.asyncio
    async def test_magic_filter_call_matching(self) -> None:
        mf = MagicFilter()
        f = mf.name == "test"
        obj = FilterObject(callback=f)

        class Event:
            name = "test"

        result = await obj.call(Event())
        assert result is True

    @pytest.mark.asyncio
    async def test_magic_filter_call_not_matching(self) -> None:
        mf = MagicFilter()
        f = mf.name == "test"
        obj = FilterObject(callback=f)

        class Event:
            name = "other"

        result = await obj.call(Event())
        assert result is False

    def test_sync_filter_detected(self) -> None:
        def my_filter(event: object) -> bool:
            return True

        obj = FilterObject(callback=my_filter)
        assert obj.awaitable is False

    def test_filter_abc_instance_awaitable(self) -> None:
        """FilterObject с экземпляром Filter ABC — awaitable=True."""

        class MyFilter(Filter):
            async def __call__(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:
                return True

        obj = FilterObject(callback=MyFilter())
        assert obj.awaitable is True

    @pytest.mark.asyncio
    async def test_filter_abc_instance_call(self) -> None:
        """FilterObject с экземпляром Filter ABC — корректный вызов."""

        class MyFilter(Filter):
            async def __call__(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:
                return {"from_filter": "value"}

        obj = FilterObject(callback=MyFilter())
        result = await obj.call("event")
        assert result == {"from_filter": "value"}

    def test_async_callable_no_filter_awaitable(self) -> None:
        """FilterObject с async callable БЕЗ наследования от Filter — awaitable=True."""
        obj = FilterObject(callback=AsyncCallableNoFilter())
        assert obj.awaitable is True

    @pytest.mark.asyncio
    async def test_async_callable_no_filter_call(self) -> None:
        """FilterObject с async callable БЕЗ наследования от Filter — корректный вызов."""
        obj = FilterObject(callback=AsyncCallableNoFilter())
        result = await obj.call("event")
        assert result is True

    def test_async_callable_filter_subclass_awaitable(self) -> None:
        """FilterObject: async callable + Filter — awaitable=True (регрессия)."""
        obj = FilterObject(callback=AsyncCallableFilter())
        assert obj.awaitable is True

    @pytest.mark.asyncio
    async def test_async_callable_filter_subclass_call(self) -> None:
        """FilterObject с async callable-классом, наследующим Filter — корректный вызов."""
        obj = FilterObject(callback=AsyncCallableFilter())
        result = await obj.call("event")
        assert result == {"from_async_callable_filter": True}

    def test_sync_callable_no_filter_not_awaitable(self) -> None:
        """FilterObject с sync callable БЕЗ наследования от Filter — awaitable=False."""
        obj = FilterObject(callback=SyncCallableNoFilter())
        assert obj.awaitable is False

    @pytest.mark.asyncio
    async def test_sync_callable_no_filter_call(self) -> None:
        """FilterObject с sync callable БЕЗ наследования от Filter — вызов через to_thread."""
        obj = FilterObject(callback=SyncCallableNoFilter())
        result = await obj.call("event")
        assert result is True

    def test_async_function_filter_awaitable(self) -> None:
        """FilterObject с обычной async функцией — awaitable=True (регрессия)."""

        async def my_filter(event: object) -> bool:
            return True

        obj = FilterObject(callback=my_filter)
        assert obj.awaitable is True

    def test_sync_function_filter_not_awaitable(self) -> None:
        """FilterObject с обычной sync функцией — awaitable=False (регрессия)."""

        def my_filter(event: object) -> bool:
            return True

        obj = FilterObject(callback=my_filter)
        assert obj.awaitable is False


# -- Тесты HandlerObject --


class TestHandlerObject:
    """Тесты для HandlerObject."""

    @pytest.mark.asyncio
    async def test_check_no_filters(self) -> None:
        obj = HandlerObject(callback=async_func)
        result, kwargs = await obj.check(a=1, b="x")
        assert result is True
        assert kwargs == {"a": 1, "b": "x"}

    @pytest.mark.asyncio
    async def test_check_all_filters_true(self) -> None:
        async def filter_true(event: object) -> bool:
            return True

        obj = HandlerObject(
            callback=async_func,
            filters=[FilterObject(callback=filter_true), FilterObject(callback=filter_true)],
        )
        result, kwargs = await obj.check("event")
        assert result is True

    @pytest.mark.asyncio
    async def test_check_one_filter_false(self) -> None:
        async def filter_true(event: object) -> bool:
            return True

        async def filter_false(event: object) -> bool:
            return False

        obj = HandlerObject(
            callback=async_func,
            filters=[FilterObject(callback=filter_true), FilterObject(callback=filter_false)],
        )
        result, kwargs = await obj.check("event")
        assert result is False

    @pytest.mark.asyncio
    async def test_check_dict_enrichment(self) -> None:
        async def enriching_filter(event: object) -> dict[str, Any]:
            return {"extra_key": "extra_value"}

        obj = HandlerObject(
            callback=async_func,
            filters=[FilterObject(callback=enriching_filter)],
        )
        result, kwargs = await obj.check("event", existing="yes")
        assert result is True
        assert kwargs["extra_key"] == "extra_value"
        assert kwargs["existing"] == "yes"

    @pytest.mark.asyncio
    async def test_check_dict_enrichment_chained(self) -> None:
        async def filter_a(event: object) -> dict[str, str]:
            return {"from_a": "value_a"}

        async def filter_b(event: object, from_a: str = "") -> dict[str, str]:
            return {"from_b": f"got_{from_a}"}

        obj = HandlerObject(
            callback=async_func,
            filters=[FilterObject(callback=filter_a), FilterObject(callback=filter_b)],
        )
        result, kwargs = await obj.check("event")
        assert result is True
        assert kwargs["from_a"] == "value_a"
        assert kwargs["from_b"] == "got_value_a"

    def test_flags_default_empty(self) -> None:
        obj = HandlerObject(callback=async_func)
        assert obj.flags == {}

    def test_flags_set(self) -> None:
        obj = HandlerObject(callback=async_func, flags={"rate_limit": "default"})
        assert obj.flags["rate_limit"] == "default"
