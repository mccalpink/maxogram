"""WebhookHandler — aiohttp web handler для приёма webhook-уведомлений от Max."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aiohttp import web
from pydantic import TypeAdapter, ValidationError

from maxogram.types.update import Update

if TYPE_CHECKING:
    from maxogram.client.bot import Bot
    from maxogram.dispatcher.dispatcher import Dispatcher

logger = logging.getLogger(__name__)

__all__ = ["WebhookHandler"]

# TypeAdapter для discriminated union Update
_update_adapter: TypeAdapter[Update] = TypeAdapter(Update)

# Типы update, которые мы умеем парсить
_KNOWN_UPDATE_TYPES = frozenset({
    "message_created",
    "message_callback",
    "message_edited",
    "message_removed",
    "message_chat_created",
    "message_construction_request",
    "message_constructed",
    "bot_started",
    "bot_added",
    "bot_removed",
    "user_added",
    "user_removed",
    "chat_title_changed",
})


class WebhookHandler:
    """Aiohttp web handler для приёма webhook-уведомлений от Max.

    Принимает POST-запрос, парсит JSON payload в соответствующий
    Update тип (discriminated union по update_type), передаёт
    в dispatcher.feed_update().

    Max отправляет payload с полями на одном уровне:
    {update_type, timestamp, user_locale, message/callback/...}
    """

    def __init__(
        self,
        dispatcher: Dispatcher,
        bot: Bot,
    ) -> None:
        self._dispatcher = dispatcher
        self._bot = bot

    def register(self, app: web.Application, path: str = "/webhook") -> None:
        """Зарегистрировать POST route в aiohttp Application."""
        app.router.add_post(path, self._handle)

    async def _handle(self, request: web.Request) -> web.Response:
        """Обработать входящий webhook-запрос от Max.

        Возвращает 200 OK в большинстве случаев, чтобы Max
        не считал webhook сломанным и не отписал его.
        400 — только при невалидном JSON или отсутствии update_type.
        """
        # Парсинг JSON
        try:
            data: dict[str, Any] = await request.json()
        except Exception:
            logger.warning("Webhook: невалидный JSON в запросе")
            return web.json_response(
                {"ok": False, "error": "invalid json"},
                status=400,
            )

        # Проверка наличия update_type
        update_type = data.get("update_type")
        if not update_type:
            logger.warning("Webhook: отсутствует update_type в payload")
            return web.json_response(
                {"ok": False, "error": "missing update_type"},
                status=400,
            )

        # Неизвестный update_type — отвечаем 200, чтобы не ломать webhook
        if update_type not in _KNOWN_UPDATE_TYPES:
            logger.info("Webhook: неизвестный update_type=%s, пропускаем", update_type)
            return web.json_response({"ok": True})

        # Парсинг в Update модель
        try:
            update = _update_adapter.validate_python(data)
        except ValidationError:
            logger.exception("Webhook: ошибка парсинга update_type=%s", update_type)
            return web.json_response({"ok": True})

        # Обработка через dispatcher
        try:
            await self._dispatcher.feed_update(self._bot, update)
        except Exception:
            logger.exception("Webhook: ошибка обработки update_type=%s", update_type)

        return web.json_response({"ok": True})
