"""Методы Bot API — /me."""

from __future__ import annotations

from typing import ClassVar

from maxogram.methods.base import MaxMethod
from maxogram.types.misc import PhotoAttachmentRequestPayload
from maxogram.types.user import BotCommand, BotInfo


class GetMyInfo(MaxMethod["BotInfo"]):
    """GET /me — Получение информации о боте."""

    __api_path__: ClassVar[str] = "/me"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = BotInfo


class EditMyInfo(MaxMethod["BotInfo"]):
    """PATCH /me — Редактирование информации о боте."""

    __api_path__: ClassVar[str] = "/me"
    __http_method__: ClassVar[str] = "PATCH"
    __returning__: ClassVar[type] = BotInfo

    name: str | None = None
    description: str | None = None
    commands: list[BotCommand] | None = None
    photo: PhotoAttachmentRequestPayload | None = None
