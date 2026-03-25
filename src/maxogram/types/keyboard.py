"""Типы клавиатуры Max API."""

from __future__ import annotations

from maxogram.types.base import MaxObject
from maxogram.types.button import Button


class InlineKeyboardAttachmentPayload(MaxObject):
    """Payload inline-клавиатуры (получение из API)."""

    buttons: list[list[Button]]


class InlineKeyboardAttachmentRequest(MaxObject):
    """Payload inline-клавиатуры (для отправки)."""

    buttons: list[list[Button]]


class Keyboard(MaxObject):
    """Клавиатура (используется в конструкторе сообщений)."""

    buttons: list[list[Button]]
