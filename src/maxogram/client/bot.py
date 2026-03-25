"""Bot — фасад над Session для Max Bot API."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from maxogram.client.session.aiohttp import AiohttpSession
from maxogram.client.session.base import BaseSession
from maxogram.enums import SenderAction, TextFormat, UploadType
from maxogram.methods.bot import EditMyInfo, GetMyInfo
from maxogram.methods.callback import AnswerOnCallback, Construct
from maxogram.methods.chat import (
    DeleteChat,
    EditChat,
    GetChat,
    GetChatByLink,
    GetChats,
    LeaveChat,
    SendAction,
)
from maxogram.methods.member import (
    AddAdmins,
    AddMembers,
    GetAdmins,
    GetMembers,
    GetMembership,
    RemoveMember,
)
from maxogram.methods.message import (
    DeleteMessage,
    EditMessage,
    GetMessageById,
    GetMessages,
    SendMessage,
)
from maxogram.methods.pin import GetPinnedMessage, PinMessage, UnpinMessage
from maxogram.methods.subscription import GetSubscriptions, Subscribe, Unsubscribe
from maxogram.methods.update import GetUpdates
from maxogram.methods.upload import GetUploadUrl
from maxogram.types.base import MaxObject

if TYPE_CHECKING:
    from maxogram.methods.base import MaxMethod
    from maxogram.types.attachment import AttachmentRequest
    from maxogram.types.chat import Chat, ChatList, ChatMember, ChatMembersList
    from maxogram.types.constructor import ConstructedMessageBody
    from maxogram.types.keyboard import Keyboard
    from maxogram.types.message import (
        Message,
        MessageList,
        NewMessageBody,
        NewMessageLink,
        SendMessageResult,
    )
    from maxogram.types.misc import (
        GetPinnedMessageResult,
        GetSubscriptionsResult,
        PhotoAttachmentRequestPayload,
        SimpleQueryResult,
    )
    from maxogram.types.update import GetUpdatesResult
    from maxogram.types.upload import UploadEndpoint
    from maxogram.types.user import BotCommand, BotInfo

T = TypeVar("T")

__all__ = ["Bot"]


def _mask_token(token: str) -> str:
    """Маскирует токен, оставляя первые 4 и последние 4 символа."""
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"


class Bot:
    """Фасад над Session для Max Bot API.

    Хранит token, создаёт MaxMethod, вызывает Session.
    Propagates set_bot на результат (MaxObject).
    30 shortcut-методов для всех API endpoints.
    """

    def __init__(
        self,
        token: str,
        session: BaseSession | None = None,
    ) -> None:
        self.token = token
        self.session = session or AiohttpSession()
        self._me: BotInfo | None = None

    def __repr__(self) -> str:
        """Безопасный repr: маскирует токен."""
        return f"Bot(token='{_mask_token(self.token)}')"

    def __str__(self) -> str:
        """Безопасный str: маскирует токен."""
        return f"Bot(token='{_mask_token(self.token)}')"

    async def __call__(self, method: MaxMethod[T]) -> T:
        """Вызвать MaxMethod через Session."""
        result = await self.session(self, method)
        if isinstance(result, MaxObject):
            result.set_bot(self)
        return result  # type: ignore[no-any-return]

    async def close(self) -> None:
        """Закрыть сессию."""
        await self.session.close()

    async def __aenter__(self) -> Bot:
        """Вход в async context manager."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Выход из async context manager — закрыть сессию."""
        await self.close()

    async def me(self) -> BotInfo:
        """Кэшированная информация о боте."""
        if self._me is None:
            self._me = await self.get_my_info()
        return self._me

    # ------------------------------------------------------------------
    # Bot (2 метода)
    # ------------------------------------------------------------------

    async def get_my_info(self) -> BotInfo:
        """GET /me — Получение информации о боте."""
        return await self(GetMyInfo())

    async def edit_my_info(
        self,
        name: str | None = None,
        description: str | None = None,
        commands: list[BotCommand] | None = None,
        photo: PhotoAttachmentRequestPayload | None = None,
    ) -> BotInfo:
        """PATCH /me — Редактирование информации о боте."""
        return await self(
            EditMyInfo(
                name=name,
                description=description,
                commands=commands,
                photo=photo,
            )
        )

    # ------------------------------------------------------------------
    # Chat (7 методов)
    # ------------------------------------------------------------------

    async def get_chats(
        self,
        count: int | None = None,
        marker: int | None = None,
    ) -> ChatList:
        """GET /chats — Список чатов бота."""
        return await self(GetChats(count=count, marker=marker))

    async def get_chat(self, chat_id: int) -> Chat:
        """GET /chats/{chatId} — Информация о чате."""
        return await self(GetChat(chat_id=chat_id))

    async def get_chat_by_link(self, chat_link: str) -> Chat:
        """GET /chats/{chatLink} — Чат по публичной ссылке."""
        return await self(GetChatByLink(chat_link=chat_link))

    async def edit_chat(
        self,
        chat_id: int,
        icon: PhotoAttachmentRequestPayload | None = None,
        title: str | None = None,
        pin: str | None = None,
        notify: bool | None = None,
    ) -> Chat:
        """PATCH /chats/{chatId} — Редактирование чата."""
        return await self(
            EditChat(
                chat_id=chat_id,
                icon=icon,
                title=title,
                pin=pin,
                notify=notify,
            )
        )

    async def delete_chat(self, chat_id: int) -> SimpleQueryResult:
        """DELETE /chats/{chatId} — Удаление чата."""
        return await self(DeleteChat(chat_id=chat_id))

    async def send_action(
        self,
        chat_id: int,
        action: SenderAction,
    ) -> SimpleQueryResult:
        """POST /chats/{chatId}/actions — Отправка действия в чат."""
        return await self(SendAction(chat_id=chat_id, action=action))

    async def leave_chat(self, chat_id: int) -> SimpleQueryResult:
        """DELETE /chats/{chatId}/members/me — Выход бота из чата."""
        return await self(LeaveChat(chat_id=chat_id))

    # ------------------------------------------------------------------
    # Pin (3 метода)
    # ------------------------------------------------------------------

    async def get_pinned_message(self, chat_id: int) -> GetPinnedMessageResult:
        """GET /chats/{chatId}/pin — Закреплённое сообщение."""
        return await self(GetPinnedMessage(chat_id=chat_id))

    async def pin_message(
        self,
        chat_id: int,
        message_id: str,
        notify: bool = True,
    ) -> SimpleQueryResult:
        """PUT /chats/{chatId}/pin — Закрепить сообщение."""
        return await self(
            PinMessage(
                chat_id=chat_id,
                message_id=message_id,
                notify=notify,
            )
        )

    async def unpin_message(self, chat_id: int) -> SimpleQueryResult:
        """DELETE /chats/{chatId}/pin — Открепить сообщение."""
        return await self(UnpinMessage(chat_id=chat_id))

    # ------------------------------------------------------------------
    # Member (6 методов)
    # ------------------------------------------------------------------

    async def get_members(
        self,
        chat_id: int,
        user_ids: list[int] | None = None,
        marker: int | None = None,
        count: int | None = None,
    ) -> ChatMembersList:
        """GET /chats/{chatId}/members — Список участников."""
        return await self(
            GetMembers(
                chat_id=chat_id,
                user_ids=user_ids,
                marker=marker,
                count=count,
            )
        )

    async def add_members(
        self,
        chat_id: int,
        user_ids: list[int],
    ) -> SimpleQueryResult:
        """POST /chats/{chatId}/members — Добавить участников."""
        return await self(AddMembers(chat_id=chat_id, user_ids=user_ids))

    async def remove_member(
        self,
        chat_id: int,
        user_id: int,
        block: bool | None = None,
    ) -> SimpleQueryResult:
        """DELETE /chats/{chatId}/members — Удалить участника."""
        return await self(
            RemoveMember(
                chat_id=chat_id,
                user_id=user_id,
                block=block,
            )
        )

    async def get_membership(self, chat_id: int) -> ChatMember:
        """GET /chats/{chatId}/members/me — Членство бота."""
        return await self(GetMembership(chat_id=chat_id))

    async def get_admins(self, chat_id: int) -> ChatMembersList:
        """GET /chats/{chatId}/members/admins — Администраторы."""
        return await self(GetAdmins(chat_id=chat_id))

    async def add_admins(
        self,
        chat_id: int,
        user_ids: list[int],
    ) -> SimpleQueryResult:
        """POST /chats/{chatId}/members/admins — Назначить администраторов."""
        return await self(AddAdmins(chat_id=chat_id, user_ids=user_ids))

    # ------------------------------------------------------------------
    # Message (5 методов)
    # ------------------------------------------------------------------

    async def send_message(
        self,
        chat_id: int | None = None,
        user_id: int | None = None,
        text: str | None = None,
        attachments: list[AttachmentRequest] | None = None,
        link: NewMessageLink | None = None,
        notify: bool = True,
        format: TextFormat | None = None,  # noqa: A002
        disable_link_preview: bool | None = None,
    ) -> SendMessageResult:
        """POST /messages — Отправка сообщения."""
        return await self(
            SendMessage(
                chat_id=chat_id,
                user_id=user_id,
                text=text,
                attachments=attachments,
                link=link,
                notify=notify,
                format=format,
                disable_link_preview=disable_link_preview,
            )
        )

    async def edit_message(
        self,
        message_id: str,
        text: str | None = None,
        attachments: list[AttachmentRequest] | None = None,
        link: NewMessageLink | None = None,
        notify: bool = True,
        format: TextFormat | None = None,  # noqa: A002
    ) -> SimpleQueryResult:
        """PUT /messages — Редактирование сообщения."""
        return await self(
            EditMessage(
                message_id=message_id,
                text=text,
                attachments=attachments,
                link=link,
                notify=notify,
                format=format,
            )
        )

    async def delete_message(self, message_id: str) -> SimpleQueryResult:
        """DELETE /messages — Удаление сообщения."""
        return await self(DeleteMessage(message_id=message_id))

    async def get_messages(
        self,
        chat_id: int | None = None,
        message_ids: list[str] | None = None,
        from_: int | None = None,
        to: int | None = None,
        count: int | None = None,
    ) -> MessageList:
        """GET /messages — Получение сообщений."""
        return await self(
            GetMessages(
                chat_id=chat_id,
                message_ids=message_ids,
                from_=from_,
                to=to,
                count=count,
            )
        )

    async def get_message_by_id(self, message_id: str) -> Message:
        """GET /messages/{messageId} — Сообщение по ID."""
        return await self(GetMessageById(message_id=message_id))

    # ------------------------------------------------------------------
    # Callback (2 метода)
    # ------------------------------------------------------------------

    async def answer_on_callback(
        self,
        callback_id: str,
        message: NewMessageBody | None = None,
        notification: str | None = None,
    ) -> SimpleQueryResult:
        """POST /answers — Ответ на callback."""
        return await self(
            AnswerOnCallback(
                callback_id=callback_id,
                message=message,
                notification=notification,
            )
        )

    async def construct(
        self,
        session_id: str,
        messages: list[ConstructedMessageBody] | None = None,
        allow_user_input: bool = False,
        hint: str | None = None,
        data: str | None = None,
        keyboard: Keyboard | None = None,
        placeholder: str | None = None,
    ) -> SimpleQueryResult:
        """POST /answers/constructor — Ответ конструктора."""
        return await self(
            Construct(
                session_id=session_id,
                messages=messages,
                allow_user_input=allow_user_input,
                hint=hint,
                data=data,
                keyboard=keyboard,
                placeholder=placeholder,
            )
        )

    # ------------------------------------------------------------------
    # Subscription (3 метода)
    # ------------------------------------------------------------------

    async def get_subscriptions(self) -> GetSubscriptionsResult:
        """GET /subscriptions — Список подписок."""
        return await self(GetSubscriptions())

    async def subscribe(
        self,
        url: str,
        update_types: list[str],
        version: str | None = None,
    ) -> SimpleQueryResult:
        """POST /subscriptions — Создать webhook-подписку."""
        return await self(
            Subscribe(
                url=url,
                update_types=update_types,
                version=version,
            )
        )

    async def unsubscribe(self, url: str) -> SimpleQueryResult:
        """DELETE /subscriptions — Удалить webhook-подписку."""
        return await self(Unsubscribe(url=url))

    # ------------------------------------------------------------------
    # Upload (1 метод)
    # ------------------------------------------------------------------

    async def get_upload_url(self, type_: UploadType) -> UploadEndpoint:
        """POST /uploads — Получение URL для загрузки файла."""
        return await self(GetUploadUrl(type_=type_))

    # ------------------------------------------------------------------
    # Update (1 метод)
    # ------------------------------------------------------------------

    async def get_updates(
        self,
        limit: int | None = None,
        timeout: int | None = None,
        marker: int | None = None,
        types: list[str] | None = None,
    ) -> GetUpdatesResult:
        """GET /updates — Long polling для получения обновлений."""
        return await self(
            GetUpdates(
                limit=limit,
                timeout=timeout,
                marker=marker,
                types=types,
            )
        )
