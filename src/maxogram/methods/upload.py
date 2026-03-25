"""Методы загрузки файлов — /uploads."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from maxogram.enums import UploadType
from maxogram.methods.base import MaxMethod
from maxogram.types.upload import UploadEndpoint


class GetUploadUrl(MaxMethod["UploadEndpoint"]):
    """POST /uploads — Получение URL для загрузки файла."""

    __api_path__: ClassVar[str] = "/uploads"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = UploadEndpoint
    __query_params__: ClassVar[frozenset[str]] = frozenset({"type_"})

    type_: UploadType = Field(alias="type")
