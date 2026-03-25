"""Интеграционные тесты: echo bot flow.

Сквозной тест: Dispatcher получает Update -> Router маршрутизирует
-> Handler обрабатывает -> Bot отвечает.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from maxogram.client.bot import Bot
from maxogram.dispatcher.dispatcher import Dispatcher
from maxogram.dispatcher.event.bases import UNHANDLED
from maxogram.dispatcher.middlewares.base import BaseMiddleware
from maxogram.dispatcher.middlewares.context import EventChat
from maxogram.dispatcher.middlewares.error import ErrorEvent
from maxogram.dispatcher.router import Router
from maxogram.enums import ChatType
from maxogram.filters.base import Filter
from maxogram.filters.command import Command, CommandObject
from maxogram.types.message import Message, MessageBody, Recipient
from maxogram.types.update import MessageCreatedUpdate
from maxogram.types.user import User

# NOTE: После изменений в dispatcher хендлеры message_created получают Message,
# а не MessageCreatedUpdate. _make_message_update() по-прежнему создаёт
# MessageCreatedUpdate (это то, что приходит в dispatcher), а dispatcher сам
# разворачивает его до Message перед вызовом хендлера.


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


class TestEchoBot:
    """Сквозные тесты echo-бота."""

    @pytest.mark.asyncio
    async def test_simple_echo_handler_called(self) -> None:
        """message_created handler вызывается и возвращает результат."""
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update(text="привет")
        received_texts: list[str] = []

        async def echo_handler(event: Message) -> str:
            """Echo-хендлер: запоминает текст."""
            received_texts.append(event.body.text or "")
            return "echoed"

        dp.message_created.register(echo_handler)
        result = await dp.feed_update(bot, update)

        assert result == "echoed"
        assert received_texts == ["привет"]

    @pytest.mark.asyncio
    async def test_command_start_filter(self) -> None:
        """Command filter работает через адаптер, CommandObject в kwargs."""
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update(text="/start deep_link_param")
        received_commands: list[CommandObject] = []

        async def start_handler(
            event: Message,
            command: CommandObject,
        ) -> str:
            """Хендлер /start: принимает CommandObject через DI."""
            received_commands.append(command)
            return "started"

        dp.message_created.register(
            start_handler,
            _MessageCommandFilter("start"),
        )
        result = await dp.feed_update(bot, update)

        assert result == "started"
        assert len(received_commands) == 1
        cmd = received_commands[0]
        assert cmd.command == "start"
        assert cmd.prefix == "/"
        assert cmd.args == "deep_link_param"

    @pytest.mark.asyncio
    async def test_sub_router_handles_message(self) -> None:
        """Handler в sub_router обрабатывает сообщение."""
        dp = Dispatcher()
        sub_router = Router(name="sub")
        dp.include_router(sub_router)
        bot = _make_bot()
        update = _make_message_update(text="from sub")
        handled_by: list[str] = []

        async def sub_handler(event: Message) -> str:
            """Хендлер в дочернем роутере."""
            handled_by.append("sub_router")
            return "sub_ok"

        sub_router.message_created.register(sub_handler)
        result = await dp.feed_update(bot, update)

        assert result == "sub_ok"
        assert handled_by == ["sub_router"]

    @pytest.mark.asyncio
    async def test_unhandled_when_no_handlers(self) -> None:
        """Без handler -> UNHANDLED."""
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update()

        result = await dp.feed_update(bot, update)

        assert result is UNHANDLED

    @pytest.mark.asyncio
    async def test_middleware_modifies_data(self) -> None:
        """Middleware модифицирует data, хендлер получает изменённые данные."""
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update()
        received_values: list[str] = []

        class InjectMiddleware(BaseMiddleware):
            """Тестовый middleware: добавляет custom_key в data."""

            async def __call__(
                self,
                handler: Any,
                event: Any,
                data: dict[str, Any],
            ) -> Any:
                data["custom_key"] = "injected_value"
                return await handler(event, data)

        async def handler_with_custom(
            event: Message,
            custom_key: str = "",
        ) -> str:
            """Хендлер: принимает custom_key из middleware."""
            received_values.append(custom_key)
            return "ok"

        dp.update.outer_middleware.register(InjectMiddleware())
        dp.message_created.register(handler_with_custom)
        await dp.feed_update(bot, update)

        assert received_values == ["injected_value"]

    @pytest.mark.asyncio
    async def test_max_context_middleware_injects_user_and_chat(self) -> None:
        """MaxContextMiddleware добавляет event_from_user и event_chat в data."""
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update(user_id=42, chat_id=777)
        received: dict[str, Any] = {}

        async def handler(
            event: Message,
            event_from_user: User | None = None,
            event_chat: EventChat | None = None,
        ) -> str:
            """Хендлер: проверяет контекстные данные."""
            received["user"] = event_from_user
            received["chat"] = event_chat
            return "ok"

        dp.message_created.register(handler)
        await dp.feed_update(bot, update)

        assert received["user"] is not None
        assert received["user"].user_id == 42
        assert received["chat"] is not None
        assert received["chat"].chat_id == 777

    @pytest.mark.asyncio
    async def test_errors_middleware_catches_exception(self) -> None:
        """Ошибка в хендлере -> error handler вызывается."""
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update()
        error_events: list[ErrorEvent] = []

        async def bad_handler(event: Message) -> None:
            """Хендлер с ошибкой."""
            msg = "test error"
            raise ValueError(msg)

        async def error_handler(event: ErrorEvent) -> str:
            """Перехват ошибки."""
            error_events.append(event)
            return "error_caught"

        dp.message_created.register(bad_handler)
        dp.error.register(error_handler)
        result = await dp.feed_update(bot, update)

        assert result == "error_caught"
        assert len(error_events) == 1
        assert isinstance(error_events[0].exception, ValueError)
        assert str(error_events[0].exception) == "test error"

    @pytest.mark.asyncio
    async def test_command_filter_does_not_match_plain_text(self) -> None:
        """Command filter не матчит обычный текст."""
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update(text="просто текст")

        async def start_handler(
            event: Message,
            command: CommandObject,
        ) -> str:
            """Хендлер /start."""
            return "started"

        dp.message_created.register(
            start_handler,
            _MessageCommandFilter("start"),
        )
        result = await dp.feed_update(bot, update)

        assert result is UNHANDLED

    @pytest.mark.asyncio
    async def test_dispatcher_handler_has_priority_over_sub_router(self) -> None:
        """Хендлер в Dispatcher вызывается раньше, чем в sub_router."""
        dp = Dispatcher()
        sub = Router(name="sub")
        dp.include_router(sub)
        bot = _make_bot()
        update = _make_message_update()
        call_order: list[str] = []

        async def dp_handler(event: Message) -> str:
            """Хендлер Dispatcher."""
            call_order.append("dp")
            return "dp"

        async def sub_handler(event: Message) -> str:
            """Хендлер sub_router."""
            call_order.append("sub")
            return "sub"

        dp.message_created.register(dp_handler)
        sub.message_created.register(sub_handler)
        result = await dp.feed_update(bot, update)

        assert result == "dp"
        assert call_order == ["dp"]
