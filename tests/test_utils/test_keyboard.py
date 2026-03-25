"""Тесты InlineKeyboardBuilder."""

from __future__ import annotations

import pytest

from maxogram.enums import Intent
from maxogram.types.attachment import InlineKeyboardAttachmentRequestWrapper
from maxogram.types.button import (
    CallbackButton,
    ChatButton,
    LinkButton,
    RequestContactButton,
    RequestGeoLocationButton,
)
from maxogram.types.keyboard import InlineKeyboardAttachmentRequest
from maxogram.utils.keyboard import InlineKeyboardBuilder


class TestButtonCreation:
    """Создание кнопок через button()."""

    def test_callback_button(self) -> None:
        """CallbackButton из text + payload."""
        kb = InlineKeyboardBuilder()
        kb.button(text="Нажми", payload="click")
        rows = kb.as_keyboard().buttons
        assert len(rows) == 1
        assert len(rows[0]) == 1
        btn = rows[0][0]
        assert isinstance(btn, CallbackButton)
        assert btn.text == "Нажми"
        assert btn.payload == "click"
        assert btn.intent == Intent.DEFAULT

    def test_callback_button_with_intent(self) -> None:
        """CallbackButton с intent=POSITIVE."""
        kb = InlineKeyboardBuilder()
        kb.button(text="Да", payload="yes", intent=Intent.POSITIVE)
        btn = kb.as_keyboard().buttons[0][0]
        assert isinstance(btn, CallbackButton)
        assert btn.intent == Intent.POSITIVE

    def test_link_button(self) -> None:
        """LinkButton из url."""
        kb = InlineKeyboardBuilder()
        kb.button(text="Сайт", url="https://example.com")
        btn = kb.as_keyboard().buttons[0][0]
        assert isinstance(btn, LinkButton)
        assert btn.url == "https://example.com"

    def test_request_contact_button(self) -> None:
        """RequestContactButton из request_contact=True."""
        kb = InlineKeyboardBuilder()
        kb.button(text="Контакт", request_contact=True)
        btn = kb.as_keyboard().buttons[0][0]
        assert isinstance(btn, RequestContactButton)

    def test_request_geo_location_button(self) -> None:
        """RequestGeoLocationButton из request_geo_location=True."""
        kb = InlineKeyboardBuilder()
        kb.button(text="Где ты?", request_geo_location=True, quick=True)
        btn = kb.as_keyboard().buttons[0][0]
        assert isinstance(btn, RequestGeoLocationButton)
        assert btn.quick is True

    def test_chat_button(self) -> None:
        """ChatButton из chat_title."""
        kb = InlineKeyboardBuilder()
        kb.button(
            text="Чат",
            chat_title="Новый чат",
            chat_description="Описание",
            start_payload="start",
        )
        btn = kb.as_keyboard().buttons[0][0]
        assert isinstance(btn, ChatButton)
        assert btn.chat_title == "Новый чат"
        assert btn.chat_description == "Описание"
        assert btn.start_payload == "start"

    def test_no_type_raises_error(self) -> None:
        """button() без payload и url вызывает ValueError."""
        kb = InlineKeyboardBuilder()
        with pytest.raises(ValueError, match="Не удалось определить тип кнопки"):
            kb.button(text="???")


class TestAdd:
    """Добавление готовых кнопок через add()."""

    def test_add_buttons(self) -> None:
        """add() принимает готовые кнопки."""
        kb = InlineKeyboardBuilder()
        btn1 = CallbackButton(text="A", payload="a")
        btn2 = LinkButton(text="B", url="https://b.com")
        kb.add(btn1, btn2)
        rows = kb.as_keyboard().buttons
        # Без adjust — каждая в своём ряду
        assert len(rows) == 2
        assert rows[0][0] is btn1
        assert rows[1][0] is btn2


class TestRow:
    """Явное добавление рядов через row()."""

    def test_row(self) -> None:
        """row() добавляет кнопки как один ряд."""
        kb = InlineKeyboardBuilder()
        btn1 = CallbackButton(text="A", payload="a")
        btn2 = CallbackButton(text="B", payload="b")
        kb.row(btn1, btn2)
        rows = kb.as_keyboard().buttons
        assert len(rows) == 1
        assert len(rows[0]) == 2

    def test_row_flushes_pending_buttons(self) -> None:
        """row() сначала сбрасывает накопленные через button()/add() кнопки."""
        kb = InlineKeyboardBuilder()
        kb.button(text="Pending", payload="p")
        btn = CallbackButton(text="Row", payload="r")
        kb.row(btn)
        rows = kb.as_keyboard().buttons
        # Первый ряд — pending, второй — row
        assert len(rows) == 2
        assert rows[0][0].text == "Pending"  # type: ignore[union-attr]
        assert rows[1][0] is btn


