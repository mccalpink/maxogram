"""Тесты для types/attachment.py — Attachment и AttachmentRequest discriminated unions."""

from __future__ import annotations

from pydantic import TypeAdapter

from maxogram.types.attachment import (
    Attachment,
    AttachmentRequest,
    AudioAttachment,
    ContactAttachment,
    FileAttachment,
    InlineKeyboardAttachment,
    LocationAttachment,
    LocationAttachmentRequest,
    PhotoAttachment,
    PhotoAttachmentRequest,
    ShareAttachment,
    StickerAttachment,
    StickerAttachmentRequest,
    VideoAttachment,
)

attachment_adapter = TypeAdapter(Attachment)
request_adapter = TypeAdapter(AttachmentRequest)


class TestAttachmentDiscriminator:
    """Discriminated union по полю type (получение из API)."""

    def test_photo(self) -> None:
        data = {
            "type": "image",
            "payload": {"photo_id": 123, "url": "https://x.com/p.jpg", "token": "t1"},
        }
        obj = attachment_adapter.validate_python(data)
        assert isinstance(obj, PhotoAttachment)
        assert obj.payload.photo_id == 123

    def test_video(self) -> None:
        data = {
            "type": "video",
            "payload": {"url": "https://x.com/v.mp4", "token": "t2"},
            "width": 1920,
            "height": 1080,
            "duration": 120,
        }
        obj = attachment_adapter.validate_python(data)
        assert isinstance(obj, VideoAttachment)
        assert obj.width == 1920
        assert obj.duration == 120

    def test_audio(self) -> None:
        data = {"type": "audio", "payload": {"url": "https://x.com/a.mp3", "token": "t3"}}
        obj = attachment_adapter.validate_python(data)
        assert isinstance(obj, AudioAttachment)

    def test_file(self) -> None:
        data = {
            "type": "file",
            "payload": {"url": "https://x.com/f.pdf", "token": "t4"},
            "filename": "doc.pdf",
            "size": 1048576,
        }
        obj = attachment_adapter.validate_python(data)
        assert isinstance(obj, FileAttachment)
        assert obj.filename == "doc.pdf"
        assert obj.size == 1048576

    def test_sticker(self) -> None:
        data = {
            "type": "sticker",
            "payload": {"code": "happy"},
            "width": 128,
            "height": 128,
        }
        obj = attachment_adapter.validate_python(data)
        assert isinstance(obj, StickerAttachment)
        assert obj.payload.code == "happy"

    def test_contact(self) -> None:
        data = {
            "type": "contact",
            "payload": {"vcf_info": "BEGIN:VCARD\nEND:VCARD"},
        }
        obj = attachment_adapter.validate_python(data)
        assert isinstance(obj, ContactAttachment)

    def test_inline_keyboard(self) -> None:
        data = {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [
                    [{"type": "callback", "text": "OK", "payload": "ok"}]
                ]
            },
        }
        obj = attachment_adapter.validate_python(data)
        assert isinstance(obj, InlineKeyboardAttachment)
        assert len(obj.payload.buttons) == 1
        assert len(obj.payload.buttons[0]) == 1

    def test_share(self) -> None:
        data = {
            "type": "share",
            "payload": {"url": "https://example.com", "token": "t5"},
            "title": "Title",
            "description": "Desc",
        }
        obj = attachment_adapter.validate_python(data)
        assert isinstance(obj, ShareAttachment)
        assert obj.title == "Title"

    def test_location(self) -> None:
        data = {"type": "location", "latitude": 55.7558, "longitude": 37.6173}
        obj = attachment_adapter.validate_python(data)
        assert isinstance(obj, LocationAttachment)
        assert obj.latitude == 55.7558
        assert obj.longitude == 37.6173


class TestAttachmentRequestDiscriminator:
    """Discriminated union для запросов (отправка в API)."""

    def test_photo_request(self) -> None:
        data = {"type": "image", "payload": {"token": "upload_token"}}
        obj = request_adapter.validate_python(data)
        assert isinstance(obj, PhotoAttachmentRequest)

    def test_sticker_request(self) -> None:
        data = {"type": "sticker", "payload": {"code": "happy"}}
        obj = request_adapter.validate_python(data)
        assert isinstance(obj, StickerAttachmentRequest)

    def test_location_request(self) -> None:
        data = {"type": "location", "latitude": 55.0, "longitude": 37.0}
        obj = request_adapter.validate_python(data)
        assert isinstance(obj, LocationAttachmentRequest)


class TestAttachmentRoundTrip:
    def test_photo_round_trip(self) -> None:
        data = {
            "type": "image",
            "payload": {"photo_id": 1, "url": "https://x.com/p.jpg", "token": "t"},
        }
        obj = attachment_adapter.validate_python(data)
        dumped = obj.model_dump()
        obj2 = attachment_adapter.validate_python(dumped)
        assert isinstance(obj2, PhotoAttachment)
        assert obj2.payload.token == "t"
