"""Типы сообщений Max API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from maxogram.enums import ChatType, MessageLinkType, SenderAction, TextFormat
from maxogram.types.attachment import Attachment, AttachmentRequest
from maxogram.types.base import MaxObject
from maxogram.types.markup import MarkupElement
from maxogram.types.user import User

if TYPE_CHECKING:
    from maxogram.client.bot import Bot
    from maxogram.types.misc import SimpleQueryResult


class Recipient(MaxObject):
    """Получатель сообщения."""

    chat_id: int | None = None
    chat_type: ChatType
    user_id: int | None = None


class MessageStat(MaxObject):
    """Статистика сообщения (только для каналов)."""

    views: int


class LinkedMessage(MaxObject):
    """Связанное сообщение (forward/reply)."""

    type: MessageLinkType
    sender: User | None = None
    chat_id: int | None = None
    message: MessageBody


class NewMessageLink(MaxObject):
    """Ссылка на сообщение при отправке (reply/forward)."""

    type: MessageLinkType
    mid: str


class MessageBody(MaxObject):
    """Тело сообщения."""

    mid: str
    seq: int
    text: str | None = None
    attachments: list[Attachment] | None = None
    markup: list[MarkupElement] | None = None


class Message(MaxObject):
    """Сообщение Max."""

    sender: User | None = None
    recipient: Recipient
    timestamp: int
    link: LinkedMessage | None = None
    body: MessageBody
    stat: MessageStat | None = None
    url: str | None = None
    constructor: User | None = None

    @property
    def datetime(self) -> datetime:
        """Время сообщения как datetime (UTC)."""
        return datetime.fromtimestamp(self.timestamp / 1000, tz=UTC)

    @property
    def text(self) -> str | None:
        """Текст сообщения (shortcut для body.text)."""
        return self.body.text

    @property
    def chat_id(self) -> int | None:
        """ID чата (shortcut для recipient.chat_id)."""
        return self.recipient.chat_id

    @property
    def message_id(self) -> str:
        """ID сообщения (shortcut для body.mid)."""
        return self.body.mid

    def _get_bot(self) -> Bot:
        """Получить Bot или поднять RuntimeError."""
        if self._bot is None:
            msg = (
                "Message is not bound to a Bot. "
                "This usually means the message was created manually, "
                "not received from API."
            )
            raise RuntimeError(msg)
        return self._bot  # type: ignore[no-any-return]

    async def answer(
        self,
        text: str | None = None,
        *,
        attachments: list[AttachmentRequest] | None = None,
        link: NewMessageLink | None = None,
        notify: bool = True,
        format: TextFormat | None = None,  # noqa: A002
    ) -> SendMessageResult:
        """Отправить ответ в тот же чат."""
        bot = self._get_bot()
        return await bot.send_message(
            chat_id=self.chat_id,
            text=text,
            attachments=attachments,
            link=link,
            notify=notify,
            format=format,
        )

    async def reply(
        self,
        text: str | None = None,
        *,
        attachments: list[AttachmentRequest] | None = None,
        notify: bool = True,
        format: TextFormat | None = None,  # noqa: A002
    ) -> SendMessageResult:
        """Ответить на сообщение (с цитатой)."""
        bot = self._get_bot()
        reply_link = NewMessageLink(type=MessageLinkType.REPLY, mid=self.message_id)
        return await bot.send_message(
            chat_id=self.chat_id,
            text=text,
            attachments=attachments,
            link=reply_link,
            notify=notify,
            format=format,
        )

    async def delete(self) -> SimpleQueryResult:
        """Удалить сообщение."""
        bot = self._get_bot()
        return await bot.delete_message(message_id=self.message_id)

    async def edit(
        self,
        text: str | None = None,
        *,
        attachments: list[AttachmentRequest] | None = None,
        link: NewMessageLink | None = None,
        notify: bool = True,
        format: TextFormat | None = None,  # noqa: A002
    ) -> SimpleQueryResult:
        """Редактировать сообщение."""
        bot = self._get_bot()
        return await bot.edit_message(
            message_id=self.message_id,
            text=text,
            attachments=attachments,
            link=link,
            notify=notify,
            format=format,
        )

    async def mark_seen(self) -> SimpleQueryResult:
        """Пометить сообщение как прочитанное (mark_seen action)."""
        bot = self._get_bot()
        chat_id = self.chat_id
        if chat_id is None:
            msg = "Cannot mark_seen: chat_id is None"
            raise ValueError(msg)
        return await bot.send_action(
            chat_id=chat_id,
            action=SenderAction.MARK_SEEN,
        )


class NewMessageBody(MaxObject):
    """Тело нового сообщения (для отправки)."""

    text: str | None = None
    attachments: list[AttachmentRequest] | None = None
    link: NewMessageLink | None = None
    notify: bool = True
    format: TextFormat | None = None


class MessageList(MaxObject):
    """Список сообщений."""

    messages: list[Message]


class SendMessageResult(MaxObject):
    """Результат отправки сообщения."""

    message: Message