class TestAdjust:
    """Разбиение кнопок на ряды через adjust()."""

    def test_adjust_even(self) -> None:
        """adjust(2) — 4 кнопки → 2 ряда по 2."""
        kb = InlineKeyboardBuilder()
        for i in range(4):
            kb.button(text=f"B{i}", payload=f"b{i}")
        kb.adjust(2)
        rows = kb.as_keyboard().buttons
        assert len(rows) == 2
        assert len(rows[0]) == 2
        assert len(rows[1]) == 2

    def test_adjust_varying_sizes(self) -> None:
        """adjust(2, 1) — 5 кнопок → [2, 1, 2]."""
        kb = InlineKeyboardBuilder()
        for i in range(5):
            kb.button(text=f"B{i}", payload=f"b{i}")
        kb.adjust(2, 1)
        rows = kb.as_keyboard().buttons
        assert len(rows) == 3
        assert len(rows[0]) == 2
        assert len(rows[1]) == 1
        assert len(rows[2]) == 2

    def test_adjust_no_buttons(self) -> None:
        """adjust() без кнопок — пустой результат."""
        kb = InlineKeyboardBuilder()
        kb.adjust(2)
        rows = kb.as_keyboard().buttons
        assert rows == []

    def test_adjust_single(self) -> None:
        """adjust(1) — каждая кнопка в своём ряду."""
        kb = InlineKeyboardBuilder()
        for i in range(3):
            kb.button(text=f"B{i}", payload=f"b{i}")
        kb.adjust(1)
        rows = kb.as_keyboard().buttons
        assert len(rows) == 3
        for row in rows:
            assert len(row) == 1


class TestAsKeyboard:
    """Сборка InlineKeyboardAttachmentRequest."""

    def test_as_keyboard_type(self) -> None:
        """as_keyboard() возвращает InlineKeyboardAttachmentRequest."""
        kb = InlineKeyboardBuilder()
        kb.button(text="OK", payload="ok")
        result = kb.as_keyboard()
        assert isinstance(result, InlineKeyboardAttachmentRequest)

    def test_empty_builder(self) -> None:
        """Пустой builder → пустой buttons."""
        kb = InlineKeyboardBuilder()
        result = kb.as_keyboard()
        assert result.buttons == []


class TestAsAttachment:
    """Сборка AttachmentRequest."""

    def test_as_attachment_type(self) -> None:
        """as_attachment() возвращает InlineKeyboardAttachmentRequestWrapper."""
        kb = InlineKeyboardBuilder()
        kb.button(text="OK", payload="ok")
        result = kb.as_attachment()
        assert isinstance(result, InlineKeyboardAttachmentRequestWrapper)
        assert result.type == "inline_keyboard"
        assert isinstance(result.payload, InlineKeyboardAttachmentRequest)
        assert len(result.payload.buttons) == 1


class TestFluentApi:
    """Fluent API — цепочки вызовов."""

    def test_chained_buttons_and_adjust(self) -> None:
        """builder.button(...).button(...).adjust(2) работает."""
        result = (
            InlineKeyboardBuilder()
            .button(text="A", payload="a")
            .button(text="B", payload="b")
            .button(text="C", payload="c")
            .button(text="D", payload="d")
            .adjust(2)
            .as_keyboard()
        )
        assert len(result.buttons) == 2
        assert len(result.buttons[0]) == 2
        assert len(result.buttons[1]) == 2

    def test_chained_add_and_row(self) -> None:
        """add() и row() возвращают self."""
        btn1 = CallbackButton(text="A", payload="a")
        btn2 = CallbackButton(text="B", payload="b")
        result = InlineKeyboardBuilder().add(btn1).row(btn2).as_keyboard()
        assert len(result.buttons) == 2


class TestDefaultRowBehavior:
    """Поведение без adjust — каждая кнопка в своём ряду."""

    def test_buttons_without_adjust(self) -> None:
        """Без adjust каждая кнопка — отдельный ряд."""
        kb = InlineKeyboardBuilder()
        kb.button(text="A", payload="a")
        kb.button(text="B", payload="b")
        kb.button(text="C", payload="c")
        rows = kb.as_keyboard().buttons
        assert len(rows) == 3
        for row in rows:
            assert len(row) == 1
