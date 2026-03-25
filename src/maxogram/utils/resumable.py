"""Resumable Upload — chunked загрузка больших файлов (до 4 GB) в Max API.

Max API поддерживает загрузку файлов чанками с использованием заголовка
``Content-Range``. Это позволяет:

- Загружать файлы до 4 GB (vs 2 GB для обычного multipart)
- Возобновлять загрузку после сетевых сбоев (resume)
- Отслеживать прогресс через callback

Классы:

- :class:`ResumableUpload` — низкоуровневое управление chunked upload
- :class:`ResumableInputFile` — :class:`MaxInputFile` для больших файлов с диска,
  автоматически выбирает chunked или обычную загрузку по threshold
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from maxogram.enums import UploadType
from maxogram.exceptions import MaxAPIError
from maxogram.utils.media import MaxInputFile, _detect_upload_type, _upload_bytes

__all__ = [
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_THRESHOLD",
    "ResumableInputFile",
    "ResumableUpload",
]

#: Размер чанка по умолчанию: 5 MB
DEFAULT_CHUNK_SIZE: int = 5 * 1024 * 1024

#: Порог для автоматического перехода на chunked upload: 10 MB
DEFAULT_THRESHOLD: int = 10 * 1024 * 1024


class ResumableUpload:
    """Управление chunked upload файла в Max API.

    Разбивает данные на чанки и отправляет последовательно с заголовком
    ``Content-Range``. Поддерживает resume — при повторном вызове
    :meth:`upload` продолжает с места обрыва.

    Args:
        upload_url: URL для загрузки (получен от ``bot.get_upload_url``).
        total_size: Общий размер файла в байтах (> 0).
        chunk_size: Размер одного чанка в байтах (по умолчанию 5 MB).
        on_progress: Callback ``(sent_bytes, total_bytes) -> None``.

    Raises:
        ValueError: Если ``total_size <= 0`` или ``chunk_size <= 0``.
    """

    def __init__(
        self,
        upload_url: str,
        total_size: int,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        on_progress: Any | None = None,
    ) -> None:
        if total_size <= 0:
            msg = f"total_size must be positive, got {total_size}"
            raise ValueError(msg)
        if chunk_size <= 0:
            msg = f"chunk_size must be positive, got {chunk_size}"
            raise ValueError(msg)

        self._upload_url = upload_url
        self._total_size = total_size
        self._chunk_size = chunk_size
        self._on_progress = on_progress
        self._bytes_sent = 0

    @property
    def upload_url(self) -> str:
        """URL для загрузки."""
        return self._upload_url

    @property
    def total_size(self) -> int:
        """Общий размер файла."""
        return self._total_size

    @property
    def chunk_size(self) -> int:
        """Размер одного чанка."""
        return self._chunk_size

    @property
    def bytes_sent(self) -> int:
        """Количество отправленных байт."""
        return self._bytes_sent

    @property
    def is_complete(self) -> bool:
        """Загрузка завершена."""
        return self._bytes_sent >= self._total_size

    @property
    def progress(self) -> float:
        """Прогресс загрузки от 0.0 до 1.0."""
        if self._total_size == 0:
            return 1.0
        return self._bytes_sent / self._total_size

    async def _send_chunk(
        self,
        session: Any,
        chunk: bytes,
        offset: int,
        end: int,
    ) -> dict[str, Any]:
        """Отправить один чанк на upload_url.

        Args:
            session: aiohttp ClientSession.
            chunk: Данные чанка.
            offset: Начальная позиция в файле.
            end: Конечная позиция (exclusive) в файле.

        Returns:
            JSON-ответ сервера.

        Raises:
            MaxAPIError: При HTTP-ошибке.
        """
        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Range": f"bytes {offset}-{end - 1}/{self._total_size}",
        }

        async with session.post(
            self._upload_url,
            data=chunk,
            headers=headers,
        ) as response:
            result: dict[str, Any] = await response.json()
            status = response.status

            if status >= 400:
                raise MaxAPIError(
                    status_code=status,
                    error=result.get("error"),
                    error_message=result.get("message", f"Upload failed: HTTP {status}"),
                )

        return result

    async def upload(self, bot: Any, data: bytes) -> str:
        """Выполнить или продолжить chunked upload.

        При первом вызове загружает все чанки. При повторном вызове
        (после сбоя) продолжает с позиции ``bytes_sent``.

        Args:
            bot: Экземпляр Bot.
            data: Полные данные файла.

        Returns:
            Upload token (из ответа последнего чанка).

        Raises:
            MaxAPIError: При ошибке HTTP-запроса.
        """
        session: Any = await bot.session._get_session()

        offset = self._bytes_sent
        token: str = ""

        while offset < self._total_size:
            end = min(offset + self._chunk_size, self._total_size)
            chunk = data[offset:end]

            result = await self._send_chunk(session, chunk, offset, end)

            self._bytes_sent = end
            offset = end

            if self._on_progress is not None:
                self._on_progress(self._bytes_sent, self._total_size)

            # Последний чанк содержит token
            if "token" in result:
                token = result["token"]

        return token


class ResumableInputFile(MaxInputFile):
    """Загрузка больших файлов с диска — автоматический выбор стратегии.

    Если файл меньше ``threshold`` — обычная multipart загрузка.
    Если файл >= ``threshold`` — chunked upload через :class:`ResumableUpload`.

    Args:
        path: Путь к файлу (строка или Path).
        filename: Имя файла (по умолчанию из пути).
        upload_type: Тип загрузки (автоопределение по расширению).
        chunk_size: Размер чанка (по умолчанию 5 MB).
        threshold: Порог для перехода на chunked upload (по умолчанию 10 MB).
        on_progress: Callback ``(sent_bytes, total_bytes) -> None``.

    Raises:
        FileNotFoundError: Если файл не существует.
    """

    def __init__(
        self,
        path: str | Path,
        filename: str | None = None,
        upload_type: UploadType | None = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        threshold: int = DEFAULT_THRESHOLD,
        on_progress: Any | None = None,
    ) -> None:
        self._path = Path(path)
        if not self._path.exists():
            msg = f"File not found: {self._path}"
            raise FileNotFoundError(msg)
        self._filename = filename or self._path.name
        self._upload_type = upload_type or _detect_upload_type(self._filename)
        self._chunk_size = chunk_size
        self._threshold = threshold
        self._on_progress = on_progress
        self._file_size = self._path.stat().st_size

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

    @property
    def chunk_size(self) -> int:
        """Размер одного чанка."""
        return self._chunk_size

    @property
    def threshold(self) -> int:
        """Порог для перехода на chunked upload."""
        return self._threshold

    @property
    def file_size(self) -> int:
        """Размер файла в байтах."""
        return self._file_size

    async def upload(self, bot: Any) -> str:
        """Загрузить файл в Max API.

        Автоматически выбирает стратегию:
        - < threshold: обычная multipart загрузка
        - >= threshold: chunked upload с Content-Range

        Args:
            bot: Экземпляр Bot.

        Returns:
            Upload token для использования в attachments.
        """
        data = self._path.read_bytes()

        if self._file_size < self._threshold:
            # Обычная multipart загрузка
            return await _upload_bytes(bot, data, self._filename, self._upload_type)

        # Chunked upload
        endpoint = await bot.get_upload_url(self._upload_type)
        upload_url: str = endpoint.url

        ru = ResumableUpload(
            upload_url=upload_url,
            total_size=self._file_size,
            chunk_size=self._chunk_size,
            on_progress=self._on_progress,
        )
        return await ru.upload(bot, data)
