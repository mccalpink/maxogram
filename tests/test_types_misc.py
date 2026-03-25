"""Тесты для types/misc.py."""

from __future__ import annotations

from maxogram.types.misc import (
    ActionRequestBody,
    Error,
    Image,
    PhotoAttachmentRequestPayload,
    PhotoToken,
    PinMessageBody,
    SimpleQueryResult,
    UserIdsList,
)


class TestImage:
    def test_create(self) -> None:
        img = Image(url="https://example.com/img.jpg")
        assert img.url == "https://example.com/img.jpg"


class TestError:
    def test_create(self) -> None:
        err = Error(error="not.found", code="404", message="Chat not found")
        assert err.error == "not.found"
        assert err.code == "404"

    def test_error_nullable(self) -> None:
        err = Error(error=None, code="500", message="Internal")
        assert err.error is None


class TestSimpleQueryResult:
    def test_success(self) -> None:
        r = SimpleQueryResult(success=True)
        assert r.success is True
        assert r.message is None

    def test_with_message(self) -> None:
        r = SimpleQueryResult(success=False, message="Error")
        assert r.success is False
        assert r.message == "Error"


class TestActionRequestBody:
    def test_create(self) -> None:
        body = ActionRequestBody(action="typing_on")
        assert body.action == "typing_on"


class TestPhotoAttachmentRequestPayload:
    def test_by_url(self) -> None:
        p = PhotoAttachmentRequestPayload(url="https://example.com/photo.jpg")
        assert p.url == "https://example.com/photo.jpg"
        assert p.token is None

    def test_by_token(self) -> None:
        p = PhotoAttachmentRequestPayload(token="abc123")
        assert p.token == "abc123"

    def test_with_photos(self) -> None:
        p = PhotoAttachmentRequestPayload(
            photos={"small": PhotoToken(token="t1"), "large": PhotoToken(token="t2")}
        )
        assert p.photos is not None
        assert p.photos["small"].token == "t1"


class TestPinMessageBody:
    def test_create(self) -> None:
        body = PinMessageBody(message_id="mid_123")
        assert body.message_id == "mid_123"
        assert body.notify is True


class TestUserIdsList:
    def test_create(self) -> None:
        lst = UserIdsList(user_ids=[1, 2, 3])
        assert lst.user_ids == [1, 2, 3]
