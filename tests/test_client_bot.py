"""Тесты Bot — фасад над Session для Max Bot API."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from maxogram.client.bot import Bot
from maxogram.client.session.aiohttp import AiohttpSession
from maxogram.client.session.base import BaseSession
from maxogram.enums import SenderAction, UploadType
from maxogram.methods.base import MaxMethod
from maxogram.methods.callback import AnswerOnCallback
from maxogram.methods.chat import GetChat, SendAction
from maxogram.methods.member import AddMembers
from maxogram.methods.message import (
    DeleteMessage,
    EditMessage,
    GetMessages,
    SendMessage,
)
from maxogram.methods.pin import PinMessage
from maxogram.methods.subscription import Subscribe
from maxogram.methods.update import GetUpdates
from maxogram.methods.upload import GetUploadUrl
from maxogram.types.base import MaxObject
from maxogram.types.user import BotInfo

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


# ---------------------------------------------------------------------------
# MockSession
# ---------------------------------------------------------------------------


class MockSession(BaseSession):
    """Мок-сессия для тестирования Bot."""

    def __init__(self) -> None:
        super().__init__()
        self.last_method: MaxMethod[Any] | None = None
        self.call_count: int = 0
        self._closed: bool = False
        self._responses: dict[type, dict[str, Any]] = {}

    def set_response(self, method_type: type, data: dict[str, Any]) -> None:
        """Задать ответ для конкретного типа метода."""
        self._responses[method_type] = data

    async def make_request(
        self,
        bot: Any,
        method: MaxMethod[Any],
        timeout: float | None = None,
    ) -> Any:
        """Запомнить вызов, вернуть ответ через check_response."""
        self.last_method = method
        self.call_count += 1
        response_data = self._responses.get(type(method), {"success": True})
        return self.check_response(method, 200, json.dumps(response_data))

    async def stream_content(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        chunk_size: int = 65536,
    ) -> AsyncGenerator[bytes, None]:
        """Пустой поток."""
        yield b""

    async def close(self) -> None:
        """Пометить сессию закрытой."""
        self._closed = True


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------

BOT_INFO_DATA: dict[str, Any] = {
    "user_id": 123,
    "name": "TestBot",
    "is_bot": True,
    "last_activity_time": 1700000000,
}

SIMPLE_OK: dict[str, Any] = {"success": True}

SEND_MESSAGE_DATA: dict[str, Any] = {
    "message": {
        "sender": {
            "user_id": 123,
            "name": "TestBot",
            "is_bot": True,
            "last_activity_time": 1700000000,
        },
        "recipient": {"chat_id": 1, "chat_type": "chat"},
        "timestamp": 1700000000,
        "body": {"mid": "mid.001", "seq": 1, "text": "hello"},
    },
}

MESSAGE_DATA: dict[str, Any] = {
    "sender": {
        "user_id": 123,
        "name": "TestBot",
        "is_bot": True,
        "last_activity_time": 1700000000,
    },
    "recipient": {"chat_id": 1, "chat_type": "chat"},
    "timestamp": 1700000000,
    "body": {"mid": "mid.002", "seq": 2, "text": "test"},
}

MESSAGE_LIST_DATA: dict[str, Any] = {
    "messages": [MESSAGE_DATA],
}

UPLOAD_ENDPOINT_DATA: dict[str, Any] = {
    "url": "https://upload.example.com/file",
}

GET_UPDATES_DATA: dict[str, Any] = {
    "updates": [],
    "marker": None,
}


@pytest.fixture
def session() -> MockSession:
    """MockSession с дефолтными ответами."""
    s = MockSession()
    s.set_response(type(None), SIMPLE_OK)  # fallback
    return s


@pytest.fixture
def bot(session: MockSession) -> Bot:
    """Bot с MockSession."""
    return Bot(token="test-token-123", session=session)


# ---------------------------------------------------------------------------
# Тесты инициализации
# ---------------------------------------------------------------------------


class TestBotInit:
    """Тесты __init__."""

    def test_token_stored(self, bot: Bot) -> None:
        """Token сохраняется как атрибут."""
        assert bot.token == "test-token-123"

    def test_session_assigned(self, bot: Bot, session: MockSession) -> None:
        """Переданная session назначается."""
        assert bot.session is session

    async def test_default_session_is_aiohttp(self) -> None:
        """Без session — создаётся AiohttpSession."""
        bot = Bot(token="tok")
        try:
            assert isinstance(bot.session, AiohttpSession)
        finally:
            await bot.close()


# ---------------------------------------------------------------------------
# Тесты __call__
# ---------------------------------------------------------------------------


class TestBotCall:
    """Тесты __call__ — вызов метода через session."""

    async def test_call_invokes_session(self, bot: Bot, session: MockSession) -> None:
        """__call__ вызывает session, результат — correct type."""
        from maxogram.methods.bot import GetMyInfo

        session.set_response(GetMyInfo, BOT_INFO_DATA)
        result = await bot(GetMyInfo())

        assert isinstance(result, BotInfo)
        assert result.user_id == 123
        assert result.name == "TestBot"
        assert session.call_count == 1

    async def test_set_bot_propagation(self, bot: Bot, session: MockSession) -> None:
        """Результат MaxObject получает _bot == bot."""
        from maxogram.methods.bot import GetMyInfo

        session.set_response(GetMyInfo, BOT_INFO_DATA)
        result = await bot(GetMyInfo())

        assert isinstance(result, MaxObject)
        assert result._bot is bot


# ---------------------------------------------------------------------------
# Тест me() — кэширование
# ---------------------------------------------------------------------------


class TestBotMe:
    """Тест me() — кэширование."""

    async def test_me_cached(self, bot: Bot, session: MockSession) -> None:
        """2 вызова me() → 1 вызов session."""
        from maxogram.methods.bot import GetMyInfo

        session.set_response(GetMyInfo, BOT_INFO_DATA)

        result1 = await bot.me()
        result2 = await bot.me()

        assert result1 is result2
        assert session.call_count == 1
        assert result1.user_id == 123


# ---------------------------------------------------------------------------
# Тест context manager
# ---------------------------------------------------------------------------


class TestBotContextManager:
    """Тест async context manager."""

    async def test_context_manager_closes_session(self, session: MockSession) -> None:
        """async with bot → close() вызывается."""
        async with Bot(token="tok", session=session):
            assert not session._closed

        assert session._closed


# ---------------------------------------------------------------------------
# Тесты shortcut-методов
# ---------------------------------------------------------------------------


class TestShortcutSendMessage:
    """send_message — создаёт SendMessage с правильными параметрами."""

    async def test_send_message(self, bot: Bot, session: MockSession) -> None:
        """send_message передаёт все параметры в SendMessage."""
        session.set_response(SendMessage, SEND_MESSAGE_DATA)

        await bot.send_message(
            chat_id=42,
            text="hello world",
            notify=False,
            disable_link_preview=True,
        )

        method = session.last_method
        assert isinstance(method, SendMessage)
        assert method.chat_id == 42
        assert method.text == "hello world"
        assert method.notify is False
        assert method.disable_link_preview is True
        assert method.user_id is None
        assert method.attachments is None
        assert method.link is None
        assert method.format is None


class TestShortcutGetChat:
    """get_chat — создаёт GetChat с chat_id."""

    async def test_get_chat(self, bot: Bot, session: MockSession) -> None:
        """get_chat передаёт chat_id."""
        session.set_response(
            GetChat,
            {
                "chat_id": 10,
                "type": "chat",
                "status": "active",
                "last_event_time": 1700000000,
                "participants_count": 5,
                "is_public": False,
            },
        )

        await bot.get_chat(chat_id=10)

        method = session.last_method
        assert isinstance(method, GetChat)
        assert method.chat_id == 10


class TestShortcutEditMessage:
    """edit_message — создаёт EditMessage с message_id."""

    async def test_edit_message(self, bot: Bot, session: MockSession) -> None:
        """edit_message передаёт message_id и text."""
        await bot.edit_message(message_id="mid.123", text="updated")

        method = session.last_method
        assert isinstance(method, EditMessage)
        assert method.message_id == "mid.123"
        assert method.text == "updated"


class TestShortcutDeleteMessage:
    """delete_message — создаёт DeleteMessage."""

    async def test_delete_message(self, bot: Bot, session: MockSession) -> None:
        """delete_message передаёт message_id."""
        await bot.delete_message(message_id="mid.456")

        method = session.last_method
        assert isinstance(method, DeleteMessage)
        assert method.message_id == "mid.456"


class TestShortcutAnswerOnCallback:
    """answer_on_callback — создаёт AnswerOnCallback с callback_id."""

    async def test_answer_on_callback(self, bot: Bot, session: MockSession) -> None:
        """answer_on_callback передаёт callback_id и notification."""
        await bot.answer_on_callback(
            callback_id="cb-001",
            notification="Done!",
        )

        method = session.last_method
        assert isinstance(method, AnswerOnCallback)
        assert method.callback_id == "cb-001"
        assert method.notification == "Done!"
        assert method.message is None


class TestShortcutGetUpdates:
    """get_updates — создаёт GetUpdates с параметрами."""

    async def test_get_updates(self, bot: Bot, session: MockSession) -> None:
        """get_updates передаёт limit, timeout, marker, types."""
        session.set_response(GetUpdates, GET_UPDATES_DATA)

        await bot.get_updates(
            limit=50,
            timeout=30,
            marker=100,
            types=["message_created", "message_callback"],
        )

        method = session.last_method
        assert isinstance(method, GetUpdates)
        assert method.limit == 50
        assert method.timeout == 30
        assert method.marker == 100
        assert method.types == ["message_created", "message_callback"]


class TestShortcutGetMessages:
    """get_messages — edge case: from_ alias."""

    async def test_get_messages_with_from(self, bot: Bot, session: MockSession) -> None:
        """get_messages передаёт from_ (alias 'from')."""
        session.set_response(GetMessages, MESSAGE_LIST_DATA)

        await bot.get_messages(
            chat_id=42,
            from_=1000,
            to=2000,
            count=10,
        )

        method = session.last_method
        assert isinstance(method, GetMessages)
        assert method.chat_id == 42
        assert method.from_ == 1000
        assert method.to == 2000
        assert method.count == 10


class TestShortcutGetUploadUrl:
    """get_upload_url — edge case: type_ alias."""

    async def test_get_upload_url(self, bot: Bot, session: MockSession) -> None:
        """get_upload_url передаёт type_ (alias 'type')."""
        session.set_response(GetUploadUrl, UPLOAD_ENDPOINT_DATA)

        await bot.get_upload_url(type_=UploadType.IMAGE)

        method = session.last_method
        assert isinstance(method, GetUploadUrl)
        assert method.type_ == UploadType.IMAGE


class TestShortcutSubscribe:
    """subscribe — url и update_types."""

    async def test_subscribe(self, bot: Bot, session: MockSession) -> None:
        """subscribe передаёт url, update_types, version."""
        await bot.subscribe(
            url="https://example.com/webhook",
            update_types=["message_created"],
            version="0.3.0",
        )

        method = session.last_method
        assert isinstance(method, Subscribe)
        assert method.url == "https://example.com/webhook"
        assert method.update_types == ["message_created"]
        assert method.version == "0.3.0"


class TestShortcutPinMessage:
    """pin_message — chat_id и message_id."""

    async def test_pin_message(self, bot: Bot, session: MockSession) -> None:
        """pin_message передаёт chat_id, message_id, notify."""
        await bot.pin_message(chat_id=42, message_id="mid.789", notify=False)

        method = session.last_method
        assert isinstance(method, PinMessage)
        assert method.chat_id == 42
        assert method.message_id == "mid.789"
        assert method.notify is False


class TestShortcutAddMembers:
    """add_members — user_ids."""

    async def test_add_members(self, bot: Bot, session: MockSession) -> None:
        """add_members передаёт chat_id и user_ids."""
        await bot.add_members(chat_id=42, user_ids=[1, 2, 3])

        method = session.last_method
        assert isinstance(method, AddMembers)
        assert method.chat_id == 42
        assert method.user_ids == [1, 2, 3]


class TestShortcutSendAction:
    """send_action — action enum."""

    async def test_send_action(self, bot: Bot, session: MockSession) -> None:
        """send_action передаёт chat_id и action."""
        await bot.send_action(chat_id=42, action=SenderAction.TYPING_ON)

        method = session.last_method
        assert isinstance(method, SendAction)
        assert method.chat_id == 42
        assert method.action == SenderAction.TYPING_ON
