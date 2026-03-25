"""MaxInputFile и наследники — абстракция загрузки файлов в Max API.

Двухэтапная загрузка:
1. ``bot.get_upload_url(type_)`` → получить URL для загрузки
2. ``POST <upload_url>`` multipart/form-data → получить token
3. Использовать token в attachments при отправке сообщения

Классы:
- :class:`BufferedInputFile` — из bytes в памяти
- :class:`FSInputFile` — из файла на диске
- :class:`URLInputFile` — скачивание по URL и загрузка
- :class:`TokenInputFile` — переиспользование уже загруженного файла
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiohttp

from maxogram.enums import UploadType

__all__ = [
    "BufferedInputFile",
    "FSInputFile",
    "MaxInputFile",
    "TokenInputFile",
    "URLInputFile",
]

# Маппинг расширений → UploadType
_EXTENSION_MAP: dict[str, UploadType] = {}
for _ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".svg"):
    _EXTENSION_MAP[_ext] = UploadType.IMAGE
for _ext in (".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"):
    _EXTENSION_MAP[_ext] = UploadType.VIDEO
for _ext in (".mp3", ".ogg", ".wav", ".flac", ".aac", ".wma", ".m4a"):
    _EXTENSION_MAP[_ext] = UploadType.AUDIO


def _detect_upload_type(filename: str) -> UploadType:
    """Определить UploadType по расширению файла."""
    ext = Path(filename).suffix.lower()
    return _EXTENSION_MAP.get(ext, UploadType.FILE)


async def _upload_bytes(
    bot: Any,
    data: bytes,
    filename: str,
    upload_type: UploadType,
) -> str:
    """Выполнить двухэтапную загрузку bytes в Max API.

    Шаг 1: ``bot.get_upload_url(type_)`` → URL.
    Шаг 2: ``POST <url>`` multipart → token.

    Returns:
        Upload token для использования в attachments.
    """
    # Шаг 1: получить URL для загрузки
    endpoint = await bot.get_upload_url(upload_type)
    upload_url: str = endpoint.url

    # Шаг 2: загрузить файл по URL
    session: aiohttp.ClientSession = await bot.session._get_session()

    form = aiohttp.FormData()
    form.add_field(
        "data",
        data,
        filename=filename,
        content_type="application/octet-stream",
    )

    async with session.post(upload_url, data=form) as response:
        result = await response.json()

    token: str = result["token"]
    return token


class MaxInputFile(ABC):
    """Абстрактный базовый класс для загрузки файлов в Max API.

    Все конкретные реализации должны реализовать :meth:`upload`,
    который возвращает upload token.
    """

    @abstractmethod
    async def upload(self, bot: Any) -> str:
        """Загрузить файл и вернуть upload token.

        Args:
            bot: Экземпляр :class:`Bot`.

        Returns:
            Upload token для использования в attachments.
        """
        ...

    @property
    @abstractmethod
    def filename(self) -> str | None:
        """Имя файла."""
        ...

    @property
    @abstractmethod
    def upload_type(self) -> UploadType:
        """Тип загрузки."""
        ...


class BufferedInputFile(MaxInputFile):
    """Загрузка файла из bytes в памяти.

    Args:
        data: Бинарные данные файла.
        filename: Имя файла (по умолчанию ``"file"``).
        upload_type: Тип загрузки (автоопределение по расширению, если не указан).
    """

    def __init__(
        self,
        data: bytes,
        filename: str = "file",
        upload_type: UploadType | None = None,
    ) -> None:
        self._data = data
        self._filename = filename
        self._upload_type = upload_type or _detect_upload_type(filename)

    @property
    def filename(self) -> str:
        """Имя файла."""
        return self._filename

    @property
    def upload_type(self) -> UploadType:
        """Тип загрузки."""
        return self._upload_type

    async def read(self) -> bytes:
        """Прочитать данные.

        Returns:
            Копия бинарных данных.
        """
        return self._data

    async def upload(self, bot: Any) -> str:
        """Загрузить данные из памяти в Max API."""
        data = await self.read()
        return await _upload_bytes(bot, data, self._filename, self._upload_type)

    @classmethod
    def from_text(
        cls,
        text: str,
        filename: str = "text.txt",
        encoding: str = "utf-8",
    ) -> BufferedInputFile:
        """Создать из текстовой строки.

        Args:
            text: Текст для загрузки.
            filename: Имя файла.
            encoding: Кодировка.
        """
        return cls(text.encode(encoding), filename=filename)


class FSInputFile(MaxInputFile):
    """Загрузка файла с диска.

    Args:
        path: Путь к файлу (строка или Path).
        filename: Имя файла (по умолчанию из пути).
        upload_type: Тип загрузки (автоопределение по расширению, если не указан).

    Raises:
        FileNotFoundError: Если файл не существует.
    """

    def __init__(
        self,
        path: str | Path,
        filename: str | None = None,
        upload_type: UploadType | None = None,
    ) -> None:
        self._path = Path(path)
        if not self._path.exists():
            msg = f"File not found: {self._path}"
            raise FileNotFoundError(msg)
        self._filename = filename or self._path.name
        self._upload_type = upload_type or _detect_upload_type(self._filename)

    @property
    def path(self) -> Path:
        """Путь к файлу."""
        return self._path

    @property
    def filename(self) -> str:
        """Имя файла."""
        return self._filename

    @property
    def upload_type(self) -> UploadType:
        """Тип загрузки."""
        return self._upload_type

    async def read(self) -> bytes:
        """Прочитать содержимое файла.

        Returns:
            Бинарное содержимое файла.
        """
        return self._path.read_bytes()

    async def upload(self, bot: Any) -> str:
        """Загрузить файл с диска в Max API."""
        data = await self.read()
        return await _upload_bytes(bot, data, self._filename, self._upload_type)


class URLInputFile(MaxInputFile):
    """Скачивание файла по URL и загрузка в Max API.

    Args:
        url: URL файла для скачивания.
        filename: Имя файла (по умолчанию извлекается из URL).
        upload_type: Тип загрузки (автоопределение по расширению, если не указан).
        headers: HTTP-заголовки для запроса скачивания.
        timeout: Таймаут скачивания в секундах.
    """

    def __init__(
        self,
        url: str,
        filename: str | None = None,
        upload_type: UploadType | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._url = url
        self._filename = filename or self._extract_filename(url)
        self._upload_type = upload_type or _detect_upload_type(self._filename)
        self._headers = headers
        self._timeout = timeout

    @staticmethod
    def _extract_filename(url: str) -> str:
        """Извлечь имя файла из URL."""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        if path:
            name = Path(path).name
            if name and "." in name:
                return name
        return "file"

    @property
    def url(self) -> str:
        """URL для скачивания."""
        return self._url

    @property
    def filename(self) -> str:
        """Имя файла."""
        return self._filename

    @property
    def upload_type(self) -> UploadType:
        """Тип загрузки."""
        return self._upload_type

    @property
    def headers(self) -> dict[str, str] | None:
        """HTTP-заголовки для скачивания."""
        return self._headers

    @property
    def timeout(self) -> float:
        """Таймаут скачивания."""
        return self._timeout

    async def read(self, bot: Any) -> bytes:
        """Скачать файл по URL.

        Args:
            bot: Экземпляр Bot (для использования HTTP-сессии).

        Returns:
            Бинарное содержимое файла.
        """
        session: aiohttp.ClientSession = await bot.session._get_session()
        request_timeout = aiohttp.ClientTimeout(total=self._timeout)
        async with session.get(
            self._url,
            headers=self._headers,
            timeout=request_timeout,
        ) as response:
            return await response.read()

    async def upload(self, bot: Any) -> str:
        """Скачать файл по URL и загрузить в Max API."""
        data = await self.read(bot)
        return await _upload_bytes(bot, data, self._filename, self._upload_type)


class TokenInputFile(MaxInputFile):
    """Переиспользование ранее загруженного файла по upload token.

    Не выполняет HTTP-запросов — просто хранит token.

    Args:
        token: Upload token ранее загруженного файла.
    """

    def __init__(self, token: str) -> None:
        self._token = token

    @property
    def token(self) -> str:
        """Upload token."""
        return self._token

    @property
    def filename(self) -> None:
        """TokenInputFile не имеет файла — возвращает None."""
        return None

    @property
    def upload_type(self) -> UploadType:
        """Тип загрузки (не используется, но для совместимости)."""
        return UploadType.FILE

    async def upload(self, bot: Any) -> str:
        """Вернуть существующий token без HTTP-запросов."""
        return self._token
