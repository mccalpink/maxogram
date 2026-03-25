"""MiddlewareManager — управление middleware и построение onion chain."""

from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, overload

__all__ = ["MiddlewareManager", "MiddlewareType"]

MiddlewareType = Callable[
    [Callable[[Any, dict[str, Any]], Awaitable[Any]], Any, dict[str, Any]],
    Awaitable[Any],
]
"""Тип middleware: принимает (handler, event, data) → result."""


class MiddlewareManager(Sequence[MiddlewareType]):
    """Менеджер middleware с поддержкой onion-style wrapping.

    Поддерживает:
    - Регистрацию middleware (class-based и функциональных)
    - Удаление middleware
    - Построение onion-chain через ``wrap_middlewares``
    - Протокол ``Sequence`` (len, [], итерация)
    """

    def __init__(self) -> None:
        self._middlewares: list[MiddlewareType] = []

    def register(self, middleware: MiddlewareType) -> MiddlewareType:
        """Зарегистрировать middleware."""
        self._middlewares.append(middleware)
        return middleware

    def unregister(self, middleware: MiddlewareType) -> None:
        """Удалить middleware. Поднимает ValueError если не найден."""
        self._middlewares.remove(middleware)

    @overload
    def __call__(self, middleware: MiddlewareType) -> MiddlewareType: ...

    @overload
    def __call__(self, middleware: None = None) -> Callable[[MiddlewareType], MiddlewareType]: ...

    def __call__(
        self, middleware: MiddlewareType | None = None
    ) -> MiddlewareType | Callable[[MiddlewareType], MiddlewareType]:
        """Вызов как декоратор или прямая регистрация.

        Использование::

            # Прямая регистрация
            observer.middleware(my_mw)

            # Декоратор с аргументом
            @observer.middleware
            async def my_mw(handler, event, data): ...

            # Декоратор-фабрика (без аргументов)
            @observer.middleware()
            async def my_mw(handler, event, data): ...
        """
        if middleware is not None:
            return self.register(middleware)

        def wrapper(m: MiddlewareType) -> MiddlewareType:
            return self.register(m)

        return wrapper

    def __len__(self) -> int:
        return len(self._middlewares)

    @overload
    def __getitem__(self, index: int) -> MiddlewareType: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[MiddlewareType]: ...

    def __getitem__(self, index: int | slice) -> MiddlewareType | Sequence[MiddlewareType]:
        return self._middlewares[index]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MiddlewareManager):
            return self._middlewares == other._middlewares
        if isinstance(other, list):
            return self._middlewares == other
        return NotImplemented

    @staticmethod
    def wrap_middlewares(
        middlewares: Sequence[MiddlewareType],
        handler: Callable[..., Awaitable[Any]],
    ) -> Callable[[Any, dict[str, Any]], Awaitable[Any]]:
        """Построить onion-style цепочку.

        Каждый middleware оборачивает предыдущий::

            mw1(mw2(mw3(handler)))

        Внутренний handler получает ``(event, **kwargs)``,
        а middleware получает ``(handler, event, data)`` где data — dict.
        """

        async def handler_wrapper(event: Any, data: dict[str, Any]) -> Any:
            return await handler(event, **data)

        middleware: Callable[[Any, dict[str, Any]], Awaitable[Any]] = handler_wrapper
        for m in reversed(middlewares):
            middleware = functools.partial(m, middleware)
        return middleware
