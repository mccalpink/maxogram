"""CallableObject, FilterObject, HandlerObject — ядро DI и хендлер-системы."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import partial
from typing import Any

from magic_filter import MagicFilter

__all__ = [
    "CallableObject",
    "CallbackType",
    "FilterObject",
    "HandlerObject",
]

CallbackType = Callable[..., Any] | Callable[..., Awaitable[Any]]
"""Тип callback — синхронная или асинхронная функция."""

_ACCEPTED_KINDS = frozenset(
    {
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    }
)


@dataclass
class CallableObject:
    """Обёртка callable с интроспекцией параметров (DI).

    Анализирует сигнатуру callback при создании.
    При вызове фильтрует kwargs — передаёт только те, которые callback объявил.
    Синхронные callback автоматически вызываются через ``asyncio.to_thread``.
    """

    callback: CallbackType
    awaitable: bool = field(init=False)
    params: frozenset[str] = field(init=False)
    varkw: bool = field(init=False)

    def __post_init__(self) -> None:
        self.awaitable = inspect.iscoroutinefunction(self.callback)
        # Class-based handlers: класс с __await__ (BaseHandler и подклассы)
        if (
            not self.awaitable
            and inspect.isclass(self.callback)
            and hasattr(self.callback, "__await__")
        ):
            self.awaitable = True
        sig = inspect.signature(self.callback)
        self.params = frozenset(
            p.name for p in sig.parameters.values() if p.kind in _ACCEPTED_KINDS
        )
        self.varkw = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )

    def _prepare_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Отфильтровать kwargs — оставить только объявленные параметры."""
        if self.varkw:
            return kwargs
        return {k: kwargs[k] for k in self.params if k in kwargs}

    async def call(self, *args: Any, **kwargs: Any) -> Any:
        """Вызвать callback с подготовленными аргументами."""
        wrapped = partial(self.callback, *args, **self._prepare_kwargs(kwargs))
        if self.awaitable:
            return await wrapped()
        return await asyncio.to_thread(wrapped)


@dataclass
class FilterObject(CallableObject):
    """Обёртка фильтра с поддержкой MagicFilter.

    Если callback — экземпляр MagicFilter, сохраняет его в ``magic``
    и заменяет callback на ``magic.resolve``.
    """

    magic: MagicFilter | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if isinstance(self.callback, MagicFilter):
            self.magic = self.callback
            self.callback = self.magic.resolve
        super().__post_init__()
        # Filter.__call__ всегда async, но inspect не определяет это через экземпляр
        from maxogram.filters.base import Filter

        if isinstance(self.callback, Filter):
            self.awaitable = True


@dataclass
class HandlerObject(CallableObject):
    """Хендлер с фильтрами и флагами.

    Метод ``check`` последовательно проверяет фильтры (AND-логика).
    Каждый фильтр может обогатить kwargs (вернув dict).
    """

    filters: list[FilterObject] | None = None
    flags: dict[str, Any] = field(default_factory=dict)

    async def check(self, *args: Any, **kwargs: Any) -> tuple[bool, dict[str, Any]]:
        """Проверить все фильтры последовательно.

        Возвращает ``(True, kwargs)`` если все фильтры прошли,
        ``(False, kwargs)`` если хотя бы один вернул False.
        Фильтр, вернувший dict, обогащает kwargs.
        """
        if not self.filters:
            return True, kwargs
        for event_filter in self.filters:
            check = await event_filter.call(*args, **kwargs)
            if not check:
                return False, kwargs
            if isinstance(check, dict):
                kwargs.update(check)
        return True, kwargs
