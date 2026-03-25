"""Расширение MagicFilter — метод .as_() для сохранения результата в kwargs."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from magic_filter import MagicFilter as _MagicFilter
from magic_filter import MagicT as _MagicT
from magic_filter.operations import BaseOperation

__all__ = [
    "MagicFilter",
]


class AsFilterResultOperation(BaseOperation):
    """Операция .as_() — оборачивает результат в dict для обогащения kwargs хендлера.

    Если значение ``None`` или пустая коллекция — возвращает ``None`` (фильтр не прошёл).
    Иначе — ``{name: value}`` (фильтр прошёл + обогащение).
    """

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def resolve(self, value: Any, initial_value: Any) -> Any:
        """Обернуть значение в dict или вернуть None."""
        if value is None or (isinstance(value, Iterable) and not value):
            return None
        return {self.name: value}


class MagicFilter(_MagicFilter):
    """Расширенный MagicFilter с поддержкой .as_()."""

    def as_(self: _MagicT, name: str) -> _MagicT:
        """Сохранить результат фильтра в kwargs хендлера под именем ``name``.

        Пример::

            F.text.regexp(r"(\\d+)").as_("match")
            # handler получит match=<re.Match object>
        """
        return self._extend(AsFilterResultOperation(name=name))
