"""Тесты для types/message.py."""

from __future__ import annotations

from datetime import UTC, datetime

from maxogram.types.message import (
    LinkedMessage,
    Message,
    MessageBody,
    MessageList,
    MessageStat,
    NewMessageBody,
    NewMessageLink,
    Recipient,
    SendMessageResult,
)

MESSAGE_JSON = {
    "sender": {
        "user_id": 111,
        "name": "Иван",
        "is_bot": False,
        "last_activity_time": 1711000000000,
    },
    "recipient": {"chat_id": 222, "chat_type": "dialog"},
    "timestamp": 1711000000000,
    "body": {
        "mid": "mid_12345",
        "seq": 1,
        "text": "Привет",
    },
}


class TestRecipient:
    def test_create(self) -> None:
        r = Recipient(chat_id=222, chat_type="dialog")
        assert r.chat_id == 222
        assert r.chat_type == "dialog"

    def test_user_id(self) -> None:
        r = Recipient(chat_type="dialog", user_id=111)
        assert r.user_id == 111


class TestMessageBody:
    def test_create(self) -> None:
        body = MessageBody(mid="mid_1", seq=1, text="Hello")
        assert body.mid == "mid_1"
        assert body.text == "Hello"

    def test_attachments_optional(self) -> None:
        body = MessageBody(mid="mid_1", seq=1)
        assert body.attachments is None
        assert body.markup is None


class TestMessage:
    def test_parse_json(self) -> None:
        msg = Message.model_validate(MESSAGE_JSON)
        assert msg.sender is not None
        assert msg.sender.user_id == 111
        assert msg.body.text == "Привет"

    def test_text_shortcut(self) -> None:
        msg = Message.model_validate(MESSAGE_JSON)
        assert msg.text == "Привет"

    def test_chat_id_shortcut(self) -> None:
        msg = Message.model_validate(MESSAGE_JSON)
        assert msg.chat_id == 222

    def test_message_id_shortcut(self) -> None:
        msg = Message.model_validate(MESSAGE_JSON)
        assert msg.message_id == "mid_12345"

    def test_datetime_property(self) -> None:
        msg = Message.model_validate(MESSAGE_JSON)
        dt = msg.datetime
        assert isinstance(dt, datetime)
        assert dt.tzinfo == UTC
        expected = datetime.fromtimestamp(1711000000000 / 1000, tz=UTC)
        assert dt == expected

    def test_round_trip(self) -> None:
        msg = Message.model_validate(MESSAGE_JSON)
        dumped = msg.model_dump()
        msg2 = Message.model_validate(dumped)
        assert msg2.body.mid == msg.body.mid
        assert msg2.timestamp == msg.timestamp


class TestLinkedMessage:
    def test_reply(self) -> None:
        data = {
            "type": "reply",
            "sender": {
                "user_id": 111,
                "name": "Иван",
                "is_bot": False,
                "last_activity_time": 1711000000000,
            },
            "message": {"mid": "mid_orig", "seq": 1, "text": "Original"},
        }
        linked = LinkedMessage.model_validate(data)
        assert linked.type == "reply"
        assert linked.message.text == "Original"


class TestNewMessageLink:
    def test_create(self) -> None:
        link = NewMessageLink(type="reply", mid="mid_123")
        assert link.type == "reply"
        assert link.mid == "mid_123"


class TestMessageStat:
    def test_create(self) -> None:
        stat = MessageStat(views=100)
        assert stat.views == 100


class TestNewMessageBody:
    def test_minimal(self) -> None:
        body = NewMessageBody(text="Hello")
        assert body.text == "Hello"
        assert body.notify is True
        assert body.format is None

    def test_with_format(self) -> None:
        body = NewMessageBody(text="**bold**", format="markdown")
        assert body.format == "markdown"


class TestMessageList:
    def test_create(self) -> None:
        data = {"messages": [MESSAGE_JSON]}
        ml = MessageList.model_validate(data)
        assert len(ml.messages) == 1


class TestSendMessageResult:
    def test_create(self) -> None:
        data = {"message": MESSAGE_JSON}
        result = SendMessageResult.model_validate(data)
        assert result.message.body.mid == "mid_12345"
