"""Тесты ContentTypeFilter."""

from __future__ import annotations

import pytest

from maxogram.filters.base import Filter
from maxogram.filters.content_type import ContentType, ContentTypeFilter
from maxogram.types.attachment import (
    AudioAttachment,
    AudioAttachmentPayload,
    ContactAttachment,
    ContactAttachmentPayload,
    FileAttachment,
    FileAttachmentPayload,
    LocationAttachment,
    PhotoAttachment,
    PhotoAttachmentPayload,
    StickerAttachment,
    StickerAttachmentPayload,
    VideoAttachment,
    VideoAttachmentPayload,
)
from maxogram.types.message import Message, MessageBody, Recipient


def _make_message(
    text: str | None = None,
    attachments: list | None = None,
) -> Message:
    """Создать Message с заданным текстом и вложениями."""
    return Message(
        recipient=Recipient(chat_type="dialog"),  # type: ignore[arg-type]
        timestamp=1700000000000,
        body=MessageBody(mid="mid1", seq=1, text=text, attachments=attachments),
    )


def _photo_attachment() -> PhotoAttachment:
    return PhotoAttachment(payload=PhotoAttachmentPayload(url="http://x", token="t"))


def _video_attachment() -> VideoAttachment:
    return VideoAttachment(payload=VideoAttachmentPayload(url="http://x", token="t"))


def _audio_attachment() -> AudioAttachment:
    return AudioAttachment(payload=AudioAttachmentPayload(url="http://x", token="t"))


def _file_attachment() -> FileAttachment:
    return FileAttachment(
        payload=FileAttachmentPayload(url="http://x", token="t"),
        filename="doc.pdf",
        size=100,
    )


def _sticker_attachment() -> StickerAttachment:
    return StickerAttachment(
        payload=StickerAttachmentPayload(code="smile"),
        width=128,
        height=128,
    )


def _contact_attachment() -> ContactAttachment:
    return ContactAttachment(payload=ContactAttachmentPayload())


def _location_attachment() -> LocationAttachment:
    return LocationAttachment(latitude=55.75, longitude=37.62)


class _FakeUpdate:
    """Имитация update с вложенным message."""

    def __init__(self, message: Message) -> None:
        self.update_type = "message_created"
        self.message = message


class TestContentTypeEnum:
    """Тесты ContentType enum."""

    def test_text_value(self) -> None:
        assert ContentType.TEXT == "text"

    def test_image_value(self) -> None:
        assert ContentType.IMAGE == "image"

    def test_video_value(self) -> None:
        assert ContentType.VIDEO == "video"

    def test_audio_value(self) -> None:
        assert ContentType.AUDIO == "audio"

    def test_file_value(self) -> None:
        assert ContentType.FILE == "file"

    def test_sticker_value(self) -> None:
        assert ContentType.STICKER == "sticker"

    def test_contact_value(self) -> None:
        assert ContentType.CONTACT == "contact"

    def test_location_value(self) -> None:
        assert ContentType.LOCATION == "location"

    def test_share_value(self) -> None:
        assert ContentType.SHARE == "share"

    def test_inline_keyboard_value(self) -> None:
        assert ContentType.INLINE_KEYBOARD == "inline_keyboard"

    def test_any_value(self) -> None:
        assert ContentType.ANY == "any"


class TestContentTypeFilterInit:
    """Тесты инициализации ContentTypeFilter."""

    def test_single_type(self) -> None:
        f = ContentTypeFilter(ContentType.IMAGE)
        assert ContentType.IMAGE in f.content_types

    def test_multiple_types(self) -> None:
        f = ContentTypeFilter(ContentType.IMAGE, ContentType.VIDEO)
        assert ContentType.IMAGE in f.content_types
        assert ContentType.VIDEO in f.content_types

    def test_string_values(self) -> None:
        f = ContentTypeFilter("image", "video")
        assert "image" in f.content_types
        assert "video" in f.content_types

    def test_is_filter_subclass(self) -> None:
        assert issubclass(ContentTypeFilter, Filter)

    def test_empty_raises(self) -> None:
        with pytest.raises(TypeError):
            ContentTypeFilter()  # type: ignore[call-arg]


