"""Построитель inline-клавиатур для Max API."""

from __future__ import annotations

from maxogram.enums import Intent
from maxogram.types.attachment import InlineKeyboardAttachmentRequestWrapper
from maxogram.types.button import (
    Button,
    CallbackButton,
    ChatButton,
    LinkButton,
    RequestContactButton,
    RequestGeoLocationButton,
)
from maxogram.types.keyboard import InlineKeyboardAttachmentRequest

__all__ = ["InlineKeyboardBuilder"]


class InlineKeyboardBuilder:
    """Построитель inline-клавиатур для Max API.

    Пример::

        builder = InlineKeyboardBuilder()
        builder.button(text="Да", payload="yes")
        builder.button(text="Нет", payload="no")
        builder.adjust(2)  # 2 кнопки в ряд
        attachment = builder.as_attachment()
    """

    def __init__(self) -> None:
        self._buttons: list[Button] = []
        self._rows: list[list[Button]] | None = None

    def button(
        self,
        text: str,
        *,
        payload: str | None = None,
        intent: Intent = Intent.DEFAULT,
        url: str | None = None,
        request_contact: bool = False,
        request_geo_location: bool = False,
        quick: bool = False,
        chat_title: str | None = None,
        chat_description: str | None = None,
        start_payload: str | None = None,
    ) -> InlineKeyboardBuilder:
        """Добавить кнопку. Тип определяется из параметров.

        Args:
            text: Текст кнопки.
            payload: Callback-данные (создаёт CallbackButton).
            intent: Визуальный стиль кнопки (только для CallbackButton).
            url: URL ссылки (создаёт LinkButton).
            request_contact: Запросить контакт (создаёт RequestContactButton).
            request_geo_location: Запросить геолокацию (создаёт RequestGeoLocationButton).
            quick: Быстрая геолокация (только для RequestGeoLocationButton).
            chat_title: Название чата (создаёт ChatButton).
            chat_description: Описание чата (только для ChatButton).
            start_payload: Стартовый payload (только для ChatButton).

        Returns:
            self для fluent API.

        Raises:
            ValueError: Если не удалось определить тип кнопки.
        """
        btn: Button
        if url is not None:
            btn = LinkButton(text=text, url=url)
        elif request_contact:
            btn = RequestContactButton(text=text)
        elif request_geo_location:
            btn = RequestGeoLocationButton(text=text, quick=quick)
        elif chat_title is not None:
            btn = ChatButton(
                text=text,
                chat_title=chat_title,
                chat_description=chat_description,
                start_payload=start_payload,
            )
        elif payload is not None:
            btn = CallbackButton(text=text, payload=payload, intent=intent)
        else:
            msg = (
                "Не удалось определить тип кнопки. "
                "Укажите payload, url, request_contact, "
                "request_geo_location или chat_title."
            )
            raise ValueError(msg)

        self._buttons.append(btn)
        return self

    def add(self, *buttons: Button) -> InlineKeyboardBuilder:
        """Добавить готовые кнопки.

        Args:
            buttons: Экземпляры кнопок.

        Returns:
            self для fluent API.
        """
        self._buttons.extend(buttons)
        return self

    def row(self, *buttons: Button) -> InlineKeyboardBuilder:
        """Добавить ряд кнопок.

        Накопленные через button()/add() кнопки сбрасываются
        в отдельный ряд перед добавлением нового.

        Args:
            buttons: Кнопки для ряда.

        Returns:
            self для fluent API.
        """
        if self._rows is None:
            self._rows = []
        if self._buttons:
            self._rows.append(list(self._buttons))
            self._buttons.clear()
        self._rows.append(list(buttons))
        return self

    def adjust(self, *sizes: int) -> InlineKeyboardBuilder:
        """Разбить кнопки на ряды по указанным размерам.

        Args:
            sizes: Размеры рядов. Если передано несколько значений,
                они циклически повторяются. adjust(2) — по 2 в ряду,
                adjust(2, 1) — первый ряд 2, второй 1, далее повторяется.

        Returns:
            self для fluent API.
        """
        all_buttons = self._collect_buttons()
        self._rows = []

        if not sizes:
            sizes = (1,)

        idx = 0
        size_idx = 0
        while idx < len(all_buttons):
            size = sizes[size_idx % len(sizes)]
            self._rows.append(all_buttons[idx : idx + size])
            idx += size
            size_idx += 1

        self._buttons.clear()
        return self

    def as_attachment(self) -> InlineKeyboardAttachmentRequestWrapper:
        """Собрать как AttachmentRequest для отправки.

        Returns:
            InlineKeyboardAttachmentRequestWrapper с type="inline_keyboard".
        """
        return InlineKeyboardAttachmentRequestWrapper(
            payload=self.as_keyboard(),
        )

    def as_keyboard(self) -> InlineKeyboardAttachmentRequest:
        """Собрать как InlineKeyboardAttachmentRequest.

        Returns:
            InlineKeyboardAttachmentRequest с рядами кнопок.
        """
        return InlineKeyboardAttachmentRequest(buttons=self._build_rows())

    def _collect_buttons(self) -> list[Button]:
        """Собрать все кнопки из _buttons и _rows в плоский список."""
        result: list[Button] = []
        if self._rows is not None:
            for row in self._rows:
                result.extend(row)
        result.extend(self._buttons)
        return result

    def _build_rows(self) -> list[list[Button]]:
        """Построить финальные ряды кнопок."""
        if self._rows is not None:
            rows = list(self._rows)
            if self._buttons:
                rows.append(list(self._buttons))
            return rows
        return [[b] for b in self._buttons]
