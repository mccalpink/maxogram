"""Перечисления Max Bot API."""

from enum import StrEnum

__all__ = [
    "AttachmentType",
    "ChatAdminPermission",
    "ChatStatus",
    "ChatType",
    "Intent",
    "MessageLinkType",
    "SenderAction",
    "TextFormat",
    "UpdateType",
    "UploadType",
]


class ChatType(StrEnum):
    """Тип чата в Max."""

    DIALOG = "dialog"
    """Личная переписка (1-на-1)."""
    CHAT = "chat"
    """Групповой чат."""
    CHANNEL = "channel"
    """Канал."""


class ChatStatus(StrEnum):
    """Статус чата."""

    ACTIVE = "active"
    """Активный."""
    REMOVED = "removed"
    """Удалён."""
    LEFT = "left"
    """Бот покинул чат."""
    CLOSED = "closed"
    """Закрыт."""
    SUSPENDED = "suspended"
    """Заблокирован."""


class SenderAction(StrEnum):
    """Действие бота (typing indicator и т.п.)."""

    TYPING_ON = "typing_on"
    """Бот печатает."""
    SENDING_PHOTO = "sending_photo"
    """Бот отправляет фото."""
    SENDING_VIDEO = "sending_video"
    """Бот отправляет видео."""
    SENDING_AUDIO = "sending_audio"
    """Бот отправляет аудио."""
    SENDING_FILE = "sending_file"
    """Бот отправляет файл."""
    MARK_SEEN = "mark_seen"
    """Бот прочитал сообщение."""


class Intent(StrEnum):
    """Визуальный стиль кнопки."""

    POSITIVE = "positive"
    """Позитивный (зелёный)."""
    NEGATIVE = "negative"
    """Негативный (красный)."""
    DEFAULT = "default"
    """Обычный."""


class AttachmentType(StrEnum):
    """Тип вложения."""

    PHOTO = "photo"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"
    STICKER = "sticker"
    CONTACT = "contact"
    SHARE = "share"
    LOCATION = "location"
    INLINE_KEYBOARD = "inline_keyboard"


class UpdateType(StrEnum):
    """Тип обновления (события) — 13 типов в Max Bot API."""

    MESSAGE_CREATED = "message_created"
    """Новое сообщение."""
    MESSAGE_CALLBACK = "message_callback"
    """Нажатие inline-кнопки."""
    MESSAGE_EDITED = "message_edited"
    """Сообщение отредактировано."""
    MESSAGE_REMOVED = "message_removed"
    """Сообщение удалено."""
    MESSAGE_CHAT_CREATED = "message_chat_created"
    """Создан чат через ChatButton."""
    MESSAGE_CONSTRUCTION_REQUEST = "message_construction_request"
    """Запрос конструктора сообщений."""
    MESSAGE_CONSTRUCTED = "message_constructed"
    """Конструктор завершил работу."""
    BOT_STARTED = "bot_started"
    """Пользователь начал диалог с ботом."""
    BOT_ADDED = "bot_added"
    """Бот добавлен в чат."""
    BOT_REMOVED = "bot_removed"
    """Бот удалён из чата."""
    USER_ADDED = "user_added"
    """Пользователь добавлен в чат."""
    USER_REMOVED = "user_removed"
    """Пользователь удалён из чата."""
    CHAT_TITLE_CHANGED = "chat_title_changed"
    """Изменено название чата."""


class MessageLinkType(StrEnum):
    """Тип связи между сообщениями."""

    FORWARD = "forward"
    """Пересланное сообщение."""
    REPLY = "reply"
    """Ответ на сообщение."""


class TextFormat(StrEnum):
    """Формат текста сообщения."""

    MARKDOWN = "markdown"
    HTML = "html"


class UploadType(StrEnum):
    """Тип загружаемого файла."""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"


class ChatAdminPermission(StrEnum):
    """Права администратора чата."""

    READ_ALL_MESSAGES = "read_all_messages"
    """Чтение всех сообщений."""
    ADD_REMOVE_MEMBERS = "add_remove_members"
    """Добавление/удаление участников."""
    ADD_ADMINS = "add_admins"
    """Назначение администраторов."""
    CHANGE_CHAT_INFO = "change_chat_info"
    """Изменение информации о чате."""
    PIN_MESSAGE = "pin_message"
    """Закрепление сообщений."""
    WRITE = "write"
    """Написание сообщений."""
