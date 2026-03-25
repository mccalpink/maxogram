"""Типы разметки текста Max API."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from maxogram.types.base import MaxObject


class StrongMarkup(MaxObject):
    """Жирный текст."""

    type: Literal["strong"] = "strong"
    from_: int = Field(alias="from")
    length: int


class EmphasizedMarkup(MaxObject):
    """Курсив."""

    type: Literal["emphasized"] = "emphasized"
    from_: int = Field(alias="from")
    length: int


class MonospacedMarkup(MaxObject):
    """Моноширинный текст."""

    type: Literal["monospaced"] = "monospaced"
    from_: int = Field(alias="from")
    length: int


class LinkMarkup(MaxObject):
    """Ссылка в тексте."""

    type: Literal["link"] = "link"
    from_: int = Field(alias="from")
    length: int
    url: str


class StrikethroughMarkup(MaxObject):
    """Зачёркнутый текст."""

    type: Literal["strikethrough"] = "strikethrough"
    from_: int = Field(alias="from")
    length: int


class UnderlineMarkup(MaxObject):
    """Подчёркнутый текст."""

    type: Literal["underline"] = "underline"
    from_: int = Field(alias="from")
    length: int


class UserMentionMarkup(MaxObject):
    """Упоминание пользователя."""

    type: Literal["user_mention"] = "user_mention"
    from_: int = Field(alias="from")
    length: int
    user_link: str | None = None
    user_id: int | None = None


class HeadingMarkup(MaxObject):
    """Заголовок."""

    type: Literal["heading"] = "heading"
    from_: int = Field(alias="from")
    length: int


class HighlightedMarkup(MaxObject):
    """Выделенный текст."""

    type: Literal["highlighted"] = "highlighted"
    from_: int = Field(alias="from")
    length: int


MarkupElement = Annotated[
    Union[
        StrongMarkup,
        EmphasizedMarkup,
        MonospacedMarkup,
        LinkMarkup,
        StrikethroughMarkup,
        UnderlineMarkup,
        UserMentionMarkup,
        HeadingMarkup,
        HighlightedMarkup,
    ],
    Field(discriminator="type"),
]
