"""Методы callback — /answers."""

from __future__ import annotations

from typing import ClassVar

from maxogram.methods.base import MaxMethod
from maxogram.types.constructor import ConstructedMessageBody
from maxogram.types.keyboard import Keyboard
from maxogram.types.message import NewMessageBody
from maxogram.types.misc import SimpleQueryResult


class AnswerOnCallback(MaxMethod["SimpleQueryResult"]):
    """POST /answers — Ответ на callback."""

    __api_path__: ClassVar[str] = "/answers"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = SimpleQueryResult
    __query_params__: ClassVar[frozenset[str]] = frozenset({"callback_id"})

    callback_id: str
    message: NewMessageBody | None = None
    notification: str | None = None


class Construct(MaxMethod["SimpleQueryResult"]):
    """POST /answers/constructor — Ответ конструктора."""

    __api_path__: ClassVar[str] = "/answers/constructor"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = SimpleQueryResult
    __query_params__: ClassVar[frozenset[str]] = frozenset({"session_id"})

    session_id: str
    messages: list[ConstructedMessageBody] | None = None
    allow_user_input: bool = False
    hint: str | None = None
    data: str | None = None
    keyboard: Keyboard | None = None
    placeholder: str | None = None
