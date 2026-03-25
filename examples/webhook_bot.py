"""Webhook Bot — бот с webhook для production deployment.

Демонстрирует:
- Настройку WebhookManager с aiohttp-сервером
- Хендлер на message_created
- Graceful shutdown и auto-reconnect

Запуск:
    MAX_BOT_TOKEN=xxx poetry run python examples/webhook_bot.py

Требования к production:
- HTTPS с CA-signed сертификатом (Let's Encrypt, etc.)
- Nginx/Caddy как reverse proxy на порт 8080
- IP-whitelist для Max API серверов (см. dev.max.ru)
"""

from __future__ import annotations

import logging
import os

from maxogram.client.bot import Bot
from maxogram.dispatcher.dispatcher import Dispatcher
from maxogram.dispatcher.router import Router
from maxogram.types.message import Message
from maxogram.webhook.manager import WebhookManager

logging.basicConfig(level=logging.INFO)

router = Router(name="webhook")


# --- Хендлеры ---


@router.message_created()
async def on_message(
    event: Message,
    bot: Bot,
    **kwargs: object,
) -> None:
    """Эхо-ответ на любое сообщение."""
    text = event.body.text
    chat_id = event.recipient.chat_id
    if text and chat_id:
        await bot.send_message(chat_id=chat_id, text=f"Webhook echo: {text}")


# --- Запуск ---


def main() -> None:
    """Точка входа: создание бота, диспатчера и запуск webhook-сервера."""
    token = os.getenv("MAX_BOT_TOKEN")
    if not token:
        print("Установите переменную окружения MAX_BOT_TOKEN")  # noqa: T201
        return

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)

    # WebhookManager управляет жизненным циклом:
    # - подписка/отписка webhook через Bot API
    # - auto-reconnect (переподписка каждые 7.5 часов)
    # - graceful shutdown по SIGINT/SIGTERM
    manager = WebhookManager(
        dispatcher=dp,
        bot=bot,
        host="0.0.0.0",   # слушаем на всех интерфейсах
        port=8080,         # Nginx проксирует 443 → 8080
        path="/webhook",   # endpoint для приёма обновлений
    )

    # webhook_url — публичный HTTPS URL, доступный серверам Max
    # Пример: https://mybot.example.com/webhook
    webhook_url = os.getenv("WEBHOOK_URL", "https://mybot.example.com/webhook")
    manager.run(webhook_url)


if __name__ == "__main__":
    main()
