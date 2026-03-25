"""Тесты ResumableUpload и ResumableInputFile — chunked загрузка больших файлов."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from maxogram.enums import UploadType
from maxogram.utils.resumable import (
    DEFAULT_CHUNK_SIZE,
    ResumableInputFile,
    ResumableUpload,
)

if TYPE_CHECKING:
    from pathlib import Path


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
    mock_session = MagicMock()
    bot.session._get_session = AsyncMock(return_value=mock_session)
    bot.token = "test_bot_token"

    return bot


def _make_response(
    status: int = 200,
    json_data: dict[str, Any] | None = None,
) -> MagicMock:
    """Создать mock HTTP-ответа (aiohttp-like)."""
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})
    return resp


def _make_async_cm(response: MagicMock) -> MagicMock:
    """Обернуть mock response в async context manager (aiohttp-style)."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _setup_chunked_responses(
    bot: Any,
    num_chunks: int,
    final_token: str = "uploaded_token_chunked",
) -> None:
    """Настроить mock-ответы для chunked upload.

    Промежуточные чанки возвращают 200 без token,
    последний чанк возвращает 200 с token.
    """
    context_managers = []
    for i in range(num_chunks):
        if i == num_chunks - 1:
            resp = _make_response(json_data={"token": final_token})
        else:
            resp = _make_response()
        context_managers.append(_make_async_cm(resp))

    session = bot.session._get_session.return_value
    session.post = MagicMock(side_effect=context_managers)


def _setup_multipart_response(
    bot: Any,
    token: str = "uploaded_token_123",
) -> None:
    """Настроить mock-ответ для обычной multipart загрузки."""
    resp = _make_response(json_data={"token": token})

    session = bot.session._get_session.return_value
    session.post = MagicMock(return_value=_make_async_cm(resp))


# ---------------------------------------------------------------------------
# ResumableUpload — управление chunked загрузкой
# ---------------------------------------------------------------------------


