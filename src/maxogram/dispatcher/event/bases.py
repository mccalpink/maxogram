"""Sentinel-объекты и исключения для обработки событий."""

from __future__ import annotations

__all__ = [
    "REJECTED",
    "UNHANDLED",
    "CancelHandler",
    "SkipHandler",
]


class _Sentinel:
    """Sentinel-объект с именованным repr и falsy-семантикой."""

    def __init__(self, name: str) -> None:
        self._name = name

    def __repr__(self) -> str:
        return self._name

    def __bool__(self) -> bool:
        return False


UNHANDLED = _Sentinel("UNHANDLED")
"""Ни один хендлер не подошёл для обработки события."""

REJECTED = _Sentinel("REJECTED")
"""Хендлер явно отклонил событие."""


class SkipHandler(Exception):  # noqa: N818
    """Пропустить текущий хендлер, перейти к следующему."""


class CancelHandler(Exception):  # noqa: N818
    """Полностью отменить обработку события."""
