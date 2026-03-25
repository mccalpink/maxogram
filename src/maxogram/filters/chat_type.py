"""Фильтр по типу чата."""

from __future__ import annotations

from typing import Any

from maxogram.enums import ChatType
from maxogram.filters.base import Filter

__all__ = [
    "ChatTypeFilter",
]


class ChatTypeFilter(Filter):
    """Фильтр по типу чата (dialog/chat/channel).

    Проверяет ``recipient.chat_type`` у Message или Update.

    Примеры::

        ChatTypeFilter(ChatType.DIALOG)               # только личные
        ChatTypeFilter(ChatType.CHAT, ChatType.CHANNEL)  # группы и каналы
        ChatTypeFilter("dialog")                       # строковое значение
    """

    __slots__ = ("chat_types",)

    def __init__(self, *chat_types: ChatType | str) -> None:
        if not chat_types:
            msg = "ChatTypeFilter requires at least one chat type"
            raise TypeError(msg)
        self.chat_types: frozenset[str] = frozenset(str(ct) for ct in chat_types)

    async def __call__(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:
        """Проверить тип чата сообщения.

        Первый позиционный аргумент — Message или Update.
        """
        event = args[0] if args else None
        if event is None:
            return False

        # Извлечь message из Update
        message = event
        if hasattr(event, "update_type") and hasattr(event, "message"):
            message = event.message
            if message is None:
                return False

        # Получить chat_type из recipient
        recipient = getattr(message, "recipient", None)
        if recipient is None:
            return False

        chat_type = getattr(recipient, "chat_type", None)
        if chat_type is None:
            return False

        return str(chat_type) in self.chat_types
