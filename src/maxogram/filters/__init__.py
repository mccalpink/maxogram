"""Система фильтров maxogram."""

from __future__ import annotations

from maxogram.filters.base import Filter
from maxogram.filters.callback_data import CallbackData
from maxogram.filters.chat_type import ChatTypeFilter
from maxogram.filters.command import Command, CommandObject
from maxogram.filters.content_type import ContentType, ContentTypeFilter
from maxogram.filters.exception import ExceptionTypeFilter
from maxogram.filters.magic_data import MagicData
from maxogram.filters.state import StateFilter
from maxogram.utils.magic_filter import MagicFilter

F = MagicFilter()
"""Глобальный экземпляр MagicFilter для DSL-фильтрации."""

__all__ = [
    "CallbackData",
    "ChatTypeFilter",
    "Command",
    "CommandObject",
    "ContentType",
    "ContentTypeFilter",
    "ExceptionTypeFilter",
    "F",
    "Filter",
    "MagicData",
    "StateFilter",
]
