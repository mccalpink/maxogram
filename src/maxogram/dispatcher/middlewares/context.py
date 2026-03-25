"""MaxContextMiddleware — извлечение контекста пользователя и чата из событий."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from maxogram.dispatcher.middlewares.base import BaseMiddleware
from maxogram.types.user import User

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

__all__ = ["EventChat", "MaxContextMiddleware"]


@dataclass(frozen=True)
class EventChat:
    """Контекст чата из события."""

    chat_id: int


class MaxContextMiddleware(BaseMiddleware):
    """Извлечение event_from_user и event_chat из Update.

    Добавляет в data:
    - ``event_from_user``: :class:`User` | None — кто инициировал событие
    - ``event_chat``: :class:`EventChat` | None — в каком чате произошло
    """

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        user, chat_id = self._resolve_context(event)
        data["event_from_user"] = user
        data["event_chat"] = EventChat(chat_id=chat_id) if chat_id is not None else None
        return await handler(event, data)

    @staticmethod
    def _resolve_context(event: Any) -> tuple[User | None, int | None]:
        """Извлечь user и chat_id из события.

        Логика зависит от update_type, т.к. в Max API нет единого поля
        для пользователя и чата (в отличие от Telegram).
        """
        update_type = getattr(event, "update_type", None)

        if update_type in ("message_created", "message_edited"):
            message = getattr(event, "message", None)
            user = getattr(message, "sender", None) if message else None
            recipient = getattr(message, "recipient", None) if message else None
            chat_id = getattr(recipient, "chat_id", None) if recipient else None
            return user, chat_id

        if update_type == "message_callback":
            callback = getattr(event, "callback", None)
            user = getattr(callback, "user", None) if callback else None
            message = getattr(event, "message", None)
            recipient = getattr(message, "recipient", None) if message else None
            chat_id = getattr(recipient, "chat_id", None) if recipient else None
            return user, chat_id

        if update_type == "message_removed":
            return None, getattr(event, "chat_id", None)

        if update_type == "message_chat_created":
            chat_dict = getattr(event, "chat", None)
            chat_id = chat_dict.get("chat_id") if isinstance(chat_dict, dict) else None
            return None, chat_id

        if update_type == "message_construction_request":
            return getattr(event, "user", None), None

        if update_type == "message_constructed":
            return None, None

        # bot_started, bot_added, bot_removed, user_added, user_removed,
        # chat_title_changed — все имеют user и chat_id на верхнем уровне.
        user = getattr(event, "user", None)
        chat_id = getattr(event, "chat_id", None)
        return user, chat_id