class TestResumableUpload:
    """ResumableUpload — класс для управления chunked upload."""

    def test_create_default_chunk_size(self) -> None:
        """Создание с размером чанка по умолчанию."""
        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=10 * 1024 * 1024,
        )
        assert ru.chunk_size == DEFAULT_CHUNK_SIZE
        assert ru.total_size == 10 * 1024 * 1024
        assert ru.bytes_sent == 0

    def test_create_custom_chunk_size(self) -> None:
        """Создание с кастомным размером чанка."""
        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=10 * 1024 * 1024,
            chunk_size=1024 * 1024,  # 1 MB
        )
        assert ru.chunk_size == 1024 * 1024

    def test_is_complete_initially_false(self) -> None:
        """Изначально загрузка не завершена."""
        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=1000,
        )
        assert ru.is_complete is False

    def test_progress_initially_zero(self) -> None:
        """Прогресс изначально 0.0."""
        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=1000,
        )
        assert ru.progress == 0.0

    async def test_upload_single_chunk(self) -> None:
        """Файл меньше chunk_size — один чанк."""
        bot = _make_bot()
        data = b"small file data"
        total = len(data)

        _setup_chunked_responses(bot, num_chunks=1, final_token="token_single")

        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=total,
        )
        token = await ru.upload(bot, data)

        assert token == "token_single"
        assert ru.is_complete is True
        assert ru.bytes_sent == total

    async def test_upload_multiple_chunks(self) -> None:
        """Файл разбивается на несколько чанков."""
        bot = _make_bot()
        chunk_size = 10
        data = b"a" * 25  # 25 bytes → 3 чанка (10, 10, 5)

        _setup_chunked_responses(bot, num_chunks=3, final_token="token_multi")

        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=len(data),
            chunk_size=chunk_size,
        )
        token = await ru.upload(bot, data)

        assert token == "token_multi"
        assert ru.is_complete is True
        assert ru.bytes_sent == 25

        # Проверяем что session.post вызван 3 раза
        session = (await bot.session._get_session()).post
        assert session.call_count == 3

    async def test_content_range_headers(self) -> None:
        """Проверка Content-Range заголовков в запросах."""
        bot = _make_bot(upload_url="https://upload.example.com/test")
        chunk_size = 10
        data = b"a" * 25  # 3 чанка: 0-9, 10-19, 20-24

        _setup_chunked_responses(bot, num_chunks=3)

        ru = ResumableUpload(
            upload_url="https://upload.example.com/test",
            total_size=25,
            chunk_size=chunk_size,
        )
        await ru.upload(bot, data)

        session = (await bot.session._get_session()).post
        calls = session.call_args_list

        # Проверяем заголовки каждого вызова
        assert calls[0].kwargs["headers"]["Content-Range"] == "bytes 0-9/25"
        assert calls[1].kwargs["headers"]["Content-Range"] == "bytes 10-19/25"
        assert calls[2].kwargs["headers"]["Content-Range"] == "bytes 20-24/25"

    async def test_content_type_octet_stream(self) -> None:
        """Content-Type должен быть application/octet-stream."""
        bot = _make_bot()
        data = b"test data"

        _setup_chunked_responses(bot, num_chunks=1)

        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=len(data),
        )
        await ru.upload(bot, data)

        session = (await bot.session._get_session()).post
        call_kwargs = session.call_args_list[0].kwargs
        assert call_kwargs["headers"]["Content-Type"] == "application/octet-stream"

    async def test_progress_callback(self) -> None:
        """Progress callback вызывается после каждого чанка."""
        bot = _make_bot()
        chunk_size = 10
        data = b"a" * 25

        _setup_chunked_responses(bot, num_chunks=3)

        progress_calls: list[tuple[int, int]] = []

        def on_progress(sent: int, total: int) -> None:
            progress_calls.append((sent, total))

        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=25,
            chunk_size=chunk_size,
            on_progress=on_progress,
        )
        await ru.upload(bot, data)

        assert progress_calls == [(10, 25), (20, 25), (25, 25)]

    async def test_progress_property_updates(self) -> None:
        """Свойство progress обновляется по ходу загрузки."""
        bot = _make_bot()
        data = b"a" * 20

        _setup_chunked_responses(bot, num_chunks=2)

        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=20,
            chunk_size=10,
        )
        assert ru.progress == 0.0

        await ru.upload(bot, data)
        assert ru.progress == 1.0

    async def test_exact_chunk_boundary(self) -> None:
        """Файл точно делится на чанки без остатка."""
        bot = _make_bot()
        chunk_size = 10
        data = b"a" * 30  # 3 чанка по 10

        _setup_chunked_responses(bot, num_chunks=3, final_token="token_exact")

        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=30,
            chunk_size=chunk_size,
        )
        token = await ru.upload(bot, data)

        assert token == "token_exact"

        session = (await bot.session._get_session()).post
        assert session.call_count == 3

    async def test_one_byte_file(self) -> None:
        """Файл из одного байта — один чанк."""
        bot = _make_bot()
        data = b"x"

        _setup_chunked_responses(bot, num_chunks=1, final_token="token_one")

        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=1,
        )
        token = await ru.upload(bot, data)

        assert token == "token_one"
        assert ru.bytes_sent == 1

    async def test_upload_url_used(self) -> None:
        """Запросы отправляются на правильный upload_url."""
        bot = _make_bot()
        data = b"test"

        _setup_chunked_responses(bot, num_chunks=1)

        ru = ResumableUpload(
            upload_url="https://upload.example.com/specific-path",
            total_size=len(data),
        )
        await ru.upload(bot, data)

        session = (await bot.session._get_session()).post
        assert session.call_args_list[0].args[0] == "https://upload.example.com/specific-path"


# ---------------------------------------------------------------------------
# ResumableUpload — resume после обрыва
# ---------------------------------------------------------------------------


class TestResumableUploadResume:
    """Resume — продолжение загрузки после обрыва."""

    async def test_resume_after_partial_upload(self) -> None:
        """Возобновление с позиции, на которой остановились."""
        bot = _make_bot()
        chunk_size = 10
        data = b"a" * 25

        # Первый upload: 2 чанка отправлены, 3-й падает
        session = bot.session._get_session.return_value
        session.post = MagicMock(
            side_effect=[
                _make_async_cm(_make_response()),
                _make_async_cm(_make_response()),
                _make_async_cm(_make_response(status=500, json_data={"error": "server error"})),
            ]
        )

        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=25,
            chunk_size=chunk_size,
        )

        with pytest.raises(Exception):  # noqa: B017
            await ru.upload(bot, data)

        # Загружено 20 из 25 байт
        assert ru.bytes_sent == 20
        assert ru.is_complete is False

        # Resume — отправляем оставшийся чанк
        session.post = MagicMock(
            side_effect=[
                _make_async_cm(_make_response(json_data={"token": "token_resumed"})),
            ]
        )

        token = await ru.upload(bot, data)

        assert token == "token_resumed"
        assert ru.is_complete is True
        assert ru.bytes_sent == 25

        # Последний запрос должен иметь правильный Content-Range
        last_call = session.post.call_args_list[0]
        assert last_call.kwargs["headers"]["Content-Range"] == "bytes 20-24/25"

    async def test_resume_bytes_sent_preserved(self) -> None:
        """bytes_sent сохраняется между вызовами upload."""
        bot = _make_bot()
        data = b"a" * 20

        # Первый чанк OK, второй fail
        session = bot.session._get_session.return_value
        session.post = MagicMock(
            side_effect=[
                _make_async_cm(_make_response()),
                _make_async_cm(_make_response(status=500)),
            ]
        )

        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=20,
            chunk_size=10,
        )

        with pytest.raises(Exception):  # noqa: B017
            await ru.upload(bot, data)

        assert ru.bytes_sent == 10


