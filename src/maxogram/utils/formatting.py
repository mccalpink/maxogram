"""Утилиты форматирования текста с markup-элементами Max API.

Builder pattern для удобного формирования текста с разметкой::

    node = Text("Привет ") + Bold("мир") + Text("!")
    text, markup = node.render()
    # text = "Привет мир!"
    # markup = [StrongMarkup(from_=7, length=3)]

Также доступны конвертеры ``as_html()`` и ``as_markdown()``.
"""

from __future__ import annotations

from html import escape as html_escape
from typing import TYPE_CHECKING

from maxogram.types.markup import (
    EmphasizedMarkup,
    HeadingMarkup,
    HighlightedMarkup,
    LinkMarkup,
    MonospacedMarkup,
    StrikethroughMarkup,
    StrongMarkup,
    UnderlineMarkup,
    UserMentionMarkup,
)

if TYPE_CHECKING:
    from maxogram.types.markup import MarkupElement

__all__ = [
    "Bold",
    "Code",
    "Heading",
    "Highlight",
    "Italic",
    "Link",
    "Pre",
    "Strikethrough",
    "Text",
    "TextBuilder",
    "Underline",
    "UserMention",
    "as_html",
    "as_markdown",
]


class _Node:
    """Базовый узел форматирования."""

    __slots__ = ("_text",)

    def __init__(self, text: str) -> None:
        self._text = text

    def render(self, offset: int = 0) -> tuple[str, list[MarkupElement]]:
        """Отрендерить узел в текст + массив markup.

        Args:
            offset: Начальная позиция в итоговом тексте.

        Returns:
            Кортеж (текст, список MarkupElement).
        """
        raise NotImplementedError

    def __add__(self, other: object) -> _ConcatNode:
        if not isinstance(other, _Node):
            return NotImplemented
        return _ConcatNode(self, other)


class _ConcatNode(_Node):
    """Конкатенация двух узлов."""

    __slots__ = ("_left", "_right")

    def __init__(self, left: _Node, right: _Node) -> None:
        super().__init__("")
        self._left = left
        self._right = right

    def render(self, offset: int = 0) -> tuple[str, list[MarkupElement]]:
        """Отрендерить оба узла последовательно."""
        left_text, left_markup = self._left.render(offset)
        right_text, right_markup = self._right.render(offset + len(left_text))
        return left_text + right_text, left_markup + right_markup


class Text(_Node):
    """Простой текст без форматирования."""

    __slots__ = ()

    def render(self, offset: int = 0) -> tuple[str, list[MarkupElement]]:
        """Вернуть текст без markup."""
        return self._text, []


class _MarkupNode(_Node):
    """Узел с одним типом markup."""

    __slots__ = ()

    def _make_markup(self, offset: int, length: int) -> MarkupElement:
        """Создать MarkupElement нужного типа."""
        raise NotImplementedError

    def render(self, offset: int = 0) -> tuple[str, list[MarkupElement]]:
        """Вернуть текст с одним markup-элементом."""
        length = len(self._text)
        if length == 0:
            return "", []
        return self._text, [self._make_markup(offset, length)]


class Bold(_MarkupNode):
    """Жирный текст (StrongMarkup)."""

    __slots__ = ()

    def _make_markup(self, offset: int, length: int) -> MarkupElement:
        return StrongMarkup(from_=offset, length=length)


class Italic(_MarkupNode):
    """Курсив (EmphasizedMarkup)."""

    __slots__ = ()

    def _make_markup(self, offset: int, length: int) -> MarkupElement:
        return EmphasizedMarkup(from_=offset, length=length)


class Code(_MarkupNode):
    """Моноширинный текст (MonospacedMarkup)."""

    __slots__ = ()

    def _make_markup(self, offset: int, length: int) -> MarkupElement:
        return MonospacedMarkup(from_=offset, length=length)


class Pre(_MarkupNode):
    """Блок кода (MonospacedMarkup)."""

    __slots__ = ()

    def _make_markup(self, offset: int, length: int) -> MarkupElement:
        return MonospacedMarkup(from_=offset, length=length)


class Strikethrough(_MarkupNode):
    """Зачёркнутый текст (StrikethroughMarkup)."""

    __slots__ = ()

    def _make_markup(self, offset: int, length: int) -> MarkupElement:
        return StrikethroughMarkup(from_=offset, length=length)


class Underline(_MarkupNode):
    """Подчёркнутый текст (UnderlineMarkup)."""

    __slots__ = ()

    def _make_markup(self, offset: int, length: int) -> MarkupElement:
        return UnderlineMarkup(from_=offset, length=length)


class Heading(_MarkupNode):
    """Заголовок (HeadingMarkup)."""

    __slots__ = ()

    def _make_markup(self, offset: int, length: int) -> MarkupElement:
        return HeadingMarkup(from_=offset, length=length)


class Highlight(_MarkupNode):
    """Выделенный текст (HighlightedMarkup)."""

    __slots__ = ()

    def _make_markup(self, offset: int, length: int) -> MarkupElement:
        return HighlightedMarkup(from_=offset, length=length)


