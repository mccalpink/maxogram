"""MaxEventObserver — observer для событий Max API с фильтрами и middleware."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

from maxogram.dispatcher.event.bases import UNHANDLED, SkipHandler
from maxogram.dispatcher.event.handler import (
    CallbackType,
    FilterObject,
    HandlerObject,
)
from maxogram.dispatcher.middlewares.manager import MiddlewareManager

__all__ = [
    "MaxEventObserver",
]


class MaxEventObserver:
    """Observer для событий Max API.

    Поддерживает:
    - Регистрацию хендлеров с фильтрами и флагами
    - Root filters (применяются ко всем хендлерам)
    - Middleware pipeline (inner + outer)
    - Trigger — поиск подходящего хендлера и вызов через middleware
    """

    def __init__(
        self,
        router: Any = None,
        event_name: str = "",
    ) -> None:
        self.router = router
        self.event_name = event_name
        self.handlers: list[HandlerObject] = []

        # Root filter — контейнер для фильтров, общих для всех хендлеров
        self._handler = HandlerObject(callback=_noop)

        # Middleware (inner + outer)
        self.middleware = MiddlewareManager()
        self.outer_middleware = MiddlewareManager()

    def register(
        self,
        callback: CallbackType,
        *filters: CallbackType,
        flags: dict[str, Any] | None = None,
    ) -> CallbackType:
        """Зарегистрировать хендлер с фильтрами.

        Флаги извлекаются из ``maxogram_flags`` атрибута callback
        (установленного FlagGenerator) и мержатся с explicit flags.
        Explicit flags имеют приоритет.
        """
        # Извлечь флаги из декоратора FlagGenerator
        resolved_flags: dict[str, Any] = {}
        decorator_flags = getattr(callback, "maxogram_flags", None)
        if decorator_flags:
            resolved_flags.update(decorator_flags)
        # Explicit flags перезаписывают decorator flags
        if flags:
            resolved_flags.update(flags)

        filter_objects = [FilterObject(callback=f) for f in filters]
        handler = HandlerObject(
            callback=callback,
            filters=filter_objects if filter_objects else None,
            flags=resolved_flags,
        )
        self.handlers.append(handler)
        return callback

    def __call__(
        self,
        *filters: CallbackType,
        flags: dict[str, Any] | None = None,
    ) -> Callable[[CallbackType], CallbackType]:
        """Декоратор для регистрации хендлера."""

        def wrapper(callback: CallbackType) -> CallbackType:
            self.register(callback, *filters, flags=flags)
            return callback

        return wrapper

    def filter(self, *filters: CallbackType) -> None:
        """Добавить root filters — применяются ко всем хендлерам."""
        new_filters = [FilterObject(callback=f) for f in filters]
        if self._handler.filters is None:
            self._handler.filters = new_filters
        else:
            self._handler.filters.extend(new_filters)

    async def trigger(self, event: Any, **kwargs: Any) -> Any:
        """Найти подходящий хендлер и вызвать через middleware.

        1. Проверить root filters
        2. Итерация по handlers (в порядке регистрации)
        3. handler.check() — проверка фильтров
        4. Первый прошедший → вызов через inner middleware chain
        5. SkipHandler → следующий хендлер
        6. Ни один → UNHANDLED
        """
        # Проверяем root filters
        root_check, kwargs = await self._handler.check(event, **kwargs)
        if not root_check:
            return UNHANDLED

        for handler in self.handlers:
            handler_kwargs = {**kwargs, "handler": handler}
            check, data = await handler.check(event, **handler_kwargs)
            if check:
                handler_kwargs.update(data)
                try:
                    # Inner middleware wrapping
                    wrapped = MiddlewareManager.wrap_middlewares(
                        self.middleware,
                        handler.call,
                    )
                    return await wrapped(event, handler_kwargs)
                except SkipHandler:
                    continue

        return UNHANDLED

    def wrap_outer_middleware(
        self,
        callback: Callable[..., Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Awaitable[Any]:
        """Обернуть callback в outer middleware chain."""
        wrapped = MiddlewareManager.wrap_middlewares(
            self.outer_middleware,
            callback,
        )
        return wrapped(event, data)


async def _noop() -> None:
    """Заглушка для root filter контейнера."""
