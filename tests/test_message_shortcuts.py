"""Тесты shortcut-методов Message (answer, reply, edit, delete)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from maxogram.enums import MessageLinkType, SenderAction, TextFormat
from maxogram.types.message import Message, MessageBody, NewMessageLink, Recipient

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


def _make_message(*, with_bot: bool = True) -> Message:
    """Создать Message, опционально привязав mock Bot."""
    msg = Message.model_validate(MESSAGE_JSON)
    if with_bot:
        bot = AsyncMock()
        bot.send_message = AsyncMock()
        bot.edit_message = AsyncMock()
        bot.delete_message = AsyncMock()
        bot.send_action = AsyncMock()
        msg.set_bot(bot)
    return msg


class TestMessageAnswer:
    """Message.answer() — отправка в тот же чат."""

    @pytest.mark.asyncio
    async def test_answer_text(self) -> None:
        msg = _make_message()
        await msg.answer("hello")
        msg.bot.send_message.assert_called_once_with(
            chat_id=222,
            text="hello",
            attachments=None,
            link=None,
            notify=True,
            format=None,
        )

    @pytest.mark.asyncio
    async def test_answer_with_attachments(self) -> None:
        msg = _make_message()
        attachments = [AsyncMock()]
        await msg.answer(attachments=attachments)
        msg.bot.send_message.assert_called_once_with(
            chat_id=222,
            text=None,
            attachments=attachments,
            link=None,
            notify=True,
            format=None,
        )

    @pytest.mark.asyncio
    async def test_answer_with_format(self) -> None:
        msg = _make_message()
        await msg.answer("**bold**", format=TextFormat.MARKDOWN)
        msg.bot.send_message.assert_called_once_with(
            chat_id=222,
            text="**bold**",
            attachments=None,
            link=None,
            notify=True,
            format=TextFormat.MARKDOWN,
        )

    @pytest.mark.asyncio
    async def test_answer_notify_false(self) -> None:
        msg = _make_message()
        await msg.answer("silent", notify=False)
        msg.bot.send_message.assert_called_once_with(
            chat_id=222,
            text="silent",
            attachments=None,
            link=None,
            notify=False,
            format=None,
        )


class TestMessageReply:
    """Message.reply() — ответ с цитатой."""

    @pytest.mark.asyncio
    async def test_reply_creates_link(self) -> None:
        msg = _make_message()
        await msg.reply("ответ")
        call_kwargs = msg.bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 222
        assert call_kwargs["text"] == "ответ"
        link = call_kwargs["link"]
        assert isinstance(link, NewMessageLink)
        assert link.type == MessageLinkType.REPLY
        assert link.mid == "mid_12345"

    @pytest.mark.asyncio
    async def test_reply_with_format(self) -> None:
        msg = _make_message()
        await msg.reply("**bold**", format=TextFormat.MARKDOWN)
        call_kwargs = msg.bot.send_message.call_args.kwargs
        assert call_kwargs["format"] == TextFormat.MARKDOWN


class TestMessageDelete:
    """Message.delete() — удаление сообщения."""

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        msg = _make_message()
        await msg.delete()
        msg.bot.delete_message.assert_called_once_with(message_id="mid_12345")


class TestMessageEdit:
    """Message.edit() — редактирование сообщения."""

    @pytest.mark.asyncio
    async def test_edit_text(self) -> None:
        msg = _make_message()
        await msg.edit("новый текст")
        msg.bot.edit_message.assert_called_once_with(
            message_id="mid_12345",
            text="новый текст",
            attachments=None,
            link=None,
            notify=True,
            format=None,
        )

    @pytest.mark.asyncio
    async def test_edit_with_format(self) -> None:
        msg = _make_message()
        await msg.edit("<b>bold</b>", format=TextFormat.HTML)
        call_kwargs = msg.bot.edit_message.call_args.kwargs
        assert call_kwargs["format"] == TextFormat.HTML


class TestMessageGetBotError:
    """Ошибка при отсутствии Bot."""

    @pytest.mark.asyncio
    async def test_answer_without_bot(self) -> None:
        msg = _make_message(with_bot=False)
        with pytest.raises(RuntimeError, match="not bound to a Bot"):
            await msg.answer("hello")

    @pytest.mark.asyncio
    async def test_reply_without_bot(self) -> None:
        msg = _make_message(with_bot=False)
        with pytest.raises(RuntimeError, match="not bound to a Bot"):
            await msg.reply("hello")

    @pytest.mark.asyncio
    async def test_delete_without_bot(self) -> None:
        msg = _make_message(with_bot=False)
        with pytest.raises(RuntimeError, match="not bound to a Bot"):
            await msg.delete()

    @pytest.mark.asyncio
    async def test_edit_without_bot(self) -> None:
        msg = _make_message(with_bot=False)
        with pytest.raises(RuntimeError, match="not bound to a Bot"):
            await msg.edit("text")

    @pytest.mark.asyncio
    async def test_mark_seen_without_bot(self) -> None:
        msg = _make_message(with_bot=False)
        with pytest.raises(RuntimeError, match="not bound to a Bot"):
            await msg.mark_seen()


class TestMessageMarkSeen:
    """Message.mark_seen() — пометка сообщения как прочитанного."""

    @pytest.mark.asyncio
    async def test_mark_seen_calls_send_action(self) -> None:
        """mark_seen вызывает bot.send_action с MARK_SEEN."""
        msg = _make_message()
        await msg.mark_seen()
        msg.bot.send_action.assert_called_once_with(
            chat_id=222,
            action=SenderAction.MARK_SEEN,
        )

    @pytest.mark.asyncio
    async def test_mark_seen_correct_chat_id(self) -> None:
        """mark_seen использует chat_id из recipient."""
        data = {**MESSAGE_JSON, "recipient": {"chat_id": 999, "chat_type": "chat"}}
        msg = Message.model_validate(data)
        bot = AsyncMock()
        bot.send_action = AsyncMock()
        msg.set_bot(bot)

        await msg.mark_seen()
        bot.send_action.assert_called_once_with(
            chat_id=999,
            action=SenderAction.MARK_SEEN,
        )

    @pytest.mark.asyncio
    async def test_mark_seen_none_chat_id_raises(self) -> None:
        """mark_seen с chat_id=None -> ValueError."""
        msg = Message(
            recipient=Recipient(chat_type="dialog"),  # type: ignore[arg-type]
            timestamp=1700000000000,
            body=MessageBody(mid="mid_1", seq=1, text="hello"),
        )
        bot = AsyncMock()
        bot.send_action = AsyncMock()
        msg.set_bot(bot)

        with pytest.raises(ValueError, match="chat_id"):
            await msg.mark_seen()
