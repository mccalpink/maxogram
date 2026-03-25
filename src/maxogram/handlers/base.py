"""BaseHandler и типизированные class-based handlers.

Позволяют организовывать логику обработки событий в классах
с типизированным доступом к event и data.

Пример::

    class MyHandler(MessageHandler):
        async def handle(self) -> Any:
            await self.event.answer("Привет!")
            state = self.data.get("state")
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from maxogram.types.callback import Callback
from maxogram.types.message import Message

__all__ = [
    "BaseHandler",
    "CallbackHandler",
    "MessageHandler",
]

T = TypeVar("T")


class BaseHandler(Generic[T], ABC):
    """Базовый class-based handler.

    Generic[T] — тип события (Message, Callback и т.д.).
    Подкласс обязан реализовать ``handle()``.

    При использовании с CallableObject:
    - Класс передаётся как callback
    - ``__init__`` принимает event (позиционный) + **kwargs (data)
    - ``__await__`` делегирует в ``handle()``
    """

    def __init__(self, event: T, **kwargs: Any) -> None:
        self.event: T = event
        self.data: dict[str, Any] = kwargs

    @property
    def bot(self) -> Any:
        """Shortcut для ``self.data['bot']``."""
        return self.data["bot"]

    @abstractmethod
    async def handle(self) -> Any:
        """Основной метод обработки события. Обязателен для реализации."""
        ...

    def __await__(self) -> Any:
        """Поддержка ``await MyHandler(event, **kwargs)``."""
        return self.handle().__await__()


class MessageHandler(BaseHandler[Message]):
    """Handler для message_created событий.

    Пример::

        class MyHandler(MessageHandler):
            async def handle(self) -> Any:
                # self.event — Message
                await self.event.answer("Привет!")
    """


class CallbackHandler(BaseHandler[Callback]):
    """Handler для message_callback событий.

    Пример::

        class MyHandler(CallbackHandler):
            async def handle(self) -> Any:
                # self.event — Callback
                callback_id = self.event.callback_id
    """
