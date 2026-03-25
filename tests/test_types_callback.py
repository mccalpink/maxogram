"""Тесты для types/callback.py."""

from __future__ import annotations

from maxogram.types.callback import Callback, CallbackAnswer


class TestCallback:
    def test_create(self) -> None:
        data = {
            "timestamp": 1711000000000,
            "callback_id": "cb_12345",
            "payload": "btn_action",
            "user": {
                "user_id": 111,
                "name": "Иван",
                "is_bot": False,
                "last_activity_time": 1711000000000,
            },
        }
        cb = Callback.model_validate(data)
        assert cb.callback_id == "cb_12345"
        assert cb.payload == "btn_action"
        assert cb.user.user_id == 111

    def test_payload_optional(self) -> None:
        data = {
            "timestamp": 1711000000000,
            "callback_id": "cb_1",
            "user": {
                "user_id": 111,
                "name": "Иван",
                "is_bot": False,
                "last_activity_time": 1711000000000,
            },
        }
        cb = Callback.model_validate(data)
        assert cb.payload is None


class TestCallbackAnswer:
    def test_notification(self) -> None:
        answer = CallbackAnswer(notification="Done!")
        assert answer.notification == "Done!"
        assert answer.message is None

    def test_empty(self) -> None:
        answer = CallbackAnswer()
        assert answer.notification is None
        assert answer.message is None