# ---------------------------------------------------------------------------
# ResumableInputFile — наследник MaxInputFile
# ---------------------------------------------------------------------------


class TestResumableInputFile:
    """ResumableInputFile — загрузка больших файлов с диска."""

    def test_create(self, tmp_path: Path) -> None:
        """Создание из файла на диске."""
        filepath = tmp_path / "big_video.mp4"
        filepath.write_bytes(b"\x00" * 100)
        f = ResumableInputFile(filepath)
        assert f.filename == "big_video.mp4"
        assert f.upload_type == UploadType.VIDEO

    def test_custom_filename(self, tmp_path: Path) -> None:
        """Кастомное имя файла."""
        filepath = tmp_path / "original.bin"
        filepath.write_bytes(b"\x00" * 50)
        f = ResumableInputFile(filepath, filename="custom.dat")
        assert f.filename == "custom.dat"

    def test_custom_upload_type(self, tmp_path: Path) -> None:
        """Кастомный upload_type."""
        filepath = tmp_path / "file.dat"
        filepath.write_bytes(b"\x00" * 50)
        f = ResumableInputFile(filepath, upload_type=UploadType.VIDEO)
        assert f.upload_type == UploadType.VIDEO

    def test_custom_chunk_size(self, tmp_path: Path) -> None:
        """Кастомный размер чанка."""
        filepath = tmp_path / "file.bin"
        filepath.write_bytes(b"\x00" * 50)
        f = ResumableInputFile(filepath, chunk_size=1024)
        assert f.chunk_size == 1024

    def test_file_not_found(self) -> None:
        """Несуществующий файл — ошибка при создании."""
        with pytest.raises(FileNotFoundError):
            ResumableInputFile("/nonexistent/path/file.bin")

    def test_file_size(self, tmp_path: Path) -> None:
        """file_size возвращает размер файла."""
        filepath = tmp_path / "test.bin"
        data = b"\x00" * 12345
        filepath.write_bytes(data)
        f = ResumableInputFile(filepath)
        assert f.file_size == 12345

    def test_path_property(self, tmp_path: Path) -> None:
        """path возвращает Path объект."""
        filepath = tmp_path / "test.bin"
        filepath.write_bytes(b"\x00")
        f = ResumableInputFile(filepath)
        assert f.path == filepath

    async def test_small_file_uses_multipart(self, tmp_path: Path) -> None:
        """Маленький файл (< threshold) загружается через обычный multipart."""
        filepath = tmp_path / "small.jpg"
        filepath.write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)

        bot = _make_bot()
        _setup_multipart_response(bot, token="token_small_multipart")

        f = ResumableInputFile(filepath, threshold=1000)
        token = await f.upload(bot)

        assert token == "token_small_multipart"
        # При multipart — вызывается get_upload_url
        bot.get_upload_url.assert_awaited_once()

    async def test_large_file_uses_chunked(self, tmp_path: Path) -> None:
        """Большой файл (>= threshold) загружается через chunked upload."""
        filepath = tmp_path / "big.mp4"
        data = b"\x00" * 50
        filepath.write_bytes(data)

        bot = _make_bot()
        # 50 bytes, chunk_size=20 → 3 чанка
        _setup_chunked_responses(bot, num_chunks=3, final_token="token_chunked")

        f = ResumableInputFile(filepath, chunk_size=20, threshold=30)
        token = await f.upload(bot)

        assert token == "token_chunked"
        # При chunked upload тоже нужен upload_url
        bot.get_upload_url.assert_awaited_once()

    async def test_progress_callback_forwarded(self, tmp_path: Path) -> None:
        """Progress callback пробрасывается в ResumableUpload."""
        filepath = tmp_path / "big.bin"
        data = b"\x00" * 30
        filepath.write_bytes(data)

        bot = _make_bot()
        _setup_chunked_responses(bot, num_chunks=3)

        progress_calls: list[tuple[int, int]] = []

        def on_progress(sent: int, total: int) -> None:
            progress_calls.append((sent, total))

        f = ResumableInputFile(filepath, chunk_size=10, threshold=20, on_progress=on_progress)
        await f.upload(bot)

        assert len(progress_calls) == 3
        assert progress_calls[-1] == (30, 30)

    async def test_threshold_boundary_equal(self, tmp_path: Path) -> None:
        """Файл размером ровно threshold — chunked upload."""
        filepath = tmp_path / "exact.bin"
        data = b"\x00" * 100
        filepath.write_bytes(data)

        bot = _make_bot()
        # 100 bytes, chunk_size=50 → 2 чанка
        _setup_chunked_responses(bot, num_chunks=2, final_token="token_boundary")

        f = ResumableInputFile(filepath, chunk_size=50, threshold=100)
        token = await f.upload(bot)

        assert token == "token_boundary"

    def test_default_threshold(self, tmp_path: Path) -> None:
        """Threshold по умолчанию — 10 MB."""
        filepath = tmp_path / "test.bin"
        filepath.write_bytes(b"\x00")
        f = ResumableInputFile(filepath)
        assert f.threshold == 10 * 1024 * 1024

    def test_is_subclass_of_max_input_file(self) -> None:
        """ResumableInputFile — наследник MaxInputFile."""
        from maxogram.utils.media import MaxInputFile

        assert issubclass(ResumableInputFile, MaxInputFile)


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestResumableEdgeCases:
    """Граничные случаи resumable upload."""

    async def test_empty_file_chunked(self, tmp_path: Path) -> None:
        """Пустой файл — всё равно multipart (< threshold)."""
        filepath = tmp_path / "empty.bin"
        filepath.write_bytes(b"")

        bot = _make_bot()
        _setup_multipart_response(bot, token="token_empty")

        f = ResumableInputFile(filepath, threshold=10)
        token = await f.upload(bot)
        assert token == "token_empty"

    async def test_chunk_size_larger_than_file(self) -> None:
        """chunk_size больше файла — один чанк."""
        bot = _make_bot()
        data = b"small"

        _setup_chunked_responses(bot, num_chunks=1, final_token="token_big_chunk")

        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=len(data),
            chunk_size=1024 * 1024,  # 1 MB chunk для 5 bytes
        )
        token = await ru.upload(bot, data)

        assert token == "token_big_chunk"
        session = (await bot.session._get_session()).post
        assert session.call_count == 1

    async def test_resumable_upload_zero_size_raises(self) -> None:
        """ResumableUpload с total_size=0 — ValueError."""
        with pytest.raises(ValueError, match="total_size"):
            ResumableUpload(
                upload_url="https://upload.example.com/abc",
                total_size=0,
            )

    async def test_resumable_upload_negative_size_raises(self) -> None:
        """ResumableUpload с отрицательным total_size — ValueError."""
        with pytest.raises(ValueError, match="total_size"):
            ResumableUpload(
                upload_url="https://upload.example.com/abc",
                total_size=-1,
            )

    async def test_chunk_size_zero_raises(self) -> None:
        """chunk_size=0 — ValueError."""
        with pytest.raises(ValueError, match="chunk_size"):
            ResumableUpload(
                upload_url="https://upload.example.com/abc",
                total_size=100,
                chunk_size=0,
            )

    async def test_chunk_size_negative_raises(self) -> None:
        """chunk_size отрицательный — ValueError."""
        with pytest.raises(ValueError, match="chunk_size"):
            ResumableUpload(
                upload_url="https://upload.example.com/abc",
                total_size=100,
                chunk_size=-1,
            )

    async def test_no_progress_callback(self) -> None:
        """Без progress callback — работает без ошибок."""
        bot = _make_bot()
        data = b"test"
        _setup_chunked_responses(bot, num_chunks=1, final_token="token_no_cb")

        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=len(data),
        )
        token = await ru.upload(bot, data)
        assert token == "token_no_cb"

    async def test_upload_error_raises(self) -> None:
        """HTTP-ошибка при загрузке чанка — пробрасывается."""
        bot = _make_bot()
        data = b"test data"

        session = bot.session._get_session.return_value
        resp_500 = _make_response(
            status=500,
            json_data={"error": "Internal Server Error"},
        )
        session.post = MagicMock(side_effect=[_make_async_cm(resp_500)])

        ru = ResumableUpload(
            upload_url="https://upload.example.com/abc",
            total_size=len(data),
        )
        with pytest.raises(Exception):  # noqa: B017
            await ru.upload(bot, data)
