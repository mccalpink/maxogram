"""Фильтр по типу контента сообщения."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from maxogram.filters.base import Filter

__all__ = [
    "ContentType",
    "ContentTypeFilter",
]


class ContentType(StrEnum):
    """Тип контента сообщения в Max.

    Значения соответствуют ``Attachment.type`` из Max Bot API.
    ``TEXT`` — текстовое сообщение без вложений.
    ``ANY`` — любой контент (текст или вложения).
    """

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    STICKER = "sticker"
    CONTACT = "contact"
    SHARE = "share"
    LOCATION = "location"
    INLINE_KEYBOARD = "inline_keyboard"
    ANY = "any"


class ContentTypeFilter(Filter):
    """Фильтр по типу контента (определяется через attachments[].type).

    Примеры::

        ContentTypeFilter(ContentType.IMAGE)                    # только фото
        ContentTypeFilter(ContentType.IMAGE, ContentType.VIDEO) # фото или видео
        ContentTypeFilter(ContentType.TEXT)                     # только текст (без вложений)
        ContentTypeFilter(ContentType.ANY)                      # любой контент
    """

    __slots__ = ("content_types",)

    def __init__(self, *content_types: ContentType | str) -> None:
        if not content_types:
            msg = "ContentTypeFilter requires at least one content type"
            raise TypeError(msg)
        self.content_types: frozenset[str] = frozenset(str(ct) for ct in content_types)

    async def __call__(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:
        """Проверить тип контента сообщения.

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

        body = getattr(message, "body", None)
        if body is None:
            return False

        attachments = getattr(body, "attachments", None)
        text = getattr(body, "text", None)

        # Собрать типы контента текущего сообщения
        has_attachments = bool(attachments)

        # ANY — любой контент
        if ContentType.ANY in self.content_types:
            return bool(text) or has_attachments

        # TEXT — текст без вложений
        if ContentType.TEXT in self.content_types and not has_attachments and text:
            return True

        # Проверить типы вложений
        if has_attachments and attachments is not None:
            attachment_types = {getattr(a, "type", None) for a in attachments}
            if attachment_types & self.content_types:
                return True

        return False
