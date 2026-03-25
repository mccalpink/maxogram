"""Тесты для types/update.py — Update discriminated union (13 типов)."""

from __future__ import annotations

from pydantic import TypeAdapter

from maxogram.types.update import (
    BotAddedUpdate,
    BotRemovedUpdate,
    BotStartedUpdate,
    ChatTitleChangedUpdate,
    GetUpdatesResult,
    MessageCallbackUpdate,
    MessageChatCreatedUpdate,
    MessageConstructedUpdate,
    MessageConstructionRequestUpdate,
    MessageCreatedUpdate,
    MessageEditedUpdate,
    MessageRemovedUpdate,
    Update,
    UserAddedUpdate,
    UserRemovedUpdate,
)

update_adapter = TypeAdapter(Update)

USER_DATA = {
    "user_id": 111,
    "name": "Иван",
    "is_bot": False,
    "last_activity_time": 1711000000000,
}

MESSAGE_DATA = {
    "sender": USER_DATA,
    "recipient": {"chat_id": 222, "chat_type": "dialog"},
    "timestamp": 1711000000000,
    "body": {"mid": "mid_12345", "seq": 1, "text": "Привет"},
}


class TestUpdateDiscriminator:
    """Discriminated union по полю update_type."""

    def test_message_created(self) -> None:
        data = {
            "update_type": "message_created",
            "timestamp": 1711000000000,
            "message": MESSAGE_DATA,
        }
        obj = update_adapter.validate_python(data)
        assert isinstance(obj, MessageCreatedUpdate)
        assert obj.message.body.text == "Привет"

    def test_message_callback(self) -> None:
        data = {
            "update_type": "message_callback",
            "timestamp": 1711000000000,
            "callback": {
                "timestamp": 1711000000000,
                "callback_id": "cb_1",
                "payload": "action",
                "user": USER_DATA,
            },
            "message": MESSAGE_DATA,
        }
        obj = update_adapter.validate_python(data)
        assert isinstance(obj, MessageCallbackUpdate)
        assert obj.callback.callback_id == "cb_1"

    def test_message_edited(self) -> None:
        data = {
            "update_type": "message_edited",
            "timestamp": 1711000000000,
            "message": MESSAGE_DATA,
        }
        obj = update_adapter.validate_python(data)
        assert isinstance(obj, MessageEditedUpdate)

    def test_message_removed(self) -> None:
        data = {
            "update_type": "message_removed",
            "timestamp": 1711000000000,
            "message_id": "mid_12345",
        }
        obj = update_adapter.validate_python(data)
        assert isinstance(obj, MessageRemovedUpdate)
        assert obj.message_id == "mid_12345"

    def test_message_chat_created(self) -> None:
        data = {
            "update_type": "message_chat_created",
            "timestamp": 1711000000000,
            "chat": {"chat_id": 333},
            "message_id": "mid_1",
        }
        obj = update_adapter.validate_python(data)
        assert isinstance(obj, MessageChatCreatedUpdate)

    def test_message_construction_request(self) -> None:
        data = {
            "update_type": "message_construction_request",
            "timestamp": 1711000000000,
            "user": USER_DATA,
            "session_id": "sess_1",
        }
        obj = update_adapter.validate_python(data)
        assert isinstance(obj, MessageConstructionRequestUpdate)
        assert obj.session_id == "sess_1"

    def test_message_constructed(self) -> None:
        data = {
            "update_type": "message_constructed",
            "timestamp": 1711000000000,
            "session_id": "sess_1",
        }
        obj = update_adapter.validate_python(data)
        assert isinstance(obj, MessageConstructedUpdate)

    def test_bot_started(self) -> None:
        data = {
            "update_type": "bot_started",
            "timestamp": 1711000000000,
            "chat_id": 222,
            "user": USER_DATA,
            "payload": "deep_link",
        }
        obj = update_adapter.validate_python(data)
        assert isinstance(obj, BotStartedUpdate)
        assert obj.chat_id == 222
        assert obj.payload == "deep_link"

    def test_bot_added(self) -> None:
        data = {
            "update_type": "bot_added",
            "timestamp": 1711000000000,
            "chat_id": 222,
            "user": USER_DATA,
            "is_channel": True,
        }
        obj = update_adapter.validate_python(data)
        assert isinstance(obj, BotAddedUpdate)
        assert obj.is_channel is True

    def test_bot_removed(self) -> None:
        data = {
            "update_type": "bot_removed",
            "timestamp": 1711000000000,
            "chat_id": 222,
            "user": USER_DATA,
        }
        obj = update_adapter.validate_python(data)
        assert isinstance(obj, BotRemovedUpdate)

    def test_user_added(self) -> None:
        data = {
            "update_type": "user_added",
            "timestamp": 1711000000000,
            "chat_id": 222,
            "user": USER_DATA,
            "inviter_id": 999,
        }
        obj = update_adapter.validate_python(data)
        assert isinstance(obj, UserAddedUpdate)
        assert obj.inviter_id == 999

    def test_user_removed(self) -> None:
        data = {
            "update_type": "user_removed",
            "timestamp": 1711000000000,
            "chat_id": 222,
            "user": USER_DATA,
            "admin_id": 888,
        }
        obj = update_adapter.validate_python(data)
        assert isinstance(obj, UserRemovedUpdate)
        assert obj.admin_id == 888

    def test_chat_title_changed(self) -> None:
        data = {
            "update_type": "chat_title_changed",
            "timestamp": 1711000000000,
            "chat_id": 222,
            "user": USER_DATA,
            "title": "New Title",
        }
        obj = update_adapter.validate_python(data)
        assert isinstance(obj, ChatTitleChangedUpdate)
        assert obj.title == "New Title"


class TestUpdateWithLocale:
    """Webhook-обновления содержат user_locale."""

    def test_message_created_with_locale(self) -> None:
        data = {
            "update_type": "message_created",
            "timestamp": 1711000000000,
            "message": MESSAGE_DATA,
            "user_locale": "ru",
        }
        obj = update_adapter.validate_python(data)
        assert isinstance(obj, MessageCreatedUpdate)
        assert obj.user_locale == "ru"


class TestGetUpdatesResult:
    """Тест результата long polling."""

    def test_parse(self) -> None:
        data = {
            "updates": [
                {
                    "update_type": "message_created",
                    "timestamp": 1711000000000,
                    "message": MESSAGE_DATA,
                },
                {
                    "update_type": "bot_started",
                    "timestamp": 1711000000000,
                    "chat_id": 222,
                    "user": USER_DATA,
                },
            ],
            "marker": 789,
        }
        result = GetUpdatesResult.model_validate(data)
        assert len(result.updates) == 2
        assert isinstance(result.updates[0], MessageCreatedUpdate)
        assert isinstance(result.updates[1], BotStartedUpdate)
        assert result.marker == 789


class TestUpdateRoundTrip:
    """Round-trip: validate → dump → validate."""

    def test_message_created_round_trip(self) -> None:
        data = {
            "update_type": "message_created",
            "timestamp": 1711000000000,
            "message": MESSAGE_DATA,
        }
        obj = update_adapter.validate_python(data)
        dumped = obj.model_dump()
        obj2 = update_adapter.validate_python(dumped)
        assert isinstance(obj2, MessageCreatedUpdate)
        assert obj2.message.body.text == "Привет"
