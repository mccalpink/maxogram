"""Фильтр по данным контекста через MagicFilter."""

from __future__ import annotations

from typing import Any

from magic_filter import MagicFilter

from maxogram.filters.base import Filter

__all__ = [
    "MagicData",
]


class _MagicDataContext:
    """Обёртка dict для атрибутного доступа (MagicFilter resolve)."""

    __slots__ = ("_data",)

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __getattr__(self, name: str) -> Any:
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(name) from None


class MagicData(Filter):
    """Фильтр по произвольным данным из middleware/workflow_data.

    Позволяет фильтровать по контексту, используя DSL MagicFilter.

    Пример::

        MagicData(F.event_chat.chat_type == "dialog")
    """

    __slots__ = ("magic",)

    def __init__(self, magic: MagicFilter) -> None:
        self.magic = magic

    async def __call__(self, *args: Any, **kwargs: Any) -> bool:
        """Применить magic filter к данным контекста."""
        context = _MagicDataContext(kwargs)
        try:
            result = self.magic.resolve(context)
        except (AttributeError, TypeError, LookupError):
            return False
        return bool(result)
