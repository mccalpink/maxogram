"""EventObserver — простой observer для lifecycle-событий (startup/shutdown)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from maxogram.dispatcher.event.handler import CallbackType, HandlerObject

__all__ = [
    "EventObserver",
]


class EventObserver:
    """Observer для lifecycle-событий (startup/shutdown).

    Все зарегистрированные callbacks вызываются последовательно.
    В отличие от MaxEventObserver — нет фильтров и middleware.
    """

    def __init__(self) -> None:
        self.handlers: list[HandlerObject] = []

    def register(self, callback: CallbackType) -> CallbackType:
        """Зарегистрировать callback."""
        self.handlers.append(HandlerObject(callback=callback))
        return callback

    def __call__(
        self,
        callback: CallbackType | None = None,
    ) -> CallbackType | Callable[[CallbackType], CallbackType]:
        """Декоратор для регистрации callback.

        Поддерживает оба варианта:
        - @dp.startup        (без скобок — callback передаётся напрямую)
        - @dp.startup()      (со скобками — возвращает декоратор)
        """
        if callback is not None:
            return self.register(callback)

        def wrapper(cb: CallbackType) -> CallbackType:
            return self.register(cb)

        return wrapper

    async def trigger(self, *args: Any, **kwargs: Any) -> None:
        """Вызвать все handlers последовательно."""
        for handler in self.handlers:
            await handler.call(*args, **kwargs)
