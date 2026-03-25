"""Тесты ExceptionTypeFilter."""

from __future__ import annotations

import pytest

from maxogram.filters.base import Filter
from maxogram.filters.exception import ExceptionTypeFilter


class TestExceptionTypeFilterInit:
    """Тесты инициализации ExceptionTypeFilter."""

    def test_single_type(self) -> None:
        f = ExceptionTypeFilter(ValueError)
        assert ValueError in f.exception_types

    def test_multiple_types(self) -> None:
        f = ExceptionTypeFilter(ValueError, TypeError)
        assert ValueError in f.exception_types
        assert TypeError in f.exception_types

    def test_is_filter_subclass(self) -> None:
        assert issubclass(ExceptionTypeFilter, Filter)

    def test_empty_raises(self) -> None:
        with pytest.raises(TypeError):
            ExceptionTypeFilter()  # type: ignore[call-arg]

    def test_base_exception(self) -> None:
        """Принимает BaseException подклассы."""
        f = ExceptionTypeFilter(KeyboardInterrupt)
        assert KeyboardInterrupt in f.exception_types


class TestExceptionTypeFilterCall:
    """Тесты вызова ExceptionTypeFilter."""

    @pytest.mark.asyncio
    async def test_exact_match(self) -> None:
        """ValueError — ExceptionTypeFilter(ValueError) -> True."""
        f = ExceptionTypeFilter(ValueError)
        result = await f(ValueError("test"))
        assert result is True

    @pytest.mark.asyncio
    async def test_subclass_match(self) -> None:
        """UnicodeError (подкласс ValueError) -> True."""
        f = ExceptionTypeFilter(ValueError)
        result = await f(UnicodeError("test"))
        assert result is True

    @pytest.mark.asyncio
    async def test_no_match(self) -> None:
        """TypeError — ExceptionTypeFilter(ValueError) -> False."""
        f = ExceptionTypeFilter(ValueError)
        result = await f(TypeError("test"))
        assert result is False

    @pytest.mark.asyncio
    async def test_multiple_types_match(self) -> None:
        """ValueError — ExceptionTypeFilter(ValueError, TypeError) -> True."""
        f = ExceptionTypeFilter(ValueError, TypeError)
        result = await f(ValueError("test"))
        assert result is True

    @pytest.mark.asyncio
    async def test_multiple_types_second_match(self) -> None:
        """TypeError — ExceptionTypeFilter(ValueError, TypeError) -> True."""
        f = ExceptionTypeFilter(ValueError, TypeError)
        result = await f(TypeError("test"))
        assert result is True

    @pytest.mark.asyncio
    async def test_multiple_types_no_match(self) -> None:
        """KeyError — ExceptionTypeFilter(ValueError, TypeError) -> False."""
        f = ExceptionTypeFilter(ValueError, TypeError)
        result = await f(KeyError("test"))
        assert result is False

    @pytest.mark.asyncio
    async def test_no_args(self) -> None:
        """Без аргументов -> False."""
        f = ExceptionTypeFilter(ValueError)
        result = await f()
        assert result is False

    @pytest.mark.asyncio
    async def test_non_exception_arg(self) -> None:
        """Не-исключение -> False."""
        f = ExceptionTypeFilter(ValueError)
        result = await f("not an exception")
        assert result is False

    @pytest.mark.asyncio
    async def test_invert(self) -> None:
        """~ExceptionTypeFilter инвертирует результат."""
        f = ~ExceptionTypeFilter(ValueError)
        result = await f(ValueError("test"))
        assert result is False

    @pytest.mark.asyncio
    async def test_invert_no_match(self) -> None:
        """~ExceptionTypeFilter на другой тип -> True."""
        f = ~ExceptionTypeFilter(ValueError)
        result = await f(TypeError("test"))
        assert result is True

    @pytest.mark.asyncio
    async def test_exception_via_kwarg(self) -> None:
        """Исключение через kwarg 'exception'."""
        f = ExceptionTypeFilter(ValueError)
        result = await f(exception=ValueError("test"))
        assert result is True

    @pytest.mark.asyncio
    async def test_custom_exception(self) -> None:
        """Пользовательское исключение."""

        class MyError(Exception):
            pass

        f = ExceptionTypeFilter(MyError)
        result = await f(MyError("custom"))
        assert result is True

    @pytest.mark.asyncio
    async def test_custom_exception_subclass(self) -> None:
        """Подкласс пользовательского исключения."""

        class MyError(Exception):
            pass

        class MySubError(MyError):
            pass

        f = ExceptionTypeFilter(MyError)
        result = await f(MySubError("sub"))
        assert result is True
