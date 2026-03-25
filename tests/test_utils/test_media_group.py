"""Тесты MediaGroupBuilder."""

from __future__ import annotations

import pytest

from maxogram.types.attachment import (
    AudioAttachmentRequest,
    FileAttachmentRequest,
    PhotoAttachmentRequest,
    VideoAttachmentRequest,
)
from maxogram.utils.media_group import MediaGroupBuilder


class TestAddPhoto:
    """Добавление фото через add_photo()."""

    def test_add_photo_by_token(self) -> None:
        """Фото по upload token."""
        builder = MediaGroupBuilder()
        builder.add_photo(token="tok_photo_1")
        result = builder.build()
        assert len(result) == 1
        att = result[0]
        assert isinstance(att, PhotoAttachmentRequest)
        assert att.type == "image"
        assert att.payload.token == "tok_photo_1"

    def test_add_photo_by_url(self) -> None:
        """Фото по URL."""
        builder = MediaGroupBuilder()
        builder.add_photo(url="https://example.com/photo.jpg")
        result = builder.build()
        assert len(result) == 1
        att = result[0]
        assert isinstance(att, PhotoAttachmentRequest)
        assert att.payload.url == "https://example.com/photo.jpg"
        assert att.payload.token is None

    def test_add_photo_no_source_raises(self) -> None:
        """Ошибка, если не указан ни token, ни url."""
        builder = MediaGroupBuilder()
        with pytest.raises(ValueError, match="token.*url"):
            builder.add_photo()

    def test_add_photo_both_sources_raises(self) -> None:
        """Ошибка, если указаны и token, и url одновременно."""
        builder = MediaGroupBuilder()
        with pytest.raises(ValueError, match="token.*url"):
            builder.add_photo(token="tok", url="https://x.com/img.jpg")


class TestAddVideo:
    """Добавление видео через add_video()."""

    def test_add_video_by_token(self) -> None:
        """Видео по upload token."""
        builder = MediaGroupBuilder()
        builder.add_video(token="tok_video_1")
        result = builder.build()
        assert len(result) == 1
        att = result[0]
        assert isinstance(att, VideoAttachmentRequest)
        assert att.type == "video"
        assert att.payload.token == "tok_video_1"

    def test_add_video_no_token_raises(self) -> None:
        """Видео требует token."""
        builder = MediaGroupBuilder()
        with pytest.raises(ValueError, match="token"):
            builder.add_video()


class TestAddAudio:
    """Добавление аудио через add_audio()."""

    def test_add_audio_by_token(self) -> None:
        """Аудио по upload token."""
        builder = MediaGroupBuilder()
        builder.add_audio(token="tok_audio_1")
        result = builder.build()
        assert len(result) == 1
        att = result[0]
        assert isinstance(att, AudioAttachmentRequest)
        assert att.type == "audio"
        assert att.payload.token == "tok_audio_1"

    def test_add_audio_no_token_raises(self) -> None:
        """Аудио требует token."""
        builder = MediaGroupBuilder()
        with pytest.raises(ValueError, match="token"):
            builder.add_audio()


class TestAddFile:
    """Добавление файла через add_file()."""

    def test_add_file_by_token(self) -> None:
        """Файл по upload token."""
        builder = MediaGroupBuilder()
        builder.add_file(token="tok_file_1")
        result = builder.build()
        assert len(result) == 1
        att = result[0]
        assert isinstance(att, FileAttachmentRequest)
        assert att.type == "file"
        assert att.payload.token == "tok_file_1"

    def test_add_file_no_token_raises(self) -> None:
        """Файл требует token."""
        builder = MediaGroupBuilder()
        with pytest.raises(ValueError, match="token"):
            builder.add_file()


class TestAddGeneric:
    """Добавление готового AttachmentRequest через add()."""

    def test_add_ready_attachment(self) -> None:
        """Добавить готовый AttachmentRequest."""
        from maxogram.types.attachment import UploadedInfo

        att = VideoAttachmentRequest(payload=UploadedInfo(token="ready_tok"))
        builder = MediaGroupBuilder()
        builder.add(att)
        result = builder.build()
        assert len(result) == 1
        assert result[0] is att


class TestFluentAPI:
    """Fluent API — цепочки вызовов."""

    def test_chaining(self) -> None:
        """Методы возвращают self для цепочки."""
        builder = MediaGroupBuilder()
        result = (
            builder.add_photo(token="p1")
            .add_video(token="v1")
            .add_audio(token="a1")
            .add_file(token="f1")
        )
        assert result is builder
        attachments = builder.build()
        assert len(attachments) == 4

    def test_add_returns_self(self) -> None:
        """add() возвращает self."""
        from maxogram.types.attachment import UploadedInfo

        builder = MediaGroupBuilder()
        att = AudioAttachmentRequest(payload=UploadedInfo(token="t"))
        result = builder.add(att)
        assert result is builder


class TestBuild:
    """Метод build()."""

    def test_empty_build(self) -> None:
        """build() без добавлений — пустой список."""
        builder = MediaGroupBuilder()
        assert builder.build() == []

    def test_multiple_photos(self) -> None:
        """Несколько фото."""
        builder = MediaGroupBuilder()
        builder.add_photo(token="p1")
        builder.add_photo(token="p2")
        builder.add_photo(url="https://example.com/3.jpg")
        result = builder.build()
        assert len(result) == 3
        assert all(isinstance(a, PhotoAttachmentRequest) for a in result)

    def test_mixed_media(self) -> None:
        """Смешанные типы медиа."""
        builder = MediaGroupBuilder()
        builder.add_photo(token="p1")
        builder.add_video(token="v1")
        builder.add_audio(token="a1")
        builder.add_file(token="f1")
        result = builder.build()
        assert len(result) == 4
        assert isinstance(result[0], PhotoAttachmentRequest)
        assert isinstance(result[1], VideoAttachmentRequest)
        assert isinstance(result[2], AudioAttachmentRequest)
        assert isinstance(result[3], FileAttachmentRequest)

    def test_build_preserves_order(self) -> None:
        """build() сохраняет порядок добавления."""
        builder = MediaGroupBuilder()
        builder.add_video(token="v1")
        builder.add_photo(token="p1")
        builder.add_file(token="f1")
        result = builder.build()
        assert isinstance(result[0], VideoAttachmentRequest)
        assert isinstance(result[1], PhotoAttachmentRequest)
        assert isinstance(result[2], FileAttachmentRequest)

    def test_build_returns_copy(self) -> None:
        """build() возвращает копию, не внутренний список."""
        builder = MediaGroupBuilder()
        builder.add_photo(token="p1")
        result1 = builder.build()
        result2 = builder.build()
        assert result1 == result2
        assert result1 is not result2

    def test_build_after_add_more(self) -> None:
        """Можно добавлять после build() и собирать снова."""
        builder = MediaGroupBuilder()
        builder.add_photo(token="p1")
        result1 = builder.build()
        assert len(result1) == 1

        builder.add_video(token="v1")
        result2 = builder.build()
        assert len(result2) == 2
