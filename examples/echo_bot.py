"""Echo Bot -- пример бота на maxogram.

Демонстрирует:
- Обработку команд (/start, /keyboard, /form)
- Echo сообщений
- Inline-клавиатуру
- Обработку callback
- FSM (простая форма с состояниями)
"""

from __future__ import annotations

import logging
import os

from maxogram.client.bot import Bot
from maxogram.dispatcher.dispatcher import Dispatcher
from maxogram.dispatcher.router import Router
from maxogram.fsm.context import FSMContext
from maxogram.fsm.middleware import FSMContextMiddleware
from maxogram.fsm.state import State, StatesGroup
from maxogram.fsm.storage.memory import MemoryStorage
from maxogram.types.update import MessageCallbackUpdate, MessageCreatedUpdate
from maxogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO)

router = Router(name="echo")


# --- Состояния FSM ---


class Form(StatesGroup):
    """Простая форма: имя + возраст."""

    name = State()
    age = State()


# --- Вспомогательные функции ---


def _get_text(event: MessageCreatedUpdate) -> str | None:
    """Извлечь текст из события message_created."""
    return event.message.body.text


def _get_chat_id(event: MessageCreatedUpdate) -> int | None:
    """Извлечь chat_id из события message_created."""
    return event.message.recipient.chat_id


# --- Хендлеры ---


@router.message_created()
async def cmd_start(
    event: MessageCreatedUpdate,
    bot: Bot,
    state: FSMContext,
    raw_state: str | None = None,
    **kwargs: object,
) -> None:
    """Обработка /start."""
    text = _get_text(event)
    if not text or not text.startswith("/start"):
        return
    chat_id = _get_chat_id(event)
    if chat_id is None:
        return

    # Сбрасываем FSM, если было активное состояние
    if raw_state:
        await state.clear()

    await bot.send_message(
        chat_id=chat_id,
        text=(
            "Привет! Я echo-бот на maxogram.\n"
            "Команды:\n"
            "/start -- начало работы\n"
            "/keyboard -- покажу inline-клавиатуру\n"
            "/form -- заполнить форму (FSM)"
        ),
    )


@router.message_created()
async def cmd_keyboard(
    event: MessageCreatedUpdate,
    bot: Bot,
    **kwargs: object,
) -> None:
    """Показать inline-клавиатуру."""
    text = _get_text(event)
    if text != "/keyboard":
        return
    chat_id = _get_chat_id(event)
    if chat_id is None:
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Like", payload="like")
    builder.button(text="Dislike", payload="dislike")
    builder.adjust(2)

    await bot.send_message(
        chat_id=chat_id,
        text="Оцените maxogram:",
        attachments=[builder.as_attachment()],
    )


@router.message_callback()
async def on_callback(
    event: MessageCallbackUpdate,
    bot: Bot,
    **kwargs: object,
) -> None:
    """Обработка нажатия inline-кнопки."""
    callback = event.callback
    payload = callback.payload

    if payload == "like":
        notification = "Спасибо!"
    elif payload == "dislike":
        notification = "Мы станем лучше!"
    else:
        notification = f"Callback: {payload}"

    await bot.answer_on_callback(
        callback_id=callback.callback_id,
        notification=notification,
    )


@router.message_created()
async def cmd_form(
    event: MessageCreatedUpdate,
    bot: Bot,
    state: FSMContext,
    **kwargs: object,
) -> None:
    """Начать заполнение формы."""
    text = _get_text(event)
    if text != "/form":
        return
    chat_id = _get_chat_id(event)
    if chat_id is None:
        return

    await state.set_state(Form.name)
    await bot.send_message(
        chat_id=chat_id,
        text="Как вас зовут?",
    )


@router.message_created()
async def process_name(
    event: MessageCreatedUpdate,
    bot: Bot,
    state: FSMContext,
    raw_state: str | None = None,
    **kwargs: object,
) -> None:
    """Получить имя и спросить возраст."""
    if raw_state != str(Form.name):
        return
    text = _get_text(event)
    chat_id = _get_chat_id(event)
    if chat_id is None:
        return

    await state.update_data(name=text)
    await state.set_state(Form.age)
    await bot.send_message(
        chat_id=chat_id,
        text=f"Приятно познакомиться, {text}! Сколько вам лет?",
    )


@router.message_created()
async def process_age(
    event: MessageCreatedUpdate,
    bot: Bot,
    state: FSMContext,
    raw_state: str | None = None,
    **kwargs: object,
) -> None:
    """Получить возраст и завершить форму."""
    if raw_state != str(Form.age):
        return
    text = _get_text(event)
    chat_id = _get_chat_id(event)
    if chat_id is None:
        return

    await state.update_data(age=text)
    data = await state.get_data()
    await state.clear()

    await bot.send_message(
        chat_id=chat_id,
        text=f"Форма заполнена!\nИмя: {data['name']}\nВозраст: {data['age']}",
    )


@router.message_created()
async def echo(
    event: MessageCreatedUpdate,
    bot: Bot,
    raw_state: str | None = None,
    **kwargs: object,
) -> None:
    """Повторить сообщение пользователя (fallback)."""
    if raw_state:
        return
    text = _get_text(event)
    if text and text.startswith("/"):
        return
    chat_id = _get_chat_id(event)
    if chat_id is None:
        return

    await bot.send_message(
        chat_id=chat_id,
        text=f"Эхо: {text or '(нет текста)'}",
    )


# --- Запуск ---


def main() -> None:
    """Точка входа: создание бота, диспатчера и запуск polling."""
    token = os.getenv("MAX_BOT_TOKEN")
    if not token:
        print("Установите переменную окружения MAX_BOT_TOKEN")  # noqa: T201
        return

    bot = Bot(token=token)
    dp = Dispatcher()

    # FSM middleware
    storage = MemoryStorage()
    dp.update.outer_middleware.register(FSMContextMiddleware(storage=storage))

    dp.include_router(router)
    dp.run_polling(bot)


if __name__ == "__main__":
    main()
