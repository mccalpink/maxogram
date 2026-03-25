"""Система флагов — метаданные для хендлеров.

FlagGenerator позволяет декорировать хендлеры флагами,
а get_flag/check_flag — читать их в middleware.

Пример::

    flags = FlagGenerator()

    @flags.rate_limit("strict")
    @router.message_created()
    async def handler(message: Message): ...

    # В middleware:
    class ThrottleMiddleware(BaseMiddleware):
        async def __call__(self, handler, event, data):
            limit = get_flag(data, "rate_limit")
            if limit:
                ...
"""

from __future__ import annotations

from typing import Any

from maxogram.dispatcher.event.handler import HandlerObject

__all__ = [
    "FlagGenerator",
    "check_flag",
    "get_flag",
]

#: Атрибут на callback для хранения флагов
FLAGS_ATTR = "maxogram_flags"


class _FlagDecorator:
    """Декоратор для установки одного флага на callback."""

    __slots__ = ("_name", "_value")

    def __init__(self, name: str, value: Any) -> None:
        self._name = name
        self._value = value

    def __call__(self, callback: Any) -> Any:
        """Установить флаг на callback и вернуть его."""
        if not hasattr(callback, FLAGS_ATTR):
            callback.maxogram_flags = {}
        callback.maxogram_flags[self._name] = self._value
        return callback


class _FlagProxy:
    """Прокси для динамического создания флагов через атрибут-вызов.

    ``flags.rate_limit("strict")`` → ``_FlagDecorator("rate_limit", "strict")``
    """

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        self._name = name

    def __call__(self, value: Any = True) -> _FlagDecorator:
        """Создать декоратор с заданным значением флага."""
        return _FlagDecorator(self._name, value)


class FlagGenerator:
    """Генератор флагов для хендлеров.

    Использование::

        flags = FlagGenerator()

        @flags.rate_limit("strict")
        @flags.priority(10)
        @router.message_created()
        async def handler(message): ...

    Флаги сохраняются в атрибуте ``maxogram_flags`` на callback.
    При регистрации в observer они автоматически извлекаются
    и помещаются в ``HandlerObject.flags``.
    """

    def __getattr__(self, name: str) -> _FlagProxy:
        """Динамическое создание proxy для любого имени флага."""
        if name.startswith("_"):
            raise AttributeError(name)
        return _FlagProxy(name)


def get_flag(
    data: dict[str, Any],
    name: str,
    *,
    default: Any = None,
) -> Any:
    """Получить значение флага из data middleware.

    Args:
        data: dict контекста (из middleware ``__call__``)
        name: имя флага
        default: значение по умолчанию, если флаг не найден

    Returns:
        Значение флага или default.
    """
    handler: HandlerObject | None = data.get("handler")
    if handler is None:
        return default
    return handler.flags.get(name, default)


def check_flag(data: dict[str, Any], name: str) -> bool:
    """Проверить наличие флага в текущем хендлере.

    Args:
        data: dict контекста (из middleware ``__call__``)
        name: имя флага

    Returns:
        True если флаг установлен (даже если значение False/None).
    """
    handler: HandlerObject | None = data.get("handler")
    if handler is None:
        return False
    return name in handler.flags
