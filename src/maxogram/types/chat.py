"""Типы чатов Max API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from maxogram.enums import ChatAdminPermission, ChatStatus, ChatType
from maxogram.types.base import MaxObject
from maxogram.types.misc import Image, PhotoAttachmentRequestPayload
from maxogram.types.user import UserWithPhoto

if TYPE_CHECKING:
    from maxogram.types.message import Message  # noqa: F811


class Chat(MaxObject):
    """Чат в Max."""

    chat_id: int
    type: ChatType
    status: ChatStatus
    title: str | None = None
    icon: Image | None = None
    last_event_time: int
    participants_count: int
    owner_id: int | None = None
    participants: dict[str, int] | None = None
    is_public: bool
    link: str | None = None
    description: str | None = None
    dialog_with_user: UserWithPhoto | None = None
    messages_count: int | None = None
    chat_message_id: str | None = None
    pinned_message: Message | None = None  # noqa: F821 — resolved via model_rebuild


class ChatMember(UserWithPhoto):
    """Участник чата."""

    last_access_time: int
    is_owner: bool
    is_admin: bool
    join_time: int
    permissions: list[ChatAdminPermission] | None = None


class ChatPatch(MaxObject):
    """Данные для редактирования чата."""

    icon: PhotoAttachmentRequestPayload | None = None
    title: str | None = None
    pin: str | None = None
    notify: bool | None = None


class ChatList(MaxObject):
    """Список чатов с пагинацией."""

    chats: list[Chat]
    marker: int | None = None


class ChatMembersList(MaxObject):
    """Список участников чата с пагинацией."""

    members: list[ChatMember]
    marker: int | None = None
