"""Тесты FSMContext."""

from __future__ import annotations

import pytest

from maxogram.fsm.context import FSMContext
from maxogram.fsm.state import State, StatesGroup
from maxogram.fsm.storage.base import StorageKey
from maxogram.fsm.storage.memory import MemoryStorage


def _make_context() -> FSMContext:
    """Создать FSMContext с MemoryStorage."""
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=100, user_id=42)
    return FSMContext(storage=storage, key=key)


class OrderForm(StatesGroup):
    """Тестовая группа состояний."""

    product = State()
    quantity = State()


class TestFSMContextState:
    """FSMContext — управление состоянием."""

    @pytest.mark.asyncio
    async def test_get_state_default_none(self) -> None:
        """По умолчанию состояние — None."""
        ctx = _make_context()
        assert await ctx.get_state() is None

    @pytest.mark.asyncio
    async def test_set_state_string(self) -> None:
        """Установка состояния строкой."""
        ctx = _make_context()
        await ctx.set_state("Form:name")
        assert await ctx.get_state() == "Form:name"

    @pytest.mark.asyncio
    async def test_set_state_object(self) -> None:
        """Установка состояния State-объектом."""
        ctx = _make_context()
        await ctx.set_state(OrderForm.product)
        assert await ctx.get_state() == "OrderForm:product"

    @pytest.mark.asyncio
    async def test_set_state_none(self) -> None:
        """Сброс состояния в None."""
        ctx = _make_context()
        await ctx.set_state(OrderForm.product)
        await ctx.set_state(None)
        assert await ctx.get_state() is None


class TestFSMContextData:
    """FSMContext — управление данными."""

    @pytest.mark.asyncio
    async def test_get_data_default_empty(self) -> None:
        """По умолчанию данные — пустой dict."""
        ctx = _make_context()
        assert await ctx.get_data() == {}

    @pytest.mark.asyncio
    async def test_set_get_data(self) -> None:
        """Установка и получение данных."""
        ctx = _make_context()
        await ctx.set_data({"name": "Alice"})
        assert await ctx.get_data() == {"name": "Alice"}

    @pytest.mark.asyncio
    async def test_update_data(self) -> None:
        """update_data мержит данные."""
        ctx = _make_context()
        await ctx.set_data({"a": 1})
        result = await ctx.update_data({"b": 2})
        assert result == {"a": 1, "b": 2}

    @pytest.mark.asyncio
    async def test_update_data_kwargs(self) -> None:
        """update_data принимает kwargs."""
        ctx = _make_context()
        result = await ctx.update_data(name="Alice", age=30)
        assert result == {"name": "Alice", "age": 30}

    @pytest.mark.asyncio
    async def test_get_value(self) -> None:
        """get_value возвращает одно значение."""
        ctx = _make_context()
        await ctx.set_data({"name": "Alice"})
        assert await ctx.get_value("name") == "Alice"

    @pytest.mark.asyncio
    async def test_get_value_default(self) -> None:
        """get_value с default."""
        ctx = _make_context()
        assert await ctx.get_value("missing", "fallback") == "fallback"


class TestFSMContextClear:
    """FSMContext — clear сбрасывает всё."""

    @pytest.mark.asyncio
    async def test_clear(self) -> None:
        """clear() сбрасывает состояние и данные."""
        ctx = _make_context()
        await ctx.set_state(OrderForm.product)
        await ctx.set_data({"name": "Alice"})

        await ctx.clear()

        assert await ctx.get_state() is None
        assert await ctx.get_data() == {}
