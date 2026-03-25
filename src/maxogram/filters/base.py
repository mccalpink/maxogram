"""Базовый класс фильтра и инверсия."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

__all__ = [
    "Filter",
    "_InvertFilter",
]


class Filter(ABC):
    """Базовый класс фильтра.

    Контракт возврата:
    - ``False`` — фильтр не прошёл
    - ``True`` — фильтр прошёл
    - ``dict`` — фильтр прошёл + обогащение kwargs хендлера
    """

    @abstractmethod
    async def __call__(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]: ...

    def __invert__(self) -> _InvertFilter:
        """``~Filter()`` — инвертированный фильтр."""
        return _InvertFilter(target=self)

    def update_handler_flags(self, flags: dict[str, Any]) -> None:  # noqa: B027
        """Хук для обновления флагов хендлера при регистрации.

        По умолчанию ничего не делает. Переопределяется в подклассах.
        """


class _InvertFilter:
    """Инвертированный фильтр: ``~Filter()``."""

    __slots__ = ("target",)

    def __init__(self, target: Filter) -> None:
        self.target = target

    async def __call__(self, *args: Any, **kwargs: Any) -> bool:
        """Инвертировать результат исходного фильтра."""
        result = await self.target(*args, **kwargs)
        return not result
