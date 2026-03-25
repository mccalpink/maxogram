"""Тесты BaseHandler, MessageHandler, CallbackHandler."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from maxogram.dispatcher.event.handler import CallableObject, HandlerObject
from maxogram.handlers.base import BaseHandler, CallbackHandler, MessageHandler
from maxogram.types.callback import Callback
from maxogram.types.message import Message

# -- Фикстуры --


@pytest.fixture
def mock_message() -> Message:
    """Минимальный mock Message."""
    msg = MagicMock(spec=Message)
    msg.chat_id = 123
    msg.sender = MagicMock()
    msg.sender.user_id = 456
    return msg


@pytest.fixture
def mock_callback() -> Callback:
    """Минимальный mock Callback."""
    cb = MagicMock(spec=Callback)
    cb.callback_id = "cb_123"
    cb.payload = "test_payload"
    return cb


@pytest.fixture
def mock_bot() -> MagicMock:
    """Mock бота."""
    return MagicMock()


# -- Тесты BaseHandler --


class TestBaseHandler:
    """Тесты для BaseHandler."""

    def test_cannot_instantiate_abstract(self) -> None:
        """BaseHandler нельзя создать без реализации handle()."""
        with pytest.raises(TypeError):
            BaseHandler(event=MagicMock())  # type: ignore[abstract]

    def test_subclass_with_handle(self, mock_message: Message) -> None:
        """Подкласс с handle() создаётся без ошибок."""

        class MyHandler(BaseHandler[Message]):
            async def handle(self) -> Any:
                return "ok"

        handler = MyHandler(event=mock_message, bot=MagicMock())
        assert handler.event is mock_message

    def test_event_stored(self, mock_message: Message) -> None:
        """event сохраняется в self.event."""

        class MyHandler(BaseHandler[Message]):
            async def handle(self) -> Any:
                return self.event

        handler = MyHandler(event=mock_message)
        assert handler.event is mock_message

    def test_data_stored(self, mock_message: Message, mock_bot: MagicMock) -> None:
        """kwargs сохраняются в self.data."""

        class MyHandler(BaseHandler[Message]):
            async def handle(self) -> Any:
                return self.data

        handler = MyHandler(event=mock_message, bot=mock_bot, custom="value")
        assert handler.data["bot"] is mock_bot
        assert handler.data["custom"] == "value"

    def test_bot_property(self, mock_message: Message, mock_bot: MagicMock) -> None:
        """self.bot — shortcut для data['bot']."""

        class MyHandler(BaseHandler[Message]):
            async def handle(self) -> Any:
                return self.bot

        handler = MyHandler(event=mock_message, bot=mock_bot)
        assert handler.bot is mock_bot

    def test_bot_property_missing_raises(self, mock_message: Message) -> None:
        """self.bot без bot в data — KeyError."""

        class MyHandler(BaseHandler[Message]):
            async def handle(self) -> Any:
                return self.bot

        handler = MyHandler(event=mock_message)
        with pytest.raises(KeyError):
            _ = handler.bot

    @pytest.mark.asyncio
    async def test_handle_called(self, mock_message: Message) -> None:
        """handle() вызывается корректно."""

        class MyHandler(BaseHandler[Message]):
            async def handle(self) -> str:
                return "handled"

        handler = MyHandler(event=mock_message)
        result = await handler.handle()
        assert result == "handled"

    @pytest.mark.asyncio
    async def test_await_handler(self, mock_message: Message) -> None:
        """await MyHandler(event, **kwargs) вызывает handle()."""

        class MyHandler(BaseHandler[Message]):
            async def handle(self) -> str:
                return "awaited"

        result = await MyHandler(event=mock_message)
        assert result == "awaited"

    @pytest.mark.asyncio
    async def test_di_integration_with_callable_object(
        self, mock_message: Message, mock_bot: MagicMock
    ) -> None:
        """BaseHandler работает с CallableObject DI — event как первый позиционный аргумент."""

        class MyHandler(BaseHandler[Message]):
            async def handle(self) -> str:
                return f"handled-{self.data.get('custom')}"

        # CallableObject должен корректно вызвать класс
        obj = CallableObject(callback=MyHandler)
        result = await obj.call(mock_message, bot=mock_bot, custom="test")
        assert result == "handled-test"

    @pytest.mark.asyncio
    async def test_handler_object_with_class_based(
        self, mock_message: Message, mock_bot: MagicMock
    ) -> None:
        """HandlerObject с class-based handler — фильтры + вызов."""

        class MyHandler(BaseHandler[Message]):
            async def handle(self) -> str:
                return "from_class"

        handler_obj = HandlerObject(callback=MyHandler)
        check, kwargs = await handler_obj.check(mock_message, bot=mock_bot)
        assert check is True
        result = await handler_obj.call(mock_message, bot=mock_bot)
        assert result == "from_class"

    @pytest.mark.asyncio
    async def test_handler_accesses_data_kwargs(
        self, mock_message: Message, mock_bot: MagicMock
    ) -> None:
        """Хендлер получает доступ ко всем kwargs через self.data."""

        class MyHandler(BaseHandler[Message]):
            async def handle(self) -> dict[str, Any]:
                return {
                    "bot": self.bot,
                    "state": self.data.get("state"),
                    "event_chat": self.data.get("event_chat"),
                }

        handler = MyHandler(
            event=mock_message, bot=mock_bot, state="some_state", event_chat="chat_obj"
        )
        result = await handler.handle()
        assert result["bot"] is mock_bot
        assert result["state"] == "some_state"
        assert result["event_chat"] == "chat_obj"


# -- Тесты MessageHandler --


class TestMessageHandler:
    """Тесты для MessageHandler (BaseHandler[Message])."""

    def test_event_type_is_message(self, mock_message: Message) -> None:
        """MessageHandler типизирован под Message."""

        class MyMsgHandler(MessageHandler):
            async def handle(self) -> Any:
                return self.event

        handler = MyMsgHandler(event=mock_message)
        assert handler.event is mock_message

    @pytest.mark.asyncio
    async def test_handle(self, mock_message: Message) -> None:
        """MessageHandler handle() вызывается корректно."""

        class MyMsgHandler(MessageHandler):
            async def handle(self) -> str:
                return "msg_handled"

        result = await MyMsgHandler(event=mock_message)
        assert result == "msg_handled"

    @pytest.mark.asyncio
    async def test_callable_object_integration(
        self, mock_message: Message, mock_bot: MagicMock
    ) -> None:
        """MessageHandler совместим с CallableObject."""

        class MyMsgHandler(MessageHandler):
            async def handle(self) -> str:
                return f"msg-{self.bot}"

        obj = CallableObject(callback=MyMsgHandler)
        result = await obj.call(mock_message, bot=mock_bot)
        assert result.startswith("msg-")


# -- Тесты CallbackHandler --


class TestCallbackHandler:
    """Тесты для CallbackHandler (BaseHandler[Callback])."""

    def test_event_type_is_callback(self, mock_callback: Callback) -> None:
        """CallbackHandler типизирован под Callback."""

        class MyCbHandler(CallbackHandler):
            async def handle(self) -> Any:
                return self.event

        handler = MyCbHandler(event=mock_callback)
        assert handler.event is mock_callback

    @pytest.mark.asyncio
    async def test_handle(self, mock_callback: Callback) -> None:
        """CallbackHandler handle() вызывается корректно."""

        class MyCbHandler(CallbackHandler):
            async def handle(self) -> str:
                return "cb_handled"

        result = await MyCbHandler(event=mock_callback)
        assert result == "cb_handled"

    @pytest.mark.asyncio
    async def test_callable_object_integration(
        self, mock_callback: Callback, mock_bot: MagicMock
    ) -> None:
        """CallbackHandler совместим с CallableObject."""

        class MyCbHandler(CallbackHandler):
            async def handle(self) -> str:
                return f"cb-{self.data.get('custom')}"

        obj = CallableObject(callback=MyCbHandler)
        result = await obj.call(mock_callback, bot=mock_bot, custom="val")
        assert result == "cb-val"


# -- Тесты интеграции с observer register --


class TestHandlerRegistration:
    """Тесты регистрации class-based handlers через observer."""

    @pytest.mark.asyncio
    async def test_register_class_handler_on_observer(
        self, mock_message: Message, mock_bot: MagicMock
    ) -> None:
        """Class-based handler регистрируется и вызывается через MaxEventObserver."""
        from maxogram.dispatcher.event.max import MaxEventObserver

        class MyHandler(MessageHandler):
            async def handle(self) -> str:
                return "observer_result"

        observer = MaxEventObserver(event_name="message_created")
        observer.register(MyHandler)

        result = await observer.trigger(mock_message, bot=mock_bot)
        assert result == "observer_result"

    @pytest.mark.asyncio
    async def test_class_handler_with_filters(
        self, mock_message: Message, mock_bot: MagicMock
    ) -> None:
        """Class-based handler с фильтрами."""
        from maxogram.dispatcher.event.max import MaxEventObserver

        async def always_true(event: Any) -> bool:
            return True

        class MyHandler(MessageHandler):
            async def handle(self) -> str:
                return "filtered_result"

        observer = MaxEventObserver(event_name="message_created")
        observer.register(MyHandler, always_true)

        result = await observer.trigger(mock_message, bot=mock_bot)
        assert result == "filtered_result"

    @pytest.mark.asyncio
    async def test_class_handler_with_flags(
        self, mock_message: Message, mock_bot: MagicMock
    ) -> None:
        """Class-based handler с flags."""
        from maxogram.dispatcher.event.max import MaxEventObserver

        class MyHandler(MessageHandler):
            async def handle(self) -> dict[str, Any]:
                handler_obj = self.data.get("handler")
                return {"flags": handler_obj.flags if handler_obj else {}}

        observer = MaxEventObserver(event_name="message_created")
        observer.register(MyHandler, flags={"rate_limit": "strict"})

        result = await observer.trigger(mock_message, bot=mock_bot)
        assert result["flags"]["rate_limit"] == "strict"
