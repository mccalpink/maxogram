"""Типы загрузки файлов Max API."""

from __future__ import annotations

from maxogram.types.base import MaxObject


class UploadEndpoint(MaxObject):
    """URL для загрузки файла (ответ POST /uploads)."""

    url: str


class UploadedFileInfo(MaxObject):
    """Информация о загруженном файле."""

    token: str
