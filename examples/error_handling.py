"""Error Handling — обработка ошибок в хендлерах.

Демонстрирует:
- Регистрацию error observer через router.error()
- ErrorEvent с доступом к исключению и оригинальному update
- ExceptionTypeFilter для фильтрации по типу исключения
- Намеренную ошибку в хендлере для демонстрации

Запуск:
    MAX_BOT_TOKEN=xxx poetry run python examples/error_handling.py
"""

from __future__ import annotations

import logging
import os

from maxogram.client.bot import Bot
from maxogram.dispatcher.dispatcher import Dispatcher
from maxogram.dispatcher.middlewares.error import ErrorEvent
from maxogram.dispatcher.router import Router
from maxogram.filters.exception import ExceptionTypeFilter
from maxogram.types.message import Message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router(name="errors")


# --- Error handlers ---
# Регистрируются через router.error() — вызываются при необработанных исключениях.
# ErrorEvent содержит: .exception (исключение) и .update (оригинальное событие).


@router.error(ExceptionTypeFilter(ValueError))
async def handle_value_error(
    event: ErrorEvent,
    bot: Bot,
    **kwargs: object,
) -> bool:
    """Обработка ValueError — ожидаемые ошибки валидации.

    ExceptionTypeFilter пропускает только указанные типы исключений.
    Возвращаем True — ошибка обработана, не пробрасывается дальше.
    """
    logger.warning(
        "ValueError перехвачен: %s", event.exception,
    )
    # Можно уведомить пользователя, если есть доступ к chat_id
    return True


@router.error()
async def handle_any_error(
    event: ErrorEvent,
    bot: Bot,
    **kwargs: object,
) -> bool:
    """Fallback — ловит все остальные необработанные исключения.

    Хендлеры ошибок проверяются в порядке регистрации.
    Этот хендлер без фильтра — catch-all для всего, что не поймали выше.
    """
    logger.error(
        "Необработанная ошибка: %s: %s",
        type(event.exception).__name__,
        event.exception,
    )
    return True


# --- Обычные хендлеры ---


@router.message_created()
async def cmd_error(
    event: Message,
    bot: Bot,
    **kwargs: object,
) -> None:
    """Команда /error — намеренно вызывает ValueError.

    ErrorsMiddleware перехватит исключение и передаст в error observer.
    """
    text = event.body.text
    if text != "/error":
        return

    # Эта ошибка будет перехвачена handle_value_error
    msg = "Демонстрация: невалидное значение"
    raise ValueError(msg)


@router.message_created()
async def cmd_crash(
    event: Message,
    bot: Bot,
    **kwargs: object,
) -> None:
    """Команда /crash — вызывает RuntimeError.

    Будет перехвачена handle_any_error (fallback).
    """
    text = event.body.text
    if text != "/crash":
        return

    msg = "Демонстрация: неожиданный сбой"
    raise RuntimeError(msg)


@router.message_created()
async def echo(
    event: Message,
    bot: Bot,
    **kwargs: object,
) -> None:
    """Эхо — нормальная работа без ошибок."""
    text = event.body.text
    if not text or text.startswith("/"):
        return
    chat_id = event.recipient.chat_id
    if chat_id is None:
        return

    await bot.send_message(chat_id=chat_id, text=f"Echo: {text}")


# --- Запуск ---


def main() -> None:
    """Точка входа."""
    token = os.getenv("MAX_BOT_TOKEN")
    if not token:
        print("Установите переменную окружения MAX_BOT_TOKEN")  # noqa: T201
        return

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)
    dp.run_polling(bot)


if __name__ == "__main__":
    main()
