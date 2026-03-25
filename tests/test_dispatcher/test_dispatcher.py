"""Тесты Dispatcher — центральный координатор фреймворка."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from maxogram.client.bot import Bot
from maxogram.dispatcher.dispatcher import Dispatcher
from maxogram.dispatcher.event.bases import UNHANDLED
from maxogram.dispatcher.event.max import MaxEventObserver
from maxogram.dispatcher.middlewares.context import MaxContextMiddleware
from maxogram.dispatcher.middlewares.error import ErrorEvent, ErrorsMiddleware
from maxogram.dispatcher.router import Router
from maxogram.enums import ChatType
from maxogram.types.message import Message, MessageBody, Recipient
from maxogram.types.update import MessageCreatedUpdate
from maxogram.types.user import User


def _make_bot() -> AsyncMock:
    """Создать мок Bot."""
    bot = AsyncMock(spec=Bot)
    bot.token = "test-token"
    return bot


def _make_message_update(
    *,
    user_id: int = 1,
    chat_id: int = 100,
    text: str = "hello",
) -> MessageCreatedUpdate:
    """Создать MessageCreatedUpdate для тестов."""
    user = User(user_id=user_id, name="Test", is_bot=False, last_activity_time=0)
    recipient = Recipient(chat_id=chat_id, chat_type=ChatType.DIALOG)
    body = MessageBody(mid="mid1", seq=1, text=text)
    msg = Message(sender=user, recipient=recipient, timestamp=0, body=body)
    return MessageCreatedUpdate(timestamp=0, message=msg)


class TestDispatcherInit:
    """Тесты инициализации Dispatcher."""

    def test_inherits_router(self) -> None:
        dp = Dispatcher()
        assert isinstance(dp, Router)

    def test_workflow_data_from_kwargs(self) -> None:
        dp = Dispatcher(db="postgres", redis="redis://localhost")
        assert dp.workflow_data == {"db": "postgres", "redis": "redis://localhost"}

    def test_workflow_data_empty_by_default(self) -> None:
        dp = Dispatcher()
        assert dp.workflow_data == {}

    def test_has_update_observer(self) -> None:
        dp = Dispatcher()
        assert isinstance(dp.update, MaxEventObserver)
        assert "update" in dp.observers
        assert dp.observers["update"] is dp.update

    def test_update_observer_has_listen_update_handler(self) -> None:
        dp = Dispatcher()
        assert len(dp.update.handlers) == 1

    def test_custom_name(self) -> None:
        dp = Dispatcher(name="my_dp")
        assert dp.name == "my_dp"

    def test_parent_router_setter_raises(self) -> None:
        dp = Dispatcher()
        parent = Router(name="parent")
        with pytest.raises(RuntimeError, match="cannot be attached"):
            dp.parent_router = parent

    def test_parent_router_getter_returns_none(self) -> None:
        dp = Dispatcher()
        assert dp.parent_router is None


class TestDispatcherBuiltinMiddleware:
    """Тесты встроенных outer middleware."""

    def test_errors_middleware_registered_first(self) -> None:
        dp = Dispatcher()
        assert len(dp.update.outer_middleware) >= 2
        assert isinstance(dp.update.outer_middleware[0], ErrorsMiddleware)

    def test_context_middleware_registered_second(self) -> None:
        dp = Dispatcher()
        assert isinstance(dp.update.outer_middleware[1], MaxContextMiddleware)

    def test_errors_middleware_references_dispatcher(self) -> None:
        dp = Dispatcher()
        errors_mw = dp.update.outer_middleware[0]
        assert isinstance(errors_mw, ErrorsMiddleware)
        assert errors_mw.router is dp


class TestDispatcherWorkflowData:
    """Тесты dict-like доступа к workflow_data."""

    def test_getitem(self) -> None:
        dp = Dispatcher(key="value")
        assert dp["key"] == "value"

    def test_setitem(self) -> None:
        dp = Dispatcher()
        dp["key"] = "value"
        assert dp.workflow_data["key"] == "value"

    def test_delitem(self) -> None:
        dp = Dispatcher(key="value")
        del dp["key"]
        assert "key" not in dp.workflow_data

    def test_contains(self) -> None:
        dp = Dispatcher(key="value")
        assert "key" in dp
        assert "missing" not in dp

    def test_get_existing(self) -> None:
        dp = Dispatcher(key="value")
        assert dp.get("key") == "value"

    def test_get_missing_default(self) -> None:
        dp = Dispatcher()
        assert dp.get("missing") is None
        assert dp.get("missing", 42) == 42

    def test_getitem_missing_raises(self) -> None:
        dp = Dispatcher()
        with pytest.raises(KeyError):
            _ = dp["missing"]

    def test_delitem_missing_raises(self) -> None:
        dp = Dispatcher()
        with pytest.raises(KeyError):
            del dp["missing"]


class TestFeedUpdate:
    """Тесты feed_update — главная точка входа."""

    @pytest.mark.asyncio
    async def test_handler_called_via_feed_update(self) -> None:
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update()
        results: list[str] = []

        async def handler(event: Any) -> str:
            results.append("handled")
            return "ok"

        dp.message_created.register(handler)
        result = await dp.feed_update(bot, update)
        assert result == "ok"
        assert results == ["handled"]

    @pytest.mark.asyncio
    async def test_data_contains_bot_and_event_update(self) -> None:
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update()
        received: dict[str, Any] = {}

        async def handler(event: Any, bot: Any = None, event_update: Any = None) -> str:
            received["bot"] = bot
            received["event_update"] = event_update
            return "ok"

        dp.message_created.register(handler)
        await dp.feed_update(bot, update)
        assert received["bot"] is bot
        assert received["event_update"] is update

    @pytest.mark.asyncio
    async def test_data_contains_workflow_data(self) -> None:
        dp = Dispatcher(db="postgres")
        bot = _make_bot()
        update = _make_message_update()
        received: dict[str, Any] = {}

        async def handler(event: Any, db: Any = None) -> str:
            received["db"] = db
            return "ok"

        dp.message_created.register(handler)
        await dp.feed_update(bot, update)
        assert received["db"] == "postgres"

    @pytest.mark.asyncio
    async def test_extra_kwargs_in_feed_update(self) -> None:
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update()
        received: dict[str, Any] = {}

        async def handler(event: Any, custom: Any = None) -> str:
            received["custom"] = custom
            return "ok"

        dp.message_created.register(handler)
        await dp.feed_update(bot, update, custom="extra")
        assert received["custom"] == "extra"

    @pytest.mark.asyncio
    async def test_unknown_update_type_returns_unhandled(self) -> None:
        dp = Dispatcher()
        bot = _make_bot()

        class FakeUpdate:
            update_type = "nonexistent_type"

        result = await dp.feed_update(bot, FakeUpdate())
        assert result is UNHANDLED

    @pytest.mark.asyncio
    async def test_no_handlers_returns_unhandled(self) -> None:
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update()
        result = await dp.feed_update(bot, update)
        assert result is UNHANDLED


class TestListenUpdate:
    """Тесты _listen_update — маршрутизация по update_type."""

    @pytest.mark.asyncio
    async def test_update_without_update_type_returns_unhandled(self) -> None:
        dp = Dispatcher()
        bot = _make_bot()

        class NoType:
            pass

        result = await dp.feed_update(bot, NoType())
        assert result is UNHANDLED

    @pytest.mark.asyncio
    async def test_routes_to_correct_observer(self) -> None:
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update()
        called_in: list[str] = []

        async def msg_handler(event: Any) -> str:
            called_in.append("message_created")
            return "msg"

        async def bot_handler(event: Any) -> str:
            called_in.append("bot_started")
            return "bot"

        dp.message_created.register(msg_handler)
        dp.bot_started.register(bot_handler)

        await dp.feed_update(bot, update)
        assert called_in == ["message_created"]


class TestFeedUpdateWithContextMiddleware:
    """Тесты MaxContextMiddleware через feed_update."""

    @pytest.mark.asyncio
    async def test_event_from_user_set(self) -> None:
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update(user_id=42)
        received: dict[str, Any] = {}

        async def handler(event: Any, event_from_user: Any = None) -> str:
            received["event_from_user"] = event_from_user
            return "ok"

        dp.message_created.register(handler)
        await dp.feed_update(bot, update)
        assert received["event_from_user"] is not None
        assert received["event_from_user"].user_id == 42

    @pytest.mark.asyncio
    async def test_event_chat_set(self) -> None:
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update(chat_id=777)
        received: dict[str, Any] = {}

        async def handler(event: Any, event_chat: Any = None) -> str:
            received["event_chat"] = event_chat
            return "ok"

        dp.message_created.register(handler)
        await dp.feed_update(bot, update)
        assert received["event_chat"] is not None
        assert received["event_chat"].chat_id == 777


class TestFeedUpdateWithErrorsMiddleware:
    """Тесты ErrorsMiddleware через feed_update."""

    @pytest.mark.asyncio
    async def test_error_handler_called_on_exception(self) -> None:
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update()
        error_received: list[Any] = []

        async def bad_handler(event: Any) -> None:
            msg = "boom"
            raise ValueError(msg)

        async def error_handler(event: Any) -> str:
            error_received.append(event)
            return "error_handled"

        dp.message_created.register(bad_handler)
        dp.error.register(error_handler)

        result = await dp.feed_update(bot, update)
        assert result == "error_handled"
        assert len(error_received) == 1
        assert isinstance(error_received[0], ErrorEvent)
        assert isinstance(error_received[0].exception, ValueError)

    @pytest.mark.asyncio
    async def test_error_reraises_if_no_error_handler(self) -> None:
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update()

        async def bad_handler(event: Any) -> None:
            msg = "unhandled boom"
            raise ValueError(msg)

        dp.message_created.register(bad_handler)

        with pytest.raises(ValueError, match="unhandled boom"):
            await dp.feed_update(bot, update)


class TestStop:
    """Тесты метода stop()."""

    def test_stop_without_start_is_noop(self) -> None:
        dp = Dispatcher()
        # _stop_signal is None, stop() should not raise
        dp.stop()

    @pytest.mark.asyncio
    async def test_stop_delegates_to_polling(self) -> None:
        from unittest.mock import MagicMock

        from maxogram.polling.polling import Polling

        dp = Dispatcher()
        mock_polling = MagicMock(spec=Polling)
        dp._pollings = [mock_polling]
        dp.stop()
        mock_polling.stop.assert_called_once()


class TestDispatcherWithSubRouters:
    """Тесты Dispatcher с дочерними роутерами."""

    @pytest.mark.asyncio
    async def test_sub_router_handler_via_feed_update(self) -> None:
        dp = Dispatcher()
        child = Router(name="child")
        dp.include_router(child)
        bot = _make_bot()
        update = _make_message_update()

        async def handler(event: Any) -> str:
            return "child_handled"

        child.message_created.register(handler)
        result = await dp.feed_update(bot, update)
        assert result == "child_handled"

    @pytest.mark.asyncio
    async def test_dispatcher_handler_before_sub_router(self) -> None:
        dp = Dispatcher()
        child = Router(name="child")
        dp.include_router(child)
        bot = _make_bot()
        update = _make_message_update()

        async def dp_handler(event: Any) -> str:
            return "dp"

        async def child_handler(event: Any) -> str:
            return "child"

        dp.message_created.register(dp_handler)
        child.message_created.register(child_handler)
        result = await dp.feed_update(bot, update)
        assert result == "dp"

    def test_cannot_attach_dispatcher_to_router(self) -> None:
        dp = Dispatcher()
        parent = Router(name="parent")
        with pytest.raises(RuntimeError, match="cannot be attached"):
            parent.include_router(dp)


class TestOuterMiddlewareOnEventObserverViaFeedUpdate:
    """Тесты outer_middleware на event observers через полный pipeline feed_update."""

    @pytest.mark.asyncio
    async def test_update_outer_middleware_still_works(self) -> None:
        """outer_middleware на update observer продолжает работать (регрессия)."""
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update()
        custom_mw_called = False

        async def custom_outer_mw(handler: Any, event: Any, data: dict[str, Any]) -> Any:
            nonlocal custom_mw_called
            custom_mw_called = True
            return await handler(event, data)

        async def handler(event: Any) -> str:
            return "ok"

        dp.update.outer_middleware.register(custom_outer_mw)
        dp.message_created.register(handler)

        result = await dp.feed_update(bot, update)
        assert result == "ok"
        assert custom_mw_called is True

    @pytest.mark.asyncio
    async def test_event_outer_middleware_called_via_feed_update(self) -> None:
        """outer_middleware на message_created вызывается через feed_update."""
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update()
        event_mw_called = False

        async def event_outer_mw(handler: Any, event: Any, data: dict[str, Any]) -> Any:
            nonlocal event_mw_called
            event_mw_called = True
            return await handler(event, data)

        async def handler(event: Any) -> str:
            return "ok"

        dp.message_created.outer_middleware.register(event_outer_mw)
        dp.message_created.register(handler)

        result = await dp.feed_update(bot, update)
        assert result == "ok"
        assert event_mw_called is True

    @pytest.mark.asyncio
    async def test_full_middleware_order_via_feed_update(self) -> None:
        """Полный порядок: update outer → event outer → event inner → handler."""
        dp = Dispatcher()
        bot = _make_bot()
        update = _make_message_update()
        order: list[str] = []

        async def update_outer_mw(handler: Any, event: Any, data: dict[str, Any]) -> Any:
            order.append("update_outer")
            return await handler(event, data)

        async def event_outer_mw(handler: Any, event: Any, data: dict[str, Any]) -> Any:
            order.append("event_outer")
            return await handler(event, data)

        async def event_inner_mw(handler: Any, event: Any, data: dict[str, Any]) -> Any:
            order.append("event_inner")
            return await handler(event, data)

        async def handler(event: Any) -> str:
            order.append("handler")
            return "ok"

        dp.update.outer_middleware.register(update_outer_mw)
        dp.message_created.outer_middleware.register(event_outer_mw)
        dp.message_created.middleware.register(event_inner_mw)
        dp.message_created.register(handler)

        await dp.feed_update(bot, update)
        assert order == [
            "update_outer",
            "event_outer",
            "event_inner",
            "handler",
        ]
