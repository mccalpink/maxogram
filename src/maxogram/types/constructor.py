"""Типы конструктора сообщений Max API."""

from __future__ import annotations

from maxogram.enums import TextFormat
from maxogram.types.attachment import AttachmentRequest
from maxogram.types.base import MaxObject
from maxogram.types.keyboard import Keyboard
from maxogram.types.markup import MarkupElement


class ConstructedMessageBody(MaxObject):
    """Тело сконструированного сообщения."""

    text: str | None = None
    attachments: list[AttachmentRequest] | None = None
    markup: list[MarkupElement] | None = None
    format: TextFormat | None = None


class ConstructorAnswer(MaxObject):
    """Ответ конструктора сообщений."""

    messages: list[ConstructedMessageBody]
    allow_user_input: bool = False
    hint: str | None = None
    data: str | None = None
    keyboard: Keyboard | None = None
    placeholder: str | None = None
