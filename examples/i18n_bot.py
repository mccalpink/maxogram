"""I18n Bot — мультиязычный бот с переводами.

Демонстрирует:
- I18n с двумя локалями (ru, en)
- I18nMiddleware для автоматического определения локали
- Использование gettext и lazy_gettext в хендлерах
- Переключение языка по команде /lang

Запуск:
    MAX_BOT_TOKEN=xxx poetry run python examples/i18n_bot.py

Структура переводов (создать перед запуском):
    locales/
    ├── ru/LC_MESSAGES/messages.mo
    └── en/LC_MESSAGES/messages.mo
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable

from maxogram.client.bot import Bot
from maxogram.dispatcher.dispatcher import Dispatcher
from maxogram.dispatcher.router import Router
from maxogram.fsm.context import FSMContext
from maxogram.fsm.middleware import FSMContextMiddleware
from maxogram.fsm.storage.memory import MemoryStorage
from maxogram.i18n.core import I18n
from maxogram.i18n.middleware import I18nMiddleware
from maxogram.types.message import Message

logging.basicConfig(level=logging.INFO)

router = Router(name="i18n")

# Менеджер переводов: ищет .mo файлы в locales/
i18n = I18n(path=Path("locales"), default_locale="ru", domain="messages")

# lazy_gettext — перевод вычисляется при обращении к str(),
# а не при определении. Полезно для констант на уровне модуля.
__ = i18n.lazy_gettext
WELCOME_TEXT = __("Welcome to the bot!")


# --- Хендлеры ---


@router.message_created()
async def cmd_start(
    event: Message,
    bot: Bot,
    gettext: Callable[[str], str],
    **kwargs: object,
) -> None:
    """Команда /start — приветствие на языке пользователя.

    gettext инжектируется I18nMiddleware и уже привязан к текущей локали.
    """
    text = event.body.text
    if not text or not text.startswith("/start"):
        return
    chat_id = event.recipient.chat_id
    if chat_id is None:
        return

    _ = gettext
    await bot.send_message(
        chat_id=chat_id,
        text=_(
            "Hello! I'm a multilingual bot.\n"
            "Commands:\n"
            "/start — greeting\n"
            "/lang — switch language"
        ),
    )


@router.message_created()
async def cmd_lang(
    event: Message,
    bot: Bot,
    state: FSMContext,
    i18n_locale: str,
    gettext: Callable[[str], str],
    **kwargs: object,
) -> None:
    """Команда /lang — переключение языка (ru ↔ en).

    Сохраняем выбранный язык в FSM data для последующих запросов.
    """
    text = event.body.text
    if text != "/lang":
        return
    chat_id = event.recipient.chat_id
    if chat_id is None:
        return

    # Переключаем: ru → en, en → ru
    new_locale = "en" if i18n_locale == "ru" else "ru"
    await state.update_data(locale=new_locale)

    # Отвечаем уже на новом языке
    _ = lambda msg: i18n.gettext(msg, locale=new_locale)  # noqa: E731
    await bot.send_message(
        chat_id=chat_id,
        text=_("Language switched!"),
    )


@router.message_created()
async def echo(
    event: Message,
    bot: Bot,
    gettext: Callable[[str], str],
    **kwargs: object,
) -> None:
    """Эхо с переведённым префиксом."""
    text = event.body.text
    if not text or text.startswith("/"):
        return
    chat_id = event.recipient.chat_id
    if chat_id is None:
        return

    _ = gettext
    await bot.send_message(
        chat_id=chat_id,
        text=f"{_('You said')}: {text}",
    )


# --- Запуск ---


def main() -> None:
    """Точка входа."""
    token = os.getenv("MAX_BOT_TOKEN")
    if not token:
        print("Установите переменную окружения MAX_BOT_TOKEN")  # noqa: T201
        return

    bot = Bot(token=token)
    dp = Dispatcher()

    # FSM middleware — для хранения выбранного языка пользователя
    storage = MemoryStorage()
    dp.update.outer_middleware.register(FSMContextMiddleware(storage=storage))

    # I18nMiddleware — определяет локаль и инжектирует gettext в хендлеры.
    # По умолчанию берёт локаль из event.user_locale (webhook payload).
    # Можно задать свой locale_resolver для кастомной логики.
    dp.update.outer_middleware.register(I18nMiddleware(i18n=i18n))

    dp.include_router(router)
    dp.run_polling(bot)


if __name__ == "__main__":
    main()
