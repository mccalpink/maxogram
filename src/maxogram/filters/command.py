"""Фильтр команд и результат парсинга."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import re

from maxogram.filters.base import Filter

__all__ = [
    "Command",
    "CommandObject",
]


@dataclass(frozen=True)
class CommandObject:
    """Результат парсинга команды.

    Атрибуты:
        prefix: Префикс команды (по умолчанию ``/``).
        command: Имя команды (без префикса и mention).
        args: Аргументы после команды или ``None``.
        regexp_match: Результат regexp-совпадения (для будущего расширения).
    """

    prefix: str = "/"
    command: str = ""
    args: str | None = None
    regexp_match: re.Match[str] | None = field(default=None, repr=False)


class Command(Filter):
    """Фильтр команд (``/start``, ``/help`` и т.д.).

    Парсит команду из ``body.text`` (без entities — в Max API их нет).
    При совпадении возвращает ``{"command": CommandObject(...)}``.

    Примеры::

        Command("start")           # /start
        Command("start", "help")   # /start или /help
        Command(prefix="!")        # !command
        Command(ignore_case=True)  # /Start == /start
        Command()                  # любая команда
    """

    def __init__(
        self,
        *commands: str,
        prefix: str = "/",
        ignore_case: bool = False,
        ignore_mention: bool = False,
    ) -> None:
        self.commands = commands
        self.prefix = prefix
        self.ignore_case = ignore_case
        # TODO: ignore_mention требует доступа к имени бота для проверки.
        # Пока mention всегда удаляется (поведение как ignore_mention=True).
        # Реализовать при добавлении Bot.me() в контекст фильтра.
        self.ignore_mention = ignore_mention

    async def __call__(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:
        """Проверить сообщение на наличие команды.

        Первый позиционный аргумент — объект сообщения (Message)
        или Update (MessageCreatedUpdate, MessageEditedUpdate и т.д.).
        """
        event = args[0] if args else None
        if event is None:
            return False

        # Если это Update с вложенным message — извлечь message
        message = event
        if hasattr(event, "update_type") and hasattr(event, "message"):
            message = event.message
            if message is None:
                return False

        # Получить текст из message.text (property) или message.body.text
        text = getattr(message, "text", None)
        if not text:
            body = getattr(message, "body", None)
            text = getattr(body, "text", None) if body else None
        if not text:
            return False

        command_obj = self._parse_command(text)
        if command_obj is None:
            return False

        # Проверить команду в списке (если задан)
        if self.commands:
            cmd = command_obj.command
            if self.ignore_case:
                if not any(c.lower() == cmd.lower() for c in self.commands):
                    return False
            else:
                if cmd not in self.commands:
                    return False

        return {"command": command_obj}

    def _parse_command(self, text: str) -> CommandObject | None:
        """Парсить текст в CommandObject.

        Формат: ``<prefix><command>[@mention] [args]``
        """
        if not text.startswith(self.prefix):
            return None

        # Убрать prefix
        without_prefix = text[len(self.prefix) :]

        # Разделить на command(+mention) и args
        parts = without_prefix.split(maxsplit=1)
        if not parts:
            return None

        command_part = parts[0]
        args = parts[1] if len(parts) > 1 else None

        # Убрать @mention из command
        if "@" in command_part:
            command_part, _ = command_part.split("@", 1)

        if not command_part:
            return None

        return CommandObject(
            prefix=self.prefix,
            command=command_part,
            args=args,
        )