class Link(_Node):
    """Текст-ссылка (LinkMarkup)."""

    __slots__ = ("_url",)

    def __init__(self, text: str, *, url: str) -> None:
        super().__init__(text)
        self._url = url

    def render(self, offset: int = 0) -> tuple[str, list[MarkupElement]]:
        """Вернуть текст с LinkMarkup."""
        length = len(self._text)
        if length == 0:
            return "", []
        markup = LinkMarkup(from_=offset, length=length, url=self._url)
        return self._text, [markup]


class UserMention(_Node):
    """Упоминание пользователя (UserMentionMarkup).

    Требуется хотя бы один из параметров: user_id или user_link.
    """

    __slots__ = ("_user_id", "_user_link")

    def __init__(
        self,
        text: str,
        *,
        user_id: int | None = None,
        user_link: str | None = None,
    ) -> None:
        if user_id is None and user_link is None:
            msg = "UserMention требует user_id или user_link"
            raise ValueError(msg)
        super().__init__(text)
        self._user_id = user_id
        self._user_link = user_link

    def render(self, offset: int = 0) -> tuple[str, list[MarkupElement]]:
        """Вернуть текст с UserMentionMarkup."""
        length = len(self._text)
        if length == 0:
            return "", []
        markup = UserMentionMarkup(
            from_=offset,
            length=length,
            user_id=self._user_id,
            user_link=self._user_link,
        )
        return self._text, [markup]


class TextBuilder:
    """Построитель форматированного текста через цепочку add().

    Пример::

        builder = TextBuilder()
        builder.add(Bold("жирный")).add(Text(" и ")).add(Italic("курсив"))
        text, markup = builder.render()
    """

    __slots__ = ("_nodes",)

    def __init__(self) -> None:
        self._nodes: list[_Node] = []

    def add(self, node: _Node) -> TextBuilder:
        """Добавить узел форматирования.

        Args:
            node: Узел (Text, Bold, Italic и т.д.)

        Returns:
            self для цепочки вызовов.
        """
        self._nodes.append(node)
        return self

    def render(self) -> tuple[str, list[MarkupElement]]:
        """Отрендерить все узлы в текст + массив markup.

        Returns:
            Кортеж (текст, список MarkupElement).
        """
        if not self._nodes:
            return "", []
        parts: list[str] = []
        all_markup: list[MarkupElement] = []
        offset = 0
        for node in self._nodes:
            text, markup = node.render(offset)
            parts.append(text)
            all_markup.extend(markup)
            offset += len(text)
        return "".join(parts), all_markup


# --- Конвертеры ---

# Маппинг типов узлов на HTML-теги
_HTML_TAGS: dict[type[_Node], tuple[str, str]] = {
    Bold: ("<b>", "</b>"),
    Italic: ("<i>", "</i>"),
    Code: ("<code>", "</code>"),
    Pre: ("<pre>", "</pre>"),
    Strikethrough: ("<s>", "</s>"),
    Underline: ("<u>", "</u>"),
    Heading: ("<b>", "</b>"),
    Highlight: ("<mark>", "</mark>"),
}

# Маппинг типов узлов на Markdown-маркеры
_MD_MARKERS: dict[type[_Node], tuple[str, str]] = {
    Bold: ("**", "**"),
    Italic: ("_", "_"),
    Code: ("`", "`"),
    Strikethrough: ("~~", "~~"),
    Underline: ("__", "__"),
    Heading: ("# ", ""),
    Highlight: ("==", "=="),
}


def _node_to_html(node: _Node) -> str:
    """Рекурсивно преобразовать узел в HTML."""
    if isinstance(node, _ConcatNode):
        return _node_to_html(node._left) + _node_to_html(node._right)

    escaped = html_escape(node._text, quote=True)

    if isinstance(node, Text):
        return escaped

    if isinstance(node, Link):
        url = html_escape(node._url, quote=True)
        return f'<a href="{url}">{escaped}</a>'

    if isinstance(node, UserMention):
        return escaped

    tags = _HTML_TAGS.get(type(node))
    if tags:
        return f"{tags[0]}{escaped}{tags[1]}"

    return escaped


def as_html(node: _Node) -> str:
    """Конвертировать дерево узлов в HTML-строку.

    Args:
        node: Корневой узел форматирования.

    Returns:
        HTML-строка с тегами.
    """
    return _node_to_html(node)


def _node_to_markdown(node: _Node) -> str:
    """Рекурсивно преобразовать узел в Markdown."""
    if isinstance(node, _ConcatNode):
        return _node_to_markdown(node._left) + _node_to_markdown(node._right)

    if isinstance(node, Text):
        return node._text

    if isinstance(node, Pre):
        return f"```\n{node._text}\n```"

    if isinstance(node, Link):
        return f"[{node._text}]({node._url})"

    if isinstance(node, UserMention):
        return node._text

    markers = _MD_MARKERS.get(type(node))
    if markers:
        return f"{markers[0]}{node._text}{markers[1]}"

    return node._text


def as_markdown(node: _Node) -> str:
    """Конвертировать дерево узлов в Markdown-строку.

    Args:
        node: Корневой узел форматирования.

    Returns:
        Markdown-строка с маркерами.
    """
    return _node_to_markdown(node)
