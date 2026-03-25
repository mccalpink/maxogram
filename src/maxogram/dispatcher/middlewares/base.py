"""BaseMiddleware — абстрактный базовый класс для middleware (onion pattern)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

__all__ = ["BaseMiddleware"]


class BaseMiddleware(ABC):
    """Базовый класс middleware (onion pattern).

    Контракт:
    - handler — следующий в цепочке (middleware или хендлер)
    - event — событие Max API
    - data — мутабельный словарь контекста

    Для продолжения цепочки: ``await handler(event, data)``
    Для прерывания: ``return`` без вызова handler.
    """

    @abstractmethod
    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any: ...
