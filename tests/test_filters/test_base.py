"""Тесты Filter ABC и _InvertFilter."""

from __future__ import annotations

from typing import Any

import pytest

from maxogram.filters.base import Filter, _InvertFilter

# -- Тестовые реализации --


class AlwaysTrueFilter(Filter):
    """Фильтр, всегда возвращающий True."""

    async def __call__(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:
        return True


class AlwaysFalseFilter(Filter):
    """Фильтр, всегда возвращающий False."""

    async def __call__(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:
        return False


class DictFilter(Filter):
    """Фильтр, возвращающий dict (обогащение контекста)."""

    async def __call__(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:
        return {"enriched": True}


# -- Тесты Filter ABC --


class TestFilterABC:
    """Тесты для абстрактного класса Filter."""

    def test_cannot_instantiate(self) -> None:
        """Filter — абстрактный, нельзя создать экземпляр."""
        with pytest.raises(TypeError):
            Filter()  # type: ignore[abstract]

    @pytest.mark.asyncio
    async def test_subclass_call_true(self) -> None:
        """Подкласс Filter с __call__ работает — True."""
        f = AlwaysTrueFilter()
        result = await f()
        assert result is True

    @pytest.mark.asyncio
    async def test_subclass_call_false(self) -> None:
        """Подкласс Filter с __call__ работает — False."""
        f = AlwaysFalseFilter()
        result = await f()
        assert result is False

    @pytest.mark.asyncio
    async def test_subclass_call_dict(self) -> None:
        """Подкласс Filter с __call__ возвращает dict."""
        f = DictFilter()
        result = await f()
        assert result == {"enriched": True}

    def test_invert_returns_invert_filter(self) -> None:
        """~Filter() возвращает _InvertFilter."""
        f = AlwaysTrueFilter()
        inverted = ~f
        assert isinstance(inverted, _InvertFilter)

    def test_update_handler_flags_default_noop(self) -> None:
        """update_handler_flags по умолчанию ничего не делает."""
        f = AlwaysTrueFilter()
        flags: dict[str, Any] = {"existing": "value"}
        f.update_handler_flags(flags)
        assert flags == {"existing": "value"}


# -- Тесты _InvertFilter --


class TestInvertFilter:
    """Тесты для _InvertFilter."""

    @pytest.mark.asyncio
    async def test_invert_true_to_false(self) -> None:
        """True → False."""
        f = _InvertFilter(target=AlwaysTrueFilter())
        result = await f()
        assert result is False

    @pytest.mark.asyncio
    async def test_invert_false_to_true(self) -> None:
        """False → True."""
        f = _InvertFilter(target=AlwaysFalseFilter())
        result = await f()
        assert result is True

    @pytest.mark.asyncio
    async def test_invert_dict_to_false(self) -> None:
        """dict (truthy) → False."""
        f = _InvertFilter(target=DictFilter())
        result = await f()
        assert result is False

    def test_target_attribute(self) -> None:
        """_InvertFilter хранит ссылку на исходный фильтр."""
        original = AlwaysTrueFilter()
        inverted = _InvertFilter(target=original)
        assert inverted.target is original

    @pytest.mark.asyncio
    async def test_invert_via_dunder(self) -> None:
        """~Filter() → _InvertFilter и корректно инвертирует."""
        f = AlwaysTrueFilter()
        inverted = ~f
        result = await inverted()
        assert result is False
