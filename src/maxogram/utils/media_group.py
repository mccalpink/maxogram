"""Построитель медиа-групп для Max API.

Позволяет собирать список вложений (attachments) для отправки
нескольких медиа-файлов в одном сообщении.
"""

from __future__ import annotations

from maxogram.types.attachment import (
    AudioAttachmentRequest,
    FileAttachmentRequest,
    PhotoAttachmentRequest,
    UploadedInfo,
    VideoAttachmentRequest,
)
from maxogram.types.misc import PhotoAttachmentRequestPayload

__all__ = ["MediaGroupBuilder"]

# Тип для элементов медиа-группы (только медиа-вложения, без клавиатур и т.п.)
MediaAttachmentRequest = (
    PhotoAttachmentRequest
    | VideoAttachmentRequest
    | AudioAttachmentRequest
    | FileAttachmentRequest
)


class MediaGroupBuilder:
    """Построитель медиа-групп для отправки нескольких вложений в сообщении.

    Пример::

        builder = MediaGroupBuilder()
        builder.add_photo(token="upload_token_1")
        builder.add_video(token="upload_token_2")
        attachments = builder.build()
        await bot.send_message(chat_id=123, attachments=attachments)
    """

    def __init__(self) -> None:
        self._attachments: list[MediaAttachmentRequest] = []

    def add_photo(
        self,
        *,
        token: str | None = None,
        url: str | None = None,
    ) -> MediaGroupBuilder:
        """Добавить фото-вложение.

        Args:
            token: Upload token загруженного фото.
            url: URL фото для отправки по ссылке.

        Returns:
            self для fluent API.

        Raises:
            ValueError: Если не указан ни token, ни url, или указаны оба.
        """
        if (token is None) == (url is None):
            msg = "Укажите ровно один из параметров: token или url."
            raise ValueError(msg)
        payload = PhotoAttachmentRequestPayload(token=token, url=url)
        self._attachments.append(PhotoAttachmentRequest(payload=payload))
        return self

    def add_video(self, *, token: str | None = None) -> MediaGroupBuilder:
        """Добавить видео-вложение.

        Args:
            token: Upload token загруженного видео.

        Returns:
            self для fluent API.

        Raises:
            ValueError: Если token не указан.
        """
        if token is None:
            msg = "Укажите token для видео-вложения."
            raise ValueError(msg)
        self._attachments.append(
            VideoAttachmentRequest(payload=UploadedInfo(token=token)),
        )
        return self

    def add_audio(self, *, token: str | None = None) -> MediaGroupBuilder:
        """Добавить аудио-вложение.

        Args:
            token: Upload token загруженного аудио.

        Returns:
            self для fluent API.

        Raises:
            ValueError: Если token не указан.
        """
        if token is None:
            msg = "Укажите token для аудио-вложения."
            raise ValueError(msg)
        self._attachments.append(
            AudioAttachmentRequest(payload=UploadedInfo(token=token)),
        )
        return self

    def add_file(self, *, token: str | None = None) -> MediaGroupBuilder:
        """Добавить файловое вложение.

        Args:
            token: Upload token загруженного файла.

        Returns:
            self для fluent API.

        Raises:
            ValueError: Если token не указан.
        """
        if token is None:
            msg = "Укажите token для файлового вложения."
            raise ValueError(msg)
        self._attachments.append(
            FileAttachmentRequest(payload=UploadedInfo(token=token)),
        )
        return self

    def add(self, attachment: MediaAttachmentRequest) -> MediaGroupBuilder:
        """Добавить готовый AttachmentRequest.

        Args:
            attachment: Готовый объект вложения.

        Returns:
            self для fluent API.
        """
        self._attachments.append(attachment)
        return self

    def build(self) -> list[MediaAttachmentRequest]:
        """Собрать список вложений.

        Returns:
            Копия списка добавленных вложений.
        """
        return list(self._attachments)
