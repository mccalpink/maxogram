"""Тесты для types/button.py — Button discriminated union."""

from __future__ import annotations

from pydantic import TypeAdapter

from maxogram.types.button import (
    Button,
    CallbackButton,
    ChatButton,
    LinkButton,
    RequestContactButton,
    RequestGeoLocationButton,
)

button_adapter = TypeAdapter(Button)


class TestButtonDiscriminator:
    """Discriminated union по полю type."""

    def test_callback(self) -> None:
        obj = button_adapter.validate_python(
            {"type": "callback", "text": "OK", "payload": "action_ok"}
        )
        assert isinstance(obj, CallbackButton)
        assert obj.text == "OK"
        assert obj.payload == "action_ok"
        assert obj.intent == "default"

    def test_callback_with_intent(self) -> None:
        obj = button_adapter.validate_python(
            {"type": "callback", "text": "Delete", "payload": "del", "intent": "negative"}
        )
        assert isinstance(obj, CallbackButton)
        assert obj.intent == "negative"

    def test_link(self) -> None:
        obj = button_adapter.validate_python(
            {"type": "link", "text": "Open", "url": "https://example.com"}
        )
        assert isinstance(obj, LinkButton)
        assert obj.url == "https://example.com"

    def test_request_contact(self) -> None:
        obj = button_adapter.validate_python({"type": "request_contact", "text": "Share contact"})
        assert isinstance(obj, RequestContactButton)

    def test_request_geo_location(self) -> None:
        obj = button_adapter.validate_python(
            {"type": "request_geo_location", "text": "Share location", "quick": True}
        )
        assert isinstance(obj, RequestGeoLocationButton)
        assert obj.quick is True

    def test_chat(self) -> None:
        obj = button_adapter.validate_python(
            {
                "type": "chat",
                "text": "Create chat",
                "chat_title": "New chat",
                "start_payload": "start_data",
            }
        )
        assert isinstance(obj, ChatButton)
        assert obj.chat_title == "New chat"


class TestButtonRoundTrip:
    def test_callback_round_trip(self) -> None:
        btn = CallbackButton(text="OK", payload="action")
        dumped = btn.model_dump()
        obj = button_adapter.validate_python(dumped)
        assert isinstance(obj, CallbackButton)
        assert obj.text == "OK"
        assert obj.payload == "action"
