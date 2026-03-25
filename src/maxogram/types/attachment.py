"""Типы вложений (attachments) Max API."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from maxogram.types.base import MaxObject
from maxogram.types.keyboard import (
    InlineKeyboardAttachmentPayload,
    InlineKeyboardAttachmentRequest,
)
from maxogram.types.misc import PhotoAttachmentRequestPayload
from maxogram.types.user import User

# ---------------------------------------------------------------------------
# Payload-модели (получение из API)
# ---------------------------------------------------------------------------


class PhotoAttachmentPayload(MaxObject):
    """Payload фото-вложения."""

    photo_id: int | None = None
    url: str
    token: str


class VideoAttachmentPayload(MaxObject):
    """Payload видео-вложения."""

    url: str
    token: str


class AudioAttachmentPayload(MaxObject):
    """Payload аудио-вложения."""

    url: str
    token: str


class FileAttachmentPayload(MaxObject):
    """Payload файлового вложения."""

    url: str
    token: str


class StickerAttachmentPayload(MaxObject):
    """Payload стикера."""

    code: str


class ContactAttachmentPayload(MaxObject):
    """Payload контакта."""

    vcf_info: str | None = None
    tam_info: User | None = None


class ShareAttachmentPayload(MaxObject):
    """Payload ссылки-превью."""

    url: str | None = None
    token: str | None = None


# ---------------------------------------------------------------------------
# Attachment-модели (получение из API) — discriminated union по полю `type`
# ---------------------------------------------------------------------------


class PhotoAttachment(MaxObject):
    """Фото-вложение."""

    type: Literal["image"] = "image"
    payload: PhotoAttachmentPayload


class VideoAttachment(MaxObject):
    """Видео-вложение."""

    type: Literal["video"] = "video"
    payload: VideoAttachmentPayload
    thumbnail: PhotoAttachmentPayload | None = None
    width: int | None = None
    height: int | None = None
    duration: int | None = None


class AudioAttachment(MaxObject):
    """Аудио-вложение."""

    type: Literal["audio"] = "audio"
    payload: AudioAttachmentPayload


class FileAttachment(MaxObject):
    """Файловое вложение."""

    type: Literal["file"] = "file"
    payload: FileAttachmentPayload
    filename: str
    size: int


class StickerAttachment(MaxObject):
    """Стикер."""

    type: Literal["sticker"] = "sticker"
    payload: StickerAttachmentPayload
    width: int
    height: int


class ContactAttachment(MaxObject):
    """Контакт."""

    type: Literal["contact"] = "contact"
    payload: ContactAttachmentPayload


class InlineKeyboardAttachment(MaxObject):
    """Inline-клавиатура (как вложение)."""

    type: Literal["inline_keyboard"] = "inline_keyboard"
    payload: InlineKeyboardAttachmentPayload


class ShareAttachment(MaxObject):
    """Ссылка-превью."""

    type: Literal["share"] = "share"
    payload: ShareAttachmentPayload
    title: str | None = None
    description: str | None = None
    image_url: str | None = None


class LocationAttachment(MaxObject):
    """Геолокация."""

    type: Literal["location"] = "location"
    latitude: float
    longitude: float


Attachment = Annotated[
    Union[
        PhotoAttachment,
        VideoAttachment,
        AudioAttachment,
        FileAttachment,
        StickerAttachment,
        ContactAttachment,
        InlineKeyboardAttachment,
        ShareAttachment,
        LocationAttachment,
    ],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Payload-модели для запросов (отправка в API)
# ---------------------------------------------------------------------------


class UploadedInfo(MaxObject):
    """Токен загруженного файла."""

    token: str


class ContactAttachmentRequestPayload(MaxObject):
    """Payload контакта для отправки."""

    name: str | None = None
    contact_id: int | None = None
    vcf_info: str | None = None
    vcf_phone: str | None = None


class ShareAttachmentRequestPayload(MaxObject):
    """Payload ссылки-превью для отправки."""

    url: str | None = None
    token: str | None = None


class StickerAttachmentRequestPayload(MaxObject):
    """Payload стикера для отправки."""

    code: str


class LocationAttachmentRequestPayload(MaxObject):
    """Payload геолокации для отправки."""

    latitude: float
    longitude: float


# ---------------------------------------------------------------------------
# AttachmentRequest-модели (отправка в API) — discriminated union по полю `type`
# ---------------------------------------------------------------------------


class PhotoAttachmentRequest(MaxObject):
    """Запрос фото-вложения."""

    type: Literal["image"] = "image"
    payload: PhotoAttachmentRequestPayload


class VideoAttachmentRequest(MaxObject):
    """Запрос видео-вложения."""

    type: Literal["video"] = "video"
    payload: UploadedInfo


class AudioAttachmentRequest(MaxObject):
    """Запрос аудио-вложения."""

    type: Literal["audio"] = "audio"
    payload: UploadedInfo


class FileAttachmentRequest(MaxObject):
    """Запрос файлового вложения."""

    type: Literal["file"] = "file"
    payload: UploadedInfo


class StickerAttachmentRequest(MaxObject):
    """Запрос стикера."""

    type: Literal["sticker"] = "sticker"
    payload: StickerAttachmentRequestPayload


class ContactAttachmentRequest(MaxObject):
    """Запрос контакта."""

    type: Literal["contact"] = "contact"
    payload: ContactAttachmentRequestPayload


class InlineKeyboardAttachmentRequestWrapper(MaxObject):
    """Запрос inline-клавиатуры."""

    type: Literal["inline_keyboard"] = "inline_keyboard"
    payload: InlineKeyboardAttachmentRequest


class ShareAttachmentRequest(MaxObject):
    """Запрос ссылки-превью."""

    type: Literal["share"] = "share"
    payload: ShareAttachmentRequestPayload


class LocationAttachmentRequest(MaxObject):
    """Запрос геолокации."""

    type: Literal["location"] = "location"
    latitude: float
    longitude: float


AttachmentRequest = Annotated[
    Union[
        PhotoAttachmentRequest,
        VideoAttachmentRequest,
        AudioAttachmentRequest,
        FileAttachmentRequest,
        StickerAttachmentRequest,
        ContactAttachmentRequest,
        InlineKeyboardAttachmentRequestWrapper,
        ShareAttachmentRequest,
        LocationAttachmentRequest,
    ],
    Field(discriminator="type"),
]
