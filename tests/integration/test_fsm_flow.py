"""Интеграционные тесты: полный FSM flow.

1. /start -> state=waiting_name
2. Пользователь вводит имя -> state=waiting_age, data["name"] сохранено
3. Пользователь вводит возраст -> state=None (clear), данные полные
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from maxogram.client.bot import Bot
from maxogram.dispatcher.dispatcher import Dispatcher
from maxogram.enums import ChatType
from maxogram.filters.base import Filter
from maxogram.filters.command import Command, CommandObject
from maxogram.fsm.context import FSMContext
from maxogram.fsm.middleware import FSMContextMiddleware
from maxogram.fsm.state import State, StatesGroup
from maxogram.fsm.storage.memory import MemoryStorage
from maxogram.types.message import Message, MessageBody, Recipient
from maxogram.types.update import MessageCreatedUpdate
from maxogram.types.user import User


class RegistrationForm(StatesGroup):
    """Группа состояний регистрации."""

    waiting_name = State()
    waiting_age = State()


class _MessageCommandFilter(Filter):
    """Обёртка Command для работы с Message напрямую.

    После изменений в dispatcher хендлеры message_created получают Message,
    поэтому фильтр тоже получает Message напрямую.
    """

    def __init__(self, *commands: str, prefix: str = "/", ignore_case: bool = False) -> None:
        self._command = Command(*commands, prefix=prefix, ignore_case=ignore_case)

    async def __call__(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:
        """Применить Command filter к Message."""
        message = args[0] if args else None
        if message is None:
            return False
        return await self._command(message)


class _StateFilter(Filter):
    """Фильтр по raw_state из FSMContextMiddleware."""

    def __init__(self, state: State) -> None:
        self._state = state

    async def __call__(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:
        """Проверить raw_state в kwargs."""
        raw_state = kwargs.get("raw_state")
        return raw_state == self._state.state


def _make_bot() -> AsyncMock:
    """Создать мок Bot."""
    bot = AsyncMock(spec=Bot)
    bot.token = "test-token"
    bot._me = None
    return bot


def _make_message_update(
    *,
    text: str = "hello",
    user_id: int = 1,
    chat_id: int = 100,
) -> MessageCreatedUpdate:
    """Создать MessageCreatedUpdate для тестов."""
    user = User(user_id=user_id, name="Test", is_bot=False, last_activity_time=0)
    recipient = Recipient(chat_id=chat_id, chat_type=ChatType.DIALOG)
    body = MessageBody(mid="mid1", seq=1, text=text)
    msg = Message(sender=user, recipient=recipient, timestamp=0, body=body)
    return MessageCreatedUpdate(timestamp=0, message=msg)


class TestFSMFlow:
    """Полный FSM flow: /start -> имя -> возраст -> clear."""

    @pytest.mark.asyncio
    async def test_full_registration_flow(self) -> None:
        """Сквозной тест: 3 шага FSM с сохранением данных."""
        dp = Dispatcher()
        storage = MemoryStorage()
        dp.update.outer_middleware.register(
            FSMContextMiddleware(storage=storage),
        )
        bot = _make_bot()
        collected_data: dict[str, Any] = {}

        # --- Хендлеры ---

        async def start_handler(
            event: Message,
            state: FSMContext,
            command: CommandObject,
        ) -> str:
            """Хендлер /start: устанавливает waiting_name."""
            await state.set_state(RegistrationForm.waiting_name)
            return "ask_name"

        async def name_handler(
            event: Message,
            state: FSMContext,
        ) -> str:
            """Хендлер имени: сохраняет имя, переход к waiting_age."""
            name = event.body.text or ""
            await state.update_data(data={"name": name})
            await state.set_state(RegistrationForm.waiting_age)
            return "ask_age"

        async def age_handler(
            event: Message,
            state: FSMContext,
        ) -> str:
            """Хендлер возраста: завершает FSM, собирает данные."""
            age = event.body.text or ""
            await state.update_data(data={"age": age})
            fsm_data = await state.get_data()
            collected_data.update(fsm_data)
            await state.clear()
            return "done"

        # Порядок регистрации: Command filter, StateFilter для каждого шага
        dp.message_created.register(start_handler, _MessageCommandFilter("start"))
        dp.message_created.register(
            name_handler,
            _StateFilter(RegistrationForm.waiting_name),
        )
        dp.message_created.register(
            age_handler,
            _StateFilter(RegistrationForm.waiting_age),
        )

        # --- Шаг 1: /start ---
        update_start = _make_message_update(text="/start", user_id=1, chat_id=100)
        result = await dp.feed_update(bot, update_start)
        assert result == "ask_name"

        # --- Шаг 2: ввод имени ---
        update_name = _make_message_update(text="Вадим", user_id=1, chat_id=100)
        result = await dp.feed_update(bot, update_name)
        assert result == "ask_age"

        # --- Шаг 3: ввод возраста ---
        update_age = _make_message_update(text="30", user_id=1, chat_id=100)
        result = await dp.feed_update(bot, update_age)
        assert result == "done"

        # Проверяем собранные данные
        assert collected_data == {"name": "Вадим", "age": "30"}

    @pytest.mark.asyncio
    async def test_fsm_state_isolation_between_users(self) -> None:
        """FSM состояния изолированы между пользователями."""
        dp = Dispatcher()
        storage = MemoryStorage()
        dp.update.outer_middleware.register(
            FSMContextMiddleware(storage=storage),
        )
        bot = _make_bot()

        async def start_handler(
            event: Message,
            state: FSMContext,
            command: CommandObject,
        ) -> str:
            """Хендлер /start."""
            await state.set_state(RegistrationForm.waiting_name)
            return "ask_name"

        async def name_handler(
            event: Message,
            state: FSMContext,
            raw_state: str | None = None,
        ) -> str:
            """Хендлер имени."""
            if raw_state != RegistrationForm.waiting_name.state:
                return "no_state"
            return "has_state"

        dp.message_created.register(start_handler, _MessageCommandFilter("start"))
        dp.message_created.register(name_handler)

        # User 1: /start -> waiting_name
        update_user1 = _make_message_update(text="/start", user_id=1, chat_id=100)
        await dp.feed_update(bot, update_user1)

        # User 2: сообщение без /start -> raw_state == None
        update_user2 = _make_message_update(text="hello", user_id=2, chat_id=200)
        result = await dp.feed_update(bot, update_user2)
        assert result == "no_state"

        # User 1: сообщение -> raw_state == waiting_name
        update_user1_name = _make_message_update(text="Вадим", user_id=1, chat_id=100)
        result = await dp.feed_update(bot, update_user1_name)
        assert result == "has_state"

    @pytest.mark.asyncio
    async def test_fsm_clear_resets_state_and_data(self) -> None:
        """clear() сбрасывает и state, и data."""
        dp = Dispatcher()
        storage = MemoryStorage()
        dp.update.outer_middleware.register(
            FSMContextMiddleware(storage=storage),
        )
        bot = _make_bot()

        async def set_and_clear(
            event: Message,
            state: FSMContext,
            raw_state: str | None = None,
        ) -> str:
            """Установить состояние, данные, затем очистить."""
            if raw_state is None:
                await state.set_state(RegistrationForm.waiting_name)
                await state.update_data(data={"test_key": "value"})
                return "set"
            await state.clear()
            return "cleared"

        dp.message_created.register(set_and_clear)

        # Первый вызов: set state + data
        update1 = _make_message_update(text="first", user_id=1, chat_id=100)
        result = await dp.feed_update(bot, update1)
        assert result == "set"

        # Второй вызов: raw_state != None -> clear
        update2 = _make_message_update(text="second", user_id=1, chat_id=100)
        result = await dp.feed_update(bot, update2)
        assert result == "cleared"

        # Третий вызов: raw_state == None после clear
        update3 = _make_message_update(text="third", user_id=1, chat_id=100)
        result = await dp.feed_update(bot, update3)
        assert result == "set"
