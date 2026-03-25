"""Multibot — два бота в одном приложении.

Демонстрирует:
- Два экземпляра Bot с разными токенами
- Общий Dispatcher для обоих ботов
- dp.run_polling(bot1, bot2) — параллельный polling
- DI: хендлер получает правильный bot автоматически

Запуск:
    MAX_BOT_TOKEN_1=xxx MAX_BOT_TOKEN_2=yyy poetry run python examples/multibot.py
"""

from __future__ import annotations

import logging
import os

from maxogram.client.bot import Bot
from maxogram.dispatcher.dispatcher import Dispatcher
from maxogram.dispatcher.router import Router
from maxogram.types.message import Message

logging.basicConfig(level=logging.INFO)

router = Router(name="multibot")


# --- Хендлеры ---
# Каждый хендлер получает тот экземпляр Bot, от которого пришёл update.
# Dispatcher автоматически передаёт правильный bot через DI.


@router.message_created()
async def cmd_whoami(
    event: Message,
    bot: Bot,
    **kwargs: object,
) -> None:
    """Команда /whoami — бот отвечает своим именем.

    Каждый бот отвечает от своего имени, хотя хендлер один.
    """
    text = event.body.text
    if text != "/whoami":
        return
    chat_id = event.recipient.chat_id
    if chat_id is None:
        return

    # bot.token[:8] — первые символы токена для идентификации
    bot_id = bot.token[:8] if bot.token else "unknown"
    await bot.send_message(
        chat_id=chat_id,
        text=f"Я бот с токеном {bot_id}...",
    )


@router.message_created()
async def echo(
    event: Message,
    bot: Bot,
    **kwargs: object,
) -> None:
    """Эхо — работает для обоих ботов."""
    text = event.body.text
    if not text or text.startswith("/"):
        return
    chat_id = event.recipient.chat_id
    if chat_id is None:
        return

    await bot.send_message(chat_id=chat_id, text=f"Echo: {text}")


# --- Запуск ---


def main() -> None:
    """Точка входа: два бота, один диспатчер."""
    token1 = os.getenv("MAX_BOT_TOKEN_1")
    token2 = os.getenv("MAX_BOT_TOKEN_2")
    if not token1 or not token2:
        print(  # noqa: T201
            "Установите переменные окружения:\n"
            "  MAX_BOT_TOKEN_1 — токен первого бота\n"
            "  MAX_BOT_TOKEN_2 — токен второго бота"
        )
        return

    bot1 = Bot(token=token1)
    bot2 = Bot(token=token2)

    dp = Dispatcher()
    dp.include_router(router)

    # run_polling принимает произвольное количество ботов.
    # Каждый бот получает свой Polling instance, все работают
    # параллельно через asyncio.gather.
    dp.run_polling(bot1, bot2)


if __name__ == "__main__":
    main()
