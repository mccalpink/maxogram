"""Фильтр по типу исключения для error handlers."""

from __future__ import annotations

from typing import Any

from maxogram.filters.base import Filter

__all__ = [
    "ExceptionTypeFilter",
]


class ExceptionTypeFilter(Filter):
    """Фильтр по типу исключения.

    Проверяет isinstance исключения к заданным типам.

    Пример::

        ExceptionTypeFilter(ValueError)              # только ValueError
        ExceptionTypeFilter(ValueError, TypeError)    # ValueError или TypeError
    """

    __slots__ = ("exception_types",)

    def __init__(self, *exception_types: type[BaseException]) -> None:
        if not exception_types:
            msg = "ExceptionTypeFilter requires at least one exception type"
            raise TypeError(msg)
        self.exception_types: tuple[type[BaseException], ...] = exception_types

    async def __call__(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:
        """Проверить тип исключения.

        Исключение может быть первым позиционным аргументом
        или kwargs['exception'].
        """
        exception = args[0] if args else kwargs.get("exception")
        if exception is None:
            return False

        if not isinstance(exception, BaseException):
            return False

        return isinstance(exception, self.exception_types)
