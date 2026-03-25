"""Scene Bot — бот-анкета через WizardScene.

Демонстрирует:
- WizardScene с пошаговой навигацией (имя → возраст → подтверждение)
- SceneRegistry для управления сценами
- Вход в сцену по команде /start

Запуск:
    MAX_BOT_TOKEN=xxx poetry run python examples/scene_bot.py
"""

from __future__ import annotations

import logging
import os

from maxogram.client.bot import Bot
from maxogram.dispatcher.dispatcher import Dispatcher
from maxogram.dispatcher.router import Router
from maxogram.fsm.context import FSMContext
from maxogram.fsm.middleware import FSMContextMiddleware
from maxogram.fsm.scene.registry import SceneRegistry
from maxogram.fsm.scene.wizard import WizardScene
from maxogram.fsm.state import State, StatesGroup
from maxogram.fsm.storage.memory import MemoryStorage
from maxogram.types.message import Message

logging.basicConfig(level=logging.INFO)

router = Router(name="scenes")


# --- Определяем состояния и сцену ---


class SurveyStates(StatesGroup):
    """Шаги анкеты: имя → возраст → подтверждение."""

    name = State()
    age = State()
    confirm = State()


class SurveyWizard(WizardScene, state=SurveyStates):
    """Wizard-сцена: последовательный сбор данных от пользователя.

    on_enter/on_leave можно переопределить для кастомной логики
    при входе/выходе из сцены. Здесь не нужно — логика в хендлерах ниже.
    """


# --- Регистрация сцены ---


# SceneRegistry создаёт экземпляры сцен и подключает их как sub_routers
registry = SceneRegistry(router=router)
registry.add(SurveyWizard)


# --- Хендлеры ---


@router.message_created()
async def cmd_start(
    event: Message,
    bot: Bot,
    state: FSMContext,
    **kwargs: object,
) -> None:
    """Команда /start — вход в сцену анкеты."""
    text = event.body.text
    if not text or not text.startswith("/start"):
        return
    chat_id = event.recipient.chat_id
    if chat_id is None:
        return

    # Вход в сцену по имени — SceneRegistry автоматически выйдет
    # из текущей сцены (если была) и войдёт в новую
    await registry.enter(ctx=state, name="SurveyWizard")
    await bot.send_message(chat_id=chat_id, text="Привет! Как вас зовут?")


@router.message_created()
async def process_name(
    event: Message,
    bot: Bot,
    state: FSMContext,
    raw_state: str | None = None,
    **kwargs: object,
) -> None:
    """Шаг 1: получить имя, перейти к возрасту."""
    if raw_state != str(SurveyStates.name):
        return
    text = event.body.text
    chat_id = event.recipient.chat_id
    if chat_id is None:
        return

    await state.update_data(name=text)

    # WizardScene предоставляет навигацию: next(), back(), goto()
    scene = registry.get("SurveyWizard")
    await scene.next(state)
    await bot.send_message(chat_id=chat_id, text=f"{text}, сколько вам лет?")


@router.message_created()
async def process_age(
    event: Message,
    bot: Bot,
    state: FSMContext,
    raw_state: str | None = None,
    **kwargs: object,
) -> None:
    """Шаг 2: получить возраст, перейти к подтверждению."""
    if raw_state != str(SurveyStates.age):
        return
    text = event.body.text
    chat_id = event.recipient.chat_id
    if chat_id is None:
        return

    await state.update_data(age=text)

    scene = registry.get("SurveyWizard")
    await scene.next(state)
    data = await state.get_data()
    await bot.send_message(
        chat_id=chat_id,
        text=f"Подтвердите данные:\nИмя: {data['name']}\nВозраст: {data['age']}\n\n"
        f"Отправьте 'да' для подтверждения или 'нет' для отмены.",
    )


@router.message_created()
async def process_confirm(
    event: Message,
    bot: Bot,
    state: FSMContext,
    raw_state: str | None = None,
    **kwargs: object,
) -> None:
    """Шаг 3: подтверждение — завершить или вернуться назад."""
    if raw_state != str(SurveyStates.confirm):
        return
    text = (event.body.text or "").lower()
    chat_id = event.recipient.chat_id
    if chat_id is None:
        return

    scene = registry.get("SurveyWizard")

    if text == "да":
        data = await state.get_data()
        await scene.leave(state)
        await bot.send_message(
            chat_id=chat_id,
            text=f"Анкета сохранена! {data['name']}, {data['age']} лет.",
        )
    elif text == "нет":
        # Возврат к первому шагу
        await scene.goto(state, step=0)
        await bot.send_message(chat_id=chat_id, text="Начнём сначала. Как вас зовут?")
    else:
        await bot.send_message(chat_id=chat_id, text="Отправьте 'да' или 'нет'.")


# --- Запуск ---


def main() -> None:
    """Точка входа."""
    token = os.getenv("MAX_BOT_TOKEN")
    if not token:
        print("Установите переменную окружения MAX_BOT_TOKEN")  # noqa: T201
        return

    bot = Bot(token=token)
    dp = Dispatcher()

    # FSM middleware — обязателен для работы со сценами
    storage = MemoryStorage()
    dp.update.outer_middleware.register(FSMContextMiddleware(storage=storage))

    dp.include_router(router)
    dp.run_polling(bot)


if __name__ == "__main__":
    main()
