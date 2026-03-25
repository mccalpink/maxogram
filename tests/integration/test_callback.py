"""Интеграционные тесты: callback flow.

Inline keyboard + callback: handler отправляет сообщение с клавиатурой,
пользователь нажимает кнопку -> MessageCallbackUpdate -> callback handler.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from maxogram.client.bot import Bot
from maxogram.dispatcher.dispatcher import Dispatcher
from maxogram.dispatcher.event.bases import UNHANDLED
from maxogram.dispatcher.middlewares.context import EventChat
from maxogram.dispatcher.router import Router
from maxogram.enums import ChatType
from maxogram.types.callback import Callback
from maxogram.types.message import Message, MessageBody, Recipient
from maxogram.types.update import MessageCallbackUpdate, MessageCreatedUpdate

# NOTE: После изменений в dispatcher хендлеры message_created получают Message,
# а хендлеры message_callback получают Callback (не целый Update).
from maxogram.types.user import User
from maxogram.utils.keyboard import InlineKeyboardBuilder


def _make_bot() -> AsyncMock:
    """Создать мок Bot."""
    bot = AsyncMock(spec=Bot)
    bot.token = "test-token"
    bot._me = None
    bot.send_message = AsyncMock(return_value=MagicMock())
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


def _make_callback_update(
    *,
    payload: str = "action",
    user_id: int = 1,
    chat_id: int = 100,
    callback_id: str = "cb1",
) -> MessageCallbackUpdate:
    """Создать MessageCallbackUpdate для тестов."""
    user = User(user_id=user_id, name="Test", is_bot=False, last_activity_time=0)
    callback = Callback(
        timestamp=0,
        callback_id=callback_id,
        payload=payload,
        user=user,
    )
    recipient = Recipient(chat_id=chat_id, chat_type=ChatType.DIALOG)
    body = MessageBody(mid="mid_cb", seq=1, text="original message")
    msg = Message(sender=user, recipient=recipient, timestamp=0, body=body)
    return MessageCallbackUpdate(timestamp=0, callback=callback, message=msg)


class TestCallbackFlow:
    """Сквозные тесты callback flow."""

    @pytest.mark.asyncio
    async def test_callback_handler_called_with_payload(self) -> None:
        """Callback handler вызывается, payload доступен."""
        dp = Dispatcher()
        bot = _make_bot()
        received_payloads: list[str | None] = []

        async def callback_handler(event: Callback) -> str:
            """Хендлер callback: запоминает payload."""
            received_payloads.append(event.payload)
            return "callback_handled"

        dp.message_callback.register(callback_handler)

        update = _make_callback_update(payload="confirm_order")
        result = await dp.feed_update(bot, update)

        assert result == "callback_handled"
        assert received_payloads == ["confirm_order"]

    @pytest.mark.asyncio
    async def test_message_then_callback_flow(self) -> None:
        """Сквозной flow: отправка сообщения с клавиатурой -> callback."""
        dp = Dispatcher()
        bot = _make_bot()
        flow_steps: list[str] = []

        async def message_handler(event: Message) -> str:
            """Хендлер: строит клавиатуру и 'отправляет' сообщение."""
            builder = InlineKeyboardBuilder()
            builder.button(text="Да", payload="yes")
            builder.button(text="Нет", payload="no")
            builder.adjust(2)
            attachment = builder.as_attachment()
            # Проверяем что клавиатура построена корректно
            assert attachment is not None
            flow_steps.append("message_sent")
            return "keyboard_sent"

        async def callback_handler(event: Callback) -> str:
            """Хендлер callback: обрабатывает нажатие."""
            flow_steps.append(f"callback:{event.payload}")
            return "callback_ok"

        dp.message_created.register(message_handler)
        dp.message_callback.register(callback_handler)

        # Шаг 1: сообщение -> отправка клавиатуры
        msg_update = _make_message_update(text="/menu")
        result = await dp.feed_update(bot, msg_update)
        assert result == "keyboard_sent"

        # Шаг 2: callback -> обработка нажатия
        cb_update = _make_callback_update(payload="yes")
        result = await dp.feed_update(bot, cb_update)
        assert result == "callback_ok"

        assert flow_steps == ["message_sent", "callback:yes"]

    @pytest.mark.asyncio
    async def test_callback_context_middleware_extracts_user_and_chat(self) -> None:
        """MaxContextMiddleware извлекает user и chat из MessageCallbackUpdate."""
        dp = Dispatcher()
        bot = _make_bot()
        received: dict[str, Any] = {}

        async def callback_handler(
            event: Callback,
            event_from_user: User | None = None,
            event_chat: EventChat | None = None,
        ) -> str:
            """Хендлер callback: проверяет контекст."""
            received["user"] = event_from_user
            received["chat"] = event_chat
            return "ok"

        dp.message_callback.register(callback_handler)

        update = _make_callback_update(user_id=42, chat_id=777)
        await dp.feed_update(bot, update)

        assert received["user"] is not None
        assert received["user"].user_id == 42
        assert received["chat"] is not None
        assert received["chat"].chat_id == 777

    @pytest.mark.asyncio
    async def test_callback_in_sub_router(self) -> None:
        """Callback handler в sub_router обрабатывает событие."""
        dp = Dispatcher()
        sub = Router(name="callbacks")
        dp.include_router(sub)
        bot = _make_bot()

        async def callback_handler(event: Callback) -> str:
            """Хендлер callback в sub_router."""
            return f"sub:{event.payload}"

        sub.message_callback.register(callback_handler)

        update = _make_callback_update(payload="sub_action")
        result = await dp.feed_update(bot, update)

        assert result == "sub:sub_action"

    @pytest.mark.asyncio
    async def test_no_callback_handler_returns_unhandled(self) -> None:
        """Без callback handler -> UNHANDLED."""
        dp = Dispatcher()
        bot = _make_bot()

        # Есть message handler, но нет callback handler
        async def message_handler(event: Message) -> str:
            """Хендлер сообщений."""
            return "msg"

        dp.message_created.register(message_handler)

        update = _make_callback_update()
        result = await dp.feed_update(bot, update)

        assert result is UNHANDLED
