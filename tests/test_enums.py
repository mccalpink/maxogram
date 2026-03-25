"""Тесты для перечислений maxogram."""

from enum import StrEnum

from maxogram.enums import (
    AttachmentType,
    ChatAdminPermission,
    ChatStatus,
    ChatType,
    Intent,
    MessageLinkType,
    SenderAction,
    TextFormat,
    UpdateType,
    UploadType,
)


class TestChatType:
    """Тесты ChatType."""

    def test_values(self) -> None:
        assert ChatType.DIALOG == "dialog"
        assert ChatType.CHAT == "chat"
        assert ChatType.CHANNEL == "channel"

    def test_is_str_enum(self) -> None:
        assert issubclass(ChatType, StrEnum)

    def test_from_string(self) -> None:
        assert ChatType("dialog") == ChatType.DIALOG


class TestChatStatus:
    """Тесты ChatStatus."""

    def test_values(self) -> None:
        assert ChatStatus.ACTIVE == "active"
        assert ChatStatus.REMOVED == "removed"
        assert ChatStatus.LEFT == "left"
        assert ChatStatus.CLOSED == "closed"
        assert ChatStatus.SUSPENDED == "suspended"


class TestSenderAction:
    """Тесты SenderAction."""

    def test_values(self) -> None:
        assert SenderAction.TYPING_ON == "typing_on"
        assert SenderAction.SENDING_PHOTO == "sending_photo"
        assert SenderAction.SENDING_VIDEO == "sending_video"
        assert SenderAction.SENDING_AUDIO == "sending_audio"
        assert SenderAction.SENDING_FILE == "sending_file"
        assert SenderAction.MARK_SEEN == "mark_seen"


class TestIntent:
    """Тесты Intent."""

    def test_values(self) -> None:
        assert Intent.POSITIVE == "positive"
        assert Intent.NEGATIVE == "negative"
        assert Intent.DEFAULT == "default"


class TestAttachmentType:
    """Тесты AttachmentType."""

    def test_values(self) -> None:
        assert AttachmentType.PHOTO == "photo"
        assert AttachmentType.VIDEO == "video"
        assert AttachmentType.AUDIO == "audio"
        assert AttachmentType.FILE == "file"
        assert AttachmentType.STICKER == "sticker"
        assert AttachmentType.CONTACT == "contact"
        assert AttachmentType.SHARE == "share"
        assert AttachmentType.LOCATION == "location"
        assert AttachmentType.INLINE_KEYBOARD == "inline_keyboard"


class TestUpdateType:
    """Тесты UpdateType — 13 типов событий Max API."""

    def test_all_13_types(self) -> None:
        assert len(UpdateType) == 13

    def test_values(self) -> None:
        assert UpdateType.MESSAGE_CREATED == "message_created"
        assert UpdateType.MESSAGE_CALLBACK == "message_callback"
        assert UpdateType.MESSAGE_EDITED == "message_edited"
        assert UpdateType.MESSAGE_REMOVED == "message_removed"
        assert UpdateType.MESSAGE_CHAT_CREATED == "message_chat_created"
        assert UpdateType.MESSAGE_CONSTRUCTION_REQUEST == "message_construction_request"
        assert UpdateType.MESSAGE_CONSTRUCTED == "message_constructed"
        assert UpdateType.BOT_STARTED == "bot_started"
        assert UpdateType.BOT_ADDED == "bot_added"
        assert UpdateType.BOT_REMOVED == "bot_removed"
        assert UpdateType.USER_ADDED == "user_added"
        assert UpdateType.USER_REMOVED == "user_removed"
        assert UpdateType.CHAT_TITLE_CHANGED == "chat_title_changed"


class TestMessageLinkType:
    """Тесты MessageLinkType."""

    def test_values(self) -> None:
        assert MessageLinkType.FORWARD == "forward"
        assert MessageLinkType.REPLY == "reply"


class TestTextFormat:
    """Тесты TextFormat."""

    def test_values(self) -> None:
        assert TextFormat.MARKDOWN == "markdown"
        assert TextFormat.HTML == "html"


class TestUploadType:
    """Тесты UploadType."""

    def test_values(self) -> None:
        assert UploadType.IMAGE == "image"
        assert UploadType.VIDEO == "video"
        assert UploadType.AUDIO == "audio"
        assert UploadType.FILE == "file"


class TestChatAdminPermission:
    """Тесты ChatAdminPermission."""

    def test_values(self) -> None:
        assert ChatAdminPermission.READ_ALL_MESSAGES == "read_all_messages"
        assert ChatAdminPermission.ADD_REMOVE_MEMBERS == "add_remove_members"
        assert ChatAdminPermission.ADD_ADMINS == "add_admins"
        assert ChatAdminPermission.CHANGE_CHAT_INFO == "change_chat_info"
        assert ChatAdminPermission.PIN_MESSAGE == "pin_message"
        assert ChatAdminPermission.WRITE == "write"
