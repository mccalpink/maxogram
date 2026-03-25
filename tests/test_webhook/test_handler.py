"""Тесты WebhookHandler — aiohttp web handler для приёма webhook-уведомлений."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from maxogram.client.bot import Bot
from maxogram.types.update import (
    BotStartedUpdate,
    MessageCallbackUpdate,
    MessageCreatedUpdate,
)


def _make_bot() -> AsyncMock:
    """Создать мок Bot."""
    bot = AsyncMock(spec=Bot)
    bot.token = "test-token"
    return bot


def _make_dispatcher() -> MagicMock:
    """Создать мок Dispatcher."""
    from maxogram.dispatcher.dispatcher import Dispatcher

    dp = MagicMock(spec=Dispatcher)
    dp.feed_update = AsyncMock()
    return dp


def _message_created_payload(text: str = "Привет") -> dict[str, Any]:
    """Webhook payload для message_created."""
    return {
        "update_type": "message_created",
        "timestamp": 1711000000000,
        "user_locale": "ru",
        "message": {
            "sender": {
                "user_id": 111,
                "name": "Иван",
                "is_bot": False,
                "last_activity_time": 0,
            },
            "recipient": {"chat_id": 222, "chat_type": "dialog"},
            "timestamp": 1711000000000,
            "body": {"mid": "mid_12345", "seq": 1, "text": text},
        },
    }


def _bot_started_payload() -> dict[str, Any]:
    """Webhook payload для bot_started."""
    return {
        "update_type": "bot_started",
        "timestamp": 1711000000000,
        "user_locale": "ru",
        "chat_id": 222,
        "user": {
            "user_id": 111,
            "name": "Иван",
            "is_bot": False,
            "last_activity_time": 0,
        },
        "payload": "deep_link",
    }


def _callback_payload() -> dict[str, Any]:
    """Webhook payload для message_callback."""
    return {
        "update_type": "message_callback",
        "timestamp": 1711000000000,
        "user_locale": "ru",
        "callback": {
            "timestamp": 1711000000000,
            "callback_id": "cb_123",
            "payload": "btn_action",
            "user": {
                "user_id": 111,
                "name": "Иван",
                "is_bot": False,
                "last_activity_time": 0,
            },
        },
        "message": {
            "sender": {
                "user_id": 999,
                "name": "MyBot",
                "is_bot": True,
                "last_activity_time": 0,
            },
            "recipient": {"chat_id": 222, "chat_type": "dialog"},
            "timestamp": 1711000000000,
            "body": {"mid": "mid_67890", "seq": 2, "text": "Выберите"},
        },
    }


@pytest.fixture
def bot() -> AsyncMock:
    return _make_bot()


@pytest.fixture
def dispatcher() -> MagicMock:
    return _make_dispatcher()


@pytest.fixture
def handler(dispatcher: MagicMock, bot: AsyncMock) -> Any:
    from maxogram.webhook.handler import WebhookHandler

    return WebhookHandler(dispatcher=dispatcher, bot=bot)


@pytest.fixture
def app(handler: Any) -> web.Application:
    """Создать aiohttp Application с webhook handler."""
    application = web.Application()
    handler.register(application, path="/webhook")
    return application


@pytest.fixture
async def client(app: web.Application) -> Any:
    """Создать тестовый клиент aiohttp."""
    server = TestServer(app)
    test_client = TestClient(server)
    await test_client.start_server()
    yield test_client
    await test_client.close()


class TestWebhookHandlerInit:
    """Тесты инициализации WebhookHandler."""

    def test_stores_parameters(self, dispatcher: MagicMock, bot: AsyncMock) -> None:
        from maxogram.webhook.handler import WebhookHandler

        handler = WebhookHandler(dispatcher=dispatcher, bot=bot)

        assert handler._dispatcher is dispatcher
        assert handler._bot is bot

    def test_register_adds_route(self, handler: Any) -> None:
        """register() добавляет POST route в aiohttp Application."""
        app = web.Application()
        handler.register(app, path="/webhook")

        routes = [r.resource.canonical for r in app.router.routes() if hasattr(r, "resource")]
        assert "/webhook" in routes

    def test_register_custom_path(self, handler: Any) -> None:
        """register() поддерживает custom path."""
        app = web.Application()
        handler.register(app, path="/custom/path")

        routes = [r.resource.canonical for r in app.router.routes() if hasattr(r, "resource")]
        assert "/custom/path" in routes


class TestWebhookHandlerPost:
    """Тесты POST handler — приём webhook update."""

    @pytest.mark.asyncio
    async def test_message_created_update(self, client: Any, dispatcher: MagicMock) -> None:
        """Корректный message_created update обрабатывается и возвращает 200."""
        payload = _message_created_payload("Привет")

        resp = await client.post("/webhook", json=payload)

        assert resp.status == 200
        dispatcher.feed_update.assert_awaited_once()

        # Проверяем, что update правильно распарсен
        call_args = dispatcher.feed_update.call_args
        update = call_args[0][1]  # второй позиционный аргумент
        assert isinstance(update, MessageCreatedUpdate)
        assert update.update_type == "message_created"
        assert update.timestamp == 1711000000000
        assert update.user_locale == "ru"
        assert update.message.body.text == "Привет"

    @pytest.mark.asyncio
    async def test_bot_started_update(self, client: Any, dispatcher: MagicMock) -> None:
        """bot_started update корректно парсится."""
        payload = _bot_started_payload()

        resp = await client.post("/webhook", json=payload)

        assert resp.status == 200
        dispatcher.feed_update.assert_awaited_once()

        call_args = dispatcher.feed_update.call_args
        update = call_args[0][1]
        assert isinstance(update, BotStartedUpdate)
        assert update.chat_id == 222
        assert update.payload == "deep_link"
        assert update.user_locale == "ru"

    @pytest.mark.asyncio
    async def test_message_callback_update(self, client: Any, dispatcher: MagicMock) -> None:
        """message_callback update корректно парсится."""
        payload = _callback_payload()

        resp = await client.post("/webhook", json=payload)

        assert resp.status == 200
        dispatcher.feed_update.assert_awaited_once()

        call_args = dispatcher.feed_update.call_args
        update = call_args[0][1]
        assert isinstance(update, MessageCallbackUpdate)
        assert update.callback.callback_id == "cb_123"

    @pytest.mark.asyncio
    async def test_bot_passed_to_feed_update(
        self, client: Any, dispatcher: MagicMock, bot: AsyncMock,
    ) -> None:
        """Bot передаётся первым аргументом в feed_update."""
        payload = _message_created_payload()

        await client.post("/webhook", json=payload)

        call_args = dispatcher.feed_update.call_args
        assert call_args[0][0] is bot

    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self, client: Any, dispatcher: MagicMock) -> None:
        """Невалидный JSON возвращает 400."""
        resp = await client.post(
            "/webhook",
            data=b"not json",
            headers={"Content-Type": "application/json"},
        )

        assert resp.status == 400
        dispatcher.feed_update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_update_type_returns_400(
        self, client: Any, dispatcher: MagicMock,
    ) -> None:
        """Отсутствие update_type возвращает 400."""
        payload = {"timestamp": 1711000000000, "message": {}}

        resp = await client.post("/webhook", json=payload)

        assert resp.status == 400
        dispatcher.feed_update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unknown_update_type_returns_200(
        self, client: Any, dispatcher: MagicMock,
    ) -> None:
        """Неизвестный update_type: возвращаем 200 (не блокируем Max API), но не обрабатываем."""
        payload = {
            "update_type": "future_unknown_event",
            "timestamp": 1711000000000,
        }

        resp = await client.post("/webhook", json=payload)

        # 200 — чтобы Max не считал webhook сломанным
        assert resp.status == 200
        dispatcher.feed_update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_feed_update_error_returns_200(self, client: Any, dispatcher: MagicMock) -> None:
        """Ошибка в feed_update не должна ломать webhook (возвращаем 200)."""
        dispatcher.feed_update.side_effect = ValueError("handler error")
        payload = _message_created_payload()

        resp = await client.post("/webhook", json=payload)

        # 200 — ошибка обработки не должна вызвать повторную отправку от Max
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_empty_body_returns_400(self, client: Any, dispatcher: MagicMock) -> None:
        """Пустое тело запроса возвращает 400."""
        resp = await client.post(
            "/webhook",
            data=b"",
            headers={"Content-Type": "application/json"},
        )

        assert resp.status == 400
        dispatcher.feed_update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_request_returns_405(self, client: Any) -> None:
        """GET запрос на webhook endpoint возвращает 405 Method Not Allowed."""
        resp = await client.get("/webhook")

        assert resp.status == 405

    @pytest.mark.asyncio
    async def test_response_body_ok(self, client: Any) -> None:
        """Тело ответа содержит ok."""
        payload = _message_created_payload()

        resp = await client.post("/webhook", json=payload)

        data = await resp.json()
        assert data == {"ok": True}