class TestContentTypeFilterCall:
    """Тесты вызова ContentTypeFilter."""

    @pytest.mark.asyncio
    async def test_text_only_message(self) -> None:
        """Текстовое сообщение без вложений — ContentType.TEXT."""
        f = ContentTypeFilter(ContentType.TEXT)
        msg = _make_message(text="hello")
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_text_filter_no_text(self) -> None:
        """Сообщение без текста и без вложений — TEXT не матчит."""
        f = ContentTypeFilter(ContentType.TEXT)
        msg = _make_message(text=None)
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_text_with_attachments(self) -> None:
        """Сообщение с текстом И вложением — TEXT не матчит (есть attachment)."""
        f = ContentTypeFilter(ContentType.TEXT)
        msg = _make_message(text="hello", attachments=[_photo_attachment()])
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_photo_match(self) -> None:
        """Фото-вложение — ContentType.IMAGE."""
        f = ContentTypeFilter(ContentType.IMAGE)
        msg = _make_message(attachments=[_photo_attachment()])
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_video_match(self) -> None:
        f = ContentTypeFilter(ContentType.VIDEO)
        msg = _make_message(attachments=[_video_attachment()])
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_audio_match(self) -> None:
        f = ContentTypeFilter(ContentType.AUDIO)
        msg = _make_message(attachments=[_audio_attachment()])
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_file_match(self) -> None:
        f = ContentTypeFilter(ContentType.FILE)
        msg = _make_message(attachments=[_file_attachment()])
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_sticker_match(self) -> None:
        f = ContentTypeFilter(ContentType.STICKER)
        msg = _make_message(attachments=[_sticker_attachment()])
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_contact_match(self) -> None:
        f = ContentTypeFilter(ContentType.CONTACT)
        msg = _make_message(attachments=[_contact_attachment()])
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_location_match(self) -> None:
        f = ContentTypeFilter(ContentType.LOCATION)
        msg = _make_message(attachments=[_location_attachment()])
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_no_match(self) -> None:
        """IMAGE фильтр на video -> False."""
        f = ContentTypeFilter(ContentType.IMAGE)
        msg = _make_message(attachments=[_video_attachment()])
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_multiple_types_match(self) -> None:
        """IMAGE | VIDEO — фото матчит."""
        f = ContentTypeFilter(ContentType.IMAGE, ContentType.VIDEO)
        msg = _make_message(attachments=[_photo_attachment()])
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_multiple_attachments_partial_match(self) -> None:
        """Несколько вложений — хотя бы одно совпало."""
        f = ContentTypeFilter(ContentType.IMAGE)
        msg = _make_message(attachments=[_video_attachment(), _photo_attachment()])
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_any_matches_text(self) -> None:
        """ContentType.ANY матчит текст."""
        f = ContentTypeFilter(ContentType.ANY)
        msg = _make_message(text="hello")
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_any_matches_attachment(self) -> None:
        """ContentType.ANY матчит вложение."""
        f = ContentTypeFilter(ContentType.ANY)
        msg = _make_message(attachments=[_photo_attachment()])
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_any_no_content(self) -> None:
        """ContentType.ANY — нет ни текста ни вложений -> False."""
        f = ContentTypeFilter(ContentType.ANY)
        msg = _make_message(text=None)
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_from_update(self) -> None:
        """Из Update с вложенным message."""
        f = ContentTypeFilter(ContentType.IMAGE)
        msg = _make_message(attachments=[_photo_attachment()])
        update = _FakeUpdate(msg)
        result = await f(update)
        assert result is True

    @pytest.mark.asyncio
    async def test_no_args(self) -> None:
        """Без аргументов -> False."""
        f = ContentTypeFilter(ContentType.IMAGE)
        result = await f()
        assert result is False

    @pytest.mark.asyncio
    async def test_invert(self) -> None:
        """~ContentTypeFilter инвертирует результат."""
        f = ~ContentTypeFilter(ContentType.IMAGE)
        msg = _make_message(attachments=[_photo_attachment()])
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_empty_attachments_list(self) -> None:
        """Пустой список вложений + нет текста -> False."""
        f = ContentTypeFilter(ContentType.IMAGE)
        msg = _make_message(text=None, attachments=[])
        result = await f(msg)
        assert result is False
