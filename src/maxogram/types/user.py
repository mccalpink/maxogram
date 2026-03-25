"""Типы пользователей и ботов Max API."""

from __future__ import annotations

from maxogram.types.base import MaxObject
from maxogram.types.misc import PhotoAttachmentRequestPayload


class User(MaxObject):
    """Пользователь Max."""

    user_id: int
    name: str
    username: str | None = None
    is_bot: bool
    last_activity_time: int


class UserWithPhoto(User):
    """Пользователь с фото и описанием."""

    description: str | None = None
    avatar_url: str | None = None
    full_avatar_url: str | None = None


class BotCommand(MaxObject):
    """Команда бота."""

    name: str
    description: str | None = None


class BotInfo(UserWithPhoto):
    """Информация о боте (ответ GET /me)."""

    commands: list[BotCommand] | None = None


class BotPatch(MaxObject):
    """Данные для редактирования бота (PATCH /me)."""

    name: str | None = None
    description: str | None = None
    commands: list[BotCommand] | None = None
    photo: PhotoAttachmentRequestPayload | None = None
