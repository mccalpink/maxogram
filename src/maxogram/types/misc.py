"""Общие вспомогательные типы Max API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from maxogram.enums import SenderAction
from maxogram.types.base import MaxObject

if TYPE_CHECKING:
    from maxogram.types.message import Message
    from maxogram.types.subscription import Subscription


class Image(MaxObject):
    """Изображение (иконка чата, аватар и т.д.)."""

    url: str


class Error(MaxObject):
    """Ошибка от Max API."""

    error: str | None = None
    code: str
    message: str


class SimpleQueryResult(MaxObject):
    """Простой результат операции."""

    success: bool
    message: str | None = None


class ActionRequestBody(MaxObject):
    """Тело запроса отправки действия (typing и т.п.)."""

    action: SenderAction


class PhotoAttachmentRequestPayload(MaxObject):
    """Payload для фото при запросе (аватар бота, иконка чата)."""

    url: str | None = None
    token: str | None = None
    photos: dict[str, PhotoToken] | None = None


class PhotoToken(MaxObject):
    """Токен фото определённого размера."""

    token: str


class UserIdsList(MaxObject):
    """Список ID пользователей."""

    user_ids: list[int]


class PinMessageBody(MaxObject):
    """Тело запроса закрепления сообщения."""

    message_id: str
    notify: bool = True


class GetPinnedMessageResult(MaxObject):
    """Результат GET /chats/{chatId}/pin."""

    message: Message | None = None


class GetSubscriptionsResult(MaxObject):
    """Результат GET /subscriptions."""

    subscriptions: list[Subscription]
