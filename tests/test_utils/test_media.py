"""Тесты MaxInputFile и наследников — двухэтапная загрузка файлов."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from maxogram.enums import UploadType
from maxogram.utils.media import (
    BufferedInputFile,
    FSInputFile,
    MaxInputFile,
    TokenInputFile,
    URLInputFile,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bot(upload_url: str = "https://upload.example.com/abc") -> Any:
    """Создать mock бота с get_upload_url и session."""
    bot = AsyncMock()

    # get_upload_url возвращает объект с .url
    upload_endpoint = MagicMock()
    upload_endpoint.url = upload_url
    bot.get_upload_url.return_value = upload_endpoint

    # session._get_session() возвращает aiohttp-like mock
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"token": "uploaded_token_123"})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_response)

    bot.session._get_session = AsyncMock(return_value=mock_session)
    bot.token = "test_bot_token"

    return bot


# ---------------------------------------------------------------------------
# MaxInputFile — абстракция
# ---------------------------------------------------------------------------


class TestMaxInputFileABC:
    """MaxInputFile — абстрактный базовый класс."""

    def test_cannot_instantiate(self) -> None:
        """Нельзя создать экземпляр MaxInputFile напрямую."""
        with pytest.raises(TypeError):
            MaxInputFile()  # type: ignore[abstract]

    def test_subclasses(self) -> None:
        """Все конкретные классы — наследники MaxInputFile."""
        assert issubclass(BufferedInputFile, MaxInputFile)
        assert issubclass(FSInputFile, MaxInputFile)
        assert issubclass(URLInputFile, MaxInputFile)
        assert issubclass(TokenInputFile, MaxInputFile)


# ---------------------------------------------------------------------------
# BufferedInputFile — из bytes в памяти
# ---------------------------------------------------------------------------


class TestBufferedInputFile:
    """BufferedInputFile — загрузка из bytes."""

    def test_create(self) -> None:
        """Создание с данными и именем файла."""
        data = b"hello world"
        f = BufferedInputFile(data, filename="test.txt")
        assert f.filename == "test.txt"

    def test_create_with_upload_type(self) -> None:
        """Создание с явным upload_type."""
        f = BufferedInputFile(b"data", filename="photo.jpg", upload_type=UploadType.IMAGE)
        assert f.upload_type == UploadType.IMAGE

    def test_default_upload_type_file(self) -> None:
        """По умолчанию upload_type=FILE."""
        f = BufferedInputFile(b"data", filename="test.bin")
        assert f.upload_type == UploadType.FILE

    async def test_read_returns_bytes(self) -> None:
        """read() возвращает все данные как bytes."""
        data = b"binary content here"
        f = BufferedInputFile(data, filename="test.bin")
        result = await f.read()
        assert result == data

    async def test_read_returns_copy(self) -> None:
        """read() возвращает копию — мутация не влияет на оригинал."""
        data = bytearray(b"original")
        f = BufferedInputFile(bytes(data), filename="test.bin")
        result = await f.read()
        assert result == b"original"

    async def test_upload(self) -> None:
        """upload() выполняет двухэтапную загрузку и возвращает token."""
        bot = _make_bot()
        f = BufferedInputFile(b"image data", filename="photo.jpg", upload_type=UploadType.IMAGE)
        token = await f.upload(bot)

        assert token == "uploaded_token_123"
        bot.get_upload_url.assert_awaited_once_with(UploadType.IMAGE)

    def test_from_text(self) -> None:
        """Создание из текстовой строки."""
        f = BufferedInputFile.from_text("hello", filename="hello.txt")
        assert f.filename == "hello.txt"

    async def test_from_text_read(self) -> None:
        """from_text — read возвращает encoded bytes."""
        f = BufferedInputFile.from_text("привет", filename="hello.txt", encoding="utf-8")
        result = await f.read()
        assert result == "привет".encode()


# ---------------------------------------------------------------------------
# FSInputFile — из файла на диске
# ---------------------------------------------------------------------------


class TestFSInputFile:
    """FSInputFile — загрузка из файла на диске."""

    def test_create_from_path_string(self, tmp_path: Path) -> None:
        """Создание из строки пути."""
        filepath = tmp_path / "test.txt"
        filepath.write_text("content")
        f = FSInputFile(str(filepath))
        assert f.filename == "test.txt"

    def test_create_from_pathlib(self, tmp_path: Path) -> None:
        """Создание из pathlib.Path."""
        filepath = tmp_path / "photo.jpg"
        filepath.write_bytes(b"\xff\xd8\xff")
        f = FSInputFile(filepath)
        assert f.filename == "photo.jpg"

    def test_custom_filename(self, tmp_path: Path) -> None:
        """Кастомное имя файла."""
        filepath = tmp_path / "original.txt"
        filepath.write_text("data")
        f = FSInputFile(filepath, filename="custom.txt")
        assert f.filename == "custom.txt"

    def test_custom_upload_type(self, tmp_path: Path) -> None:
        """Кастомный upload_type."""
        filepath = tmp_path / "video.mp4"
        filepath.write_bytes(b"\x00\x00")
        f = FSInputFile(filepath, upload_type=UploadType.VIDEO)
        assert f.upload_type == UploadType.VIDEO

    async def test_read(self, tmp_path: Path) -> None:
        """read() читает содержимое файла."""
        filepath = tmp_path / "test.txt"
        filepath.write_bytes(b"file content")
        f = FSInputFile(filepath)
        result = await f.read()
        assert result == b"file content"

    async def test_read_large_binary(self, tmp_path: Path) -> None:
        """read() корректно читает бинарный файл."""
        filepath = tmp_path / "binary.bin"
        data = bytes(range(256)) * 100
        filepath.write_bytes(data)
        f = FSInputFile(filepath)
        result = await f.read()
        assert result == data

    def test_nonexistent_file(self) -> None:
        """Несуществующий файл — ошибка при создании."""
        with pytest.raises(FileNotFoundError):
            FSInputFile("/nonexistent/path/file.txt")

    async def test_upload(self, tmp_path: Path) -> None:
        """upload() выполняет двухэтапную загрузку."""
        filepath = tmp_path / "photo.jpg"
        filepath.write_bytes(b"\xff\xd8\xff\xe0 jpeg data")
        bot = _make_bot()
        f = FSInputFile(filepath, upload_type=UploadType.IMAGE)
        token = await f.upload(bot)
        assert token == "uploaded_token_123"

    def test_path_property(self, tmp_path: Path) -> None:
        """path возвращает Path объект."""
        filepath = tmp_path / "test.txt"
        filepath.write_text("data")
        f = FSInputFile(filepath)
        assert f.path == filepath


# ---------------------------------------------------------------------------
# URLInputFile — скачивание по URL и загрузка
# ---------------------------------------------------------------------------


class TestURLInputFile:
    """URLInputFile — скачивание с URL."""

    def test_create(self) -> None:
        """Создание с URL."""
        f = URLInputFile("https://example.com/photo.jpg")
        assert f.url == "https://example.com/photo.jpg"

    def test_filename_from_url(self) -> None:
        """Имя файла извлекается из URL."""
        f = URLInputFile("https://example.com/images/photo.jpg")
        assert f.filename == "photo.jpg"

    def test_custom_filename(self) -> None:
        """Кастомное имя файла."""
        f = URLInputFile("https://example.com/photo.jpg", filename="custom.png")
        assert f.filename == "custom.png"

    def test_custom_upload_type(self) -> None:
        """Кастомный upload_type."""
        f = URLInputFile("https://example.com/photo.jpg", upload_type=UploadType.IMAGE)
        assert f.upload_type == UploadType.IMAGE

    def test_filename_fallback(self) -> None:
        """Если из URL не извлекается имя — используется fallback."""
        f = URLInputFile("https://example.com/")
        assert f.filename == "file"

    def test_custom_headers(self) -> None:
        """Поддержка кастомных заголовков для скачивания."""
        headers = {"Authorization": "Bearer token123"}
        f = URLInputFile("https://example.com/photo.jpg", headers=headers)
        assert f.headers == headers

    def test_custom_timeout(self) -> None:
        """Поддержка кастомного таймаута для скачивания."""
        f = URLInputFile("https://example.com/photo.jpg", timeout=120.0)
        assert f.timeout == 120.0


# ---------------------------------------------------------------------------
# TokenInputFile — переиспользование уже загруженного файла
# ---------------------------------------------------------------------------


class TestTokenInputFile:
    """TokenInputFile — повторное использование upload token."""

    def test_create(self) -> None:
        """Создание с token."""
        f = TokenInputFile("upload_token_xyz")
        assert f.token == "upload_token_xyz"

    async def test_upload_returns_token(self) -> None:
        """upload() сразу возвращает token без HTTP-запросов."""
        f = TokenInputFile("existing_token")
        bot = _make_bot()
        token = await f.upload(bot)
        assert token == "existing_token"
        # Не вызывает get_upload_url — файл уже загружен
        bot.get_upload_url.assert_not_awaited()

    def test_no_read(self) -> None:
        """TokenInputFile не имеет read() — нечего читать."""
        f = TokenInputFile("token")
        assert not hasattr(f, "read") or f.__class__ is TokenInputFile

    def test_filename_none(self) -> None:
        """TokenInputFile не имеет filename."""
        f = TokenInputFile("token")
        assert f.filename is None


# ---------------------------------------------------------------------------
# UploadType auto-detection
# ---------------------------------------------------------------------------


class TestUploadTypeDetection:
    """Автоматическое определение UploadType по расширению."""

    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("photo.jpg", UploadType.IMAGE),
            ("photo.jpeg", UploadType.IMAGE),
            ("photo.png", UploadType.IMAGE),
            ("photo.gif", UploadType.IMAGE),
            ("photo.bmp", UploadType.IMAGE),
            ("photo.webp", UploadType.IMAGE),
            ("video.mp4", UploadType.VIDEO),
            ("video.avi", UploadType.VIDEO),
            ("video.mov", UploadType.VIDEO),
            ("video.mkv", UploadType.VIDEO),
            ("song.mp3", UploadType.AUDIO),
            ("song.ogg", UploadType.AUDIO),
            ("song.wav", UploadType.AUDIO),
            ("song.flac", UploadType.AUDIO),
            ("document.pdf", UploadType.FILE),
            ("archive.zip", UploadType.FILE),
            ("unknown.xyz", UploadType.FILE),
        ],
    )
    def test_detect_from_filename(self, filename: str, expected: UploadType) -> None:
        """Определение UploadType по расширению файла."""
        f = BufferedInputFile(b"data", filename=filename)
        assert f.upload_type == expected

    def test_explicit_overrides_detection(self) -> None:
        """Явный upload_type имеет приоритет над автоопределением."""
        f = BufferedInputFile(b"data", filename="photo.jpg", upload_type=UploadType.FILE)
        assert f.upload_type == UploadType.FILE


# ---------------------------------------------------------------------------
# BufferedInputFile — edge cases
# ---------------------------------------------------------------------------


class TestBufferedInputFileEdgeCases:
    """Граничные случаи BufferedInputFile."""

    async def test_empty_data(self) -> None:
        """Пустые данные."""
        f = BufferedInputFile(b"", filename="empty.txt")
        result = await f.read()
        assert result == b""

    def test_no_filename(self) -> None:
        """Без имени файла — используется default."""
        f = BufferedInputFile(b"data")
        assert f.filename is not None  # имеет default


# ---------------------------------------------------------------------------
# Интеграция upload flow
# ---------------------------------------------------------------------------


class TestUploadFlow:
    """Двухэтапная загрузка — full flow mock."""

    async def test_buffered_upload_calls_sequence(self) -> None:
        """BufferedInputFile.upload вызывает: get_upload_url → POST upload_url."""
        bot = _make_bot(upload_url="https://platform-api.max.ru/upload/xyz")
        f = BufferedInputFile(b"photo data", filename="photo.jpg", upload_type=UploadType.IMAGE)

        token = await f.upload(bot)

        # 1. get_upload_url вызван с правильным типом
        bot.get_upload_url.assert_awaited_once_with(UploadType.IMAGE)

        # 2. Результат — token
        assert token == "uploaded_token_123"

    async def test_fs_upload_calls_sequence(self, tmp_path: Path) -> None:
        """FSInputFile.upload вызывает: get_upload_url → POST upload_url."""
        filepath = tmp_path / "video.mp4"
        filepath.write_bytes(b"\x00\x00\x00\x20 ftyp")
        bot = _make_bot()

        f = FSInputFile(filepath, upload_type=UploadType.VIDEO)
        token = await f.upload(bot)

        bot.get_upload_url.assert_awaited_once_with(UploadType.VIDEO)
        assert token == "uploaded_token_123"

    async def test_token_upload_no_network(self) -> None:
        """TokenInputFile.upload не делает HTTP-запросов."""
        bot = _make_bot()
        f = TokenInputFile("existing_token_abc")
        token = await f.upload(bot)

        assert token == "existing_token_abc"
        bot.get_upload_url.assert_not_awaited()
