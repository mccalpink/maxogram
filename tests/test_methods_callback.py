"""Тесты для methods/callback.py."""

from __future__ import annotations

from maxogram.methods.callback import AnswerOnCallback, Construct
from maxogram.types.constructor import ConstructedMessageBody
from maxogram.types.keyboard import Keyboard
from maxogram.types.message import NewMessageBody
from maxogram.types.misc import SimpleQueryResult


class TestAnswerOnCallback:
    """Тесты POST /answers — ответ на callback."""

    def test_metadata(self) -> None:
        assert AnswerOnCallback.__api_path__ == "/answers"
        assert AnswerOnCallback.__http_method__ == "POST"
        assert AnswerOnCallback.__returning__ is SimpleQueryResult
        assert AnswerOnCallback.__query_params__ == {"callback_id"}
        assert AnswerOnCallback.__path_params__ == {}

    def test_create_minimal(self) -> None:
        """Создание с минимальными параметрами — только callback_id."""
        m = AnswerOnCallback(callback_id="cb-123")
        assert m.callback_id == "cb-123"
        assert m.message is None
        assert m.notification is None

    def test_create_with_notification(self) -> None:
        """Ответ с текстовым уведомлением."""
        m = AnswerOnCallback(callback_id="cb-1", notification="Принято!")
        assert m.notification == "Принято!"

    def test_create_with_message(self) -> None:
        """Ответ с изменением сообщения."""
        body = NewMessageBody(text="Обновлённый текст")
        m = AnswerOnCallback(callback_id="cb-2", message=body)
        assert m.message is not None
        assert m.message.text == "Обновлённый текст"

    def test_body_excludes_query_params(self) -> None:
        """callback_id — query param, не попадает в body."""
        m = AnswerOnCallback(
            callback_id="cb-x",
            notification="Уведомление",
        )
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert "callback_id" not in body
        assert "notification" in body

    def test_body_excludes_none(self) -> None:
        """Поля со значением None не попадают в body."""
        m = AnswerOnCallback(callback_id="cb-y")
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert body == {}


class TestConstruct:
    """Тесты POST /answers/constructor — ответ конструктора."""

    def test_metadata(self) -> None:
        assert Construct.__api_path__ == "/answers/constructor"
        assert Construct.__http_method__ == "POST"
        assert Construct.__returning__ is SimpleQueryResult
        assert Construct.__query_params__ == {"session_id"}
        assert Construct.__path_params__ == {}

    def test_create_minimal(self) -> None:
        """Создание с минимальными параметрами — только session_id."""
        m = Construct(session_id="sess-abc")
        assert m.session_id == "sess-abc"
        assert m.messages is None
        assert m.allow_user_input is False
        assert m.hint is None
        assert m.data is None
        assert m.keyboard is None
        assert m.placeholder is None

    def test_create_with_messages(self) -> None:
        """Создание с сообщениями конструктора."""
        msgs = [ConstructedMessageBody(text="Первый"), ConstructedMessageBody(text="Второй")]
        m = Construct(session_id="sess-1", messages=msgs)
        assert m.messages is not None
        assert len(m.messages) == 2
        assert m.messages[0].text == "Первый"

    def test_create_with_all_fields(self) -> None:
        """Создание со всеми полями."""
        from maxogram.types.button import CallbackButton

        kbd = Keyboard(buttons=[[CallbackButton(type="callback", text="OK", payload="ok")]])
        m = Construct(
            session_id="sess-full",
            messages=[ConstructedMessageBody(text="Текст")],
            allow_user_input=True,
            hint="Подсказка",
            data='{"key": "value"}',
            keyboard=kbd,
            placeholder="Введите текст",
        )
        assert m.allow_user_input is True
        assert m.hint == "Подсказка"
        assert m.data == '{"key": "value"}'
        assert m.keyboard is not None
        assert m.placeholder == "Введите текст"

    def test_body_excludes_query_params(self) -> None:
        """session_id — query param, не попадает в body."""
        m = Construct(
            session_id="sess-x",
            allow_user_input=True,
            hint="Подсказка",
        )
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        assert "session_id" not in body
        assert "allow_user_input" in body
        assert "hint" in body

    def test_body_excludes_none(self) -> None:
        """Поля со значением None не попадают в body."""
        m = Construct(session_id="sess-y")
        exclude = m.__query_params__ | set(m.__path_params__)
        body = m.model_dump(exclude=exclude, exclude_none=True)
        # allow_user_input=False — не None, попадает
        assert body == {"allow_user_input": False}
