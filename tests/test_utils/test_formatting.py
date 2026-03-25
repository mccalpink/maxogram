"""Тесты утилит форматирования текста."""

from __future__ import annotations

import pytest

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
from maxogram.utils.formatting import (
    Bold,
    Code,
    Heading,
    Highlight,
    Italic,
    Link,
    Pre,
    Strikethrough,
    Text,
    TextBuilder,
    Underline,
    UserMention,
    as_html,
    as_markdown,
)


class TestSingleElements:
    """Одиночные элементы форматирования."""

    def test_plain_text(self) -> None:
        """Text — просто текст без markup."""
        node = Text("Привет")
        text, markup = node.render()
        assert text == "Привет"
        assert markup == []

    def test_bold(self) -> None:
        """Bold — StrongMarkup."""
        node = Bold("жирный")
        text, markup = node.render()
        assert text == "жирный"
        assert len(markup) == 1
        m = markup[0]
        assert isinstance(m, StrongMarkup)
        assert m.from_ == 0
        assert m.length == 6

    def test_italic(self) -> None:
        """Italic — EmphasizedMarkup."""
        node = Italic("курсив")
        text, markup = node.render()
        assert text == "курсив"
        assert len(markup) == 1
        assert isinstance(markup[0], EmphasizedMarkup)
        assert markup[0].from_ == 0
        assert markup[0].length == 6

    def test_code(self) -> None:
        """Code — MonospacedMarkup."""
        node = Code("print()")
        text, markup = node.render()
        assert text == "print()"
        assert len(markup) == 1
        assert isinstance(markup[0], MonospacedMarkup)
        assert markup[0].from_ == 0
        assert markup[0].length == 7

    def test_pre(self) -> None:
        """Pre — MonospacedMarkup (как Code, для блоков)."""
        node = Pre("def foo():\n    pass")
        text, markup = node.render()
        assert text == "def foo():\n    pass"
        assert len(markup) == 1
        assert isinstance(markup[0], MonospacedMarkup)

    def test_link(self) -> None:
        """Link — LinkMarkup с url."""
        node = Link("сайт", url="https://example.com")
        text, markup = node.render()
        assert text == "сайт"
        assert len(markup) == 1
        m = markup[0]
        assert isinstance(m, LinkMarkup)
        assert m.from_ == 0
        assert m.length == 4
        assert m.url == "https://example.com"

    def test_strikethrough(self) -> None:
        """Strikethrough — StrikethroughMarkup."""
        node = Strikethrough("зачёркнуто")
        text, markup = node.render()
        assert text == "зачёркнуто"
        assert len(markup) == 1
        assert isinstance(markup[0], StrikethroughMarkup)

    def test_underline(self) -> None:
        """Underline — UnderlineMarkup."""
        node = Underline("подчёркнуто")
        text, markup = node.render()
        assert text == "подчёркнуто"
        assert len(markup) == 1
        assert isinstance(markup[0], UnderlineMarkup)

    def test_heading(self) -> None:
        """Heading — HeadingMarkup."""
        node = Heading("Заголовок")
        text, markup = node.render()
        assert text == "Заголовок"
        assert len(markup) == 1
        assert isinstance(markup[0], HeadingMarkup)

    def test_highlight(self) -> None:
        """Highlight — HighlightedMarkup."""
        node = Highlight("выделено")
        text, markup = node.render()
        assert text == "выделено"
        assert len(markup) == 1
        assert isinstance(markup[0], HighlightedMarkup)

    def test_user_mention_by_id(self) -> None:
        """UserMention по user_id."""
        node = UserMention("Вася", user_id=12345)
        text, markup = node.render()
        assert text == "Вася"
        assert len(markup) == 1
        m = markup[0]
        assert isinstance(m, UserMentionMarkup)
        assert m.user_id == 12345
        assert m.user_link is None

    def test_user_mention_by_link(self) -> None:
        """UserMention по user_link."""
        node = UserMention("Вася", user_link="vasya")
        text, markup = node.render()
        m = markup[0]
        assert isinstance(m, UserMentionMarkup)
        assert m.user_link == "vasya"
        assert m.user_id is None

    def test_empty_text(self) -> None:
        """Пустой текст — пустой результат."""
        node = Text("")
        text, markup = node.render()
        assert text == ""
        assert markup == []

    def test_empty_bold(self) -> None:
        """Пустой Bold — нет markup (нулевая длина)."""
        node = Bold("")
        text, markup = node.render()
        assert text == ""
        assert markup == []


class TestConcatenation:
    """Конкатенация элементов через + оператор."""

    def test_text_plus_text(self) -> None:
        """Text + Text = конкатенация строк без markup."""
        node = Text("Привет ") + Text("мир")
        text, markup = node.render()
        assert text == "Привет мир"
        assert markup == []

    def test_text_plus_bold(self) -> None:
        """Text + Bold — markup со смещением."""
        node = Text("Привет ") + Bold("мир")
        text, markup = node.render()
        assert text == "Привет мир"
        assert len(markup) == 1
        m = markup[0]
        assert isinstance(m, StrongMarkup)
        assert m.from_ == 7  # len("Привет ") в символах
        assert m.length == 3

    def test_bold_plus_text(self) -> None:
        """Bold + Text — markup в начале."""
        node = Bold("жирный") + Text(" текст")
        text, markup = node.render()
        assert text == "жирный текст"
        assert len(markup) == 1
        assert markup[0].from_ == 0
        assert markup[0].length == 6

    def test_multiple_concat(self) -> None:
        """Цепочка из нескольких элементов."""
        node = Text("a") + Bold("b") + Italic("c") + Text("d")
        text, markup = node.render()
        assert text == "abcd"
        assert len(markup) == 2
        # Bold "b" at offset 1
        assert isinstance(markup[0], StrongMarkup)
        assert markup[0].from_ == 1
        assert markup[0].length == 1
        # Italic "c" at offset 2
        assert isinstance(markup[1], EmphasizedMarkup)
        assert markup[1].from_ == 2
        assert markup[1].length == 1

    def test_bold_plus_bold(self) -> None:
        """Bold + Bold — два отдельных markup."""
        node = Bold("а") + Bold("б")
        text, markup = node.render()
        assert text == "аб"
        assert len(markup) == 2
        assert markup[0].from_ == 0
        assert markup[0].length == 1
        assert markup[1].from_ == 1
        assert markup[1].length == 1

    def test_unicode_offsets(self) -> None:
        """Корректные offset для Unicode (кириллица, эмодзи)."""
        # Max API использует offset в символах (не байтах)
        node = Text("Привет ") + Bold("мир") + Text("!")
        text, markup = node.render()
        assert text == "Привет мир!"
        m = markup[0]
        assert m.from_ == 7
        assert m.length == 3


class TestTextBuilder:
    """TextBuilder — альтернативный API."""

    def test_builder_basic(self) -> None:
        """TextBuilder с цепочкой вызовов."""
        builder = TextBuilder()
        builder.add(Text("Привет "))
        builder.add(Bold("мир"))
        text, markup = builder.render()
        assert text == "Привет мир"
        assert len(markup) == 1

    def test_builder_add_returns_self(self) -> None:
        """add() возвращает self для цепочки."""
        builder = TextBuilder()
        result = builder.add(Text("test"))
        assert result is builder

    def test_builder_empty(self) -> None:
        """Пустой builder — пустой результат."""
        builder = TextBuilder()
        text, markup = builder.render()
        assert text == ""
        assert markup == []

    def test_builder_multiple_markup(self) -> None:
        """Builder с разными типами markup."""
        builder = TextBuilder()
        builder.add(Bold("жирный"))
        builder.add(Text(" и "))
        builder.add(Italic("курсив"))
        builder.add(Text(" и "))
        builder.add(Code("код"))
        text, markup = builder.render()
        assert text == "жирный и курсив и код"
        assert len(markup) == 3
        assert isinstance(markup[0], StrongMarkup)
        assert isinstance(markup[1], EmphasizedMarkup)
        assert isinstance(markup[2], MonospacedMarkup)


class TestAsHtml:
    """Конвертация в HTML."""

    def test_plain_text(self) -> None:
        """Простой текст — без тегов."""
        assert as_html(Text("hello")) == "hello"

    def test_bold(self) -> None:
        """Bold -> <b>."""
        assert as_html(Bold("жирный")) == "<b>жирный</b>"

    def test_italic(self) -> None:
        """Italic -> <i>."""
        assert as_html(Italic("курсив")) == "<i>курсив</i>"

    def test_code(self) -> None:
        """Code -> <code>."""
        assert as_html(Code("print()")) == "<code>print()</code>"

    def test_pre(self) -> None:
        """Pre -> <pre>."""
        assert as_html(Pre("code block")) == "<pre>code block</pre>"

    def test_link(self) -> None:
        """Link -> <a href>."""
        assert as_html(Link("сайт", url="https://example.com")) == (
            '<a href="https://example.com">сайт</a>'
        )

    def test_strikethrough(self) -> None:
        """Strikethrough -> <s>."""
        assert as_html(Strikethrough("зачёркнуто")) == "<s>зачёркнуто</s>"

    def test_underline(self) -> None:
        """Underline -> <u>."""
        assert as_html(Underline("подчёркнуто")) == "<u>подчёркнуто</u>"

    def test_mixed(self) -> None:
        """Смешанный текст — теги в правильных позициях."""
        node = Text("Привет ") + Bold("мир") + Text("!")
        assert as_html(node) == "Привет <b>мир</b>!"

    def test_html_escaping(self) -> None:
        """Спецсимволы HTML экранируются."""
        node = Text("<script>alert('xss')</script>")
        assert as_html(node) == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"

    def test_html_escaping_in_bold(self) -> None:
        """Спецсимволы внутри markup тоже экранируются."""
        node = Bold("<b>")
        assert as_html(node) == "<b>&lt;b&gt;</b>"


class TestAsMarkdown:
    """Конвертация в Markdown."""

    def test_plain_text(self) -> None:
        """Простой текст — без маркеров."""
        assert as_markdown(Text("hello")) == "hello"

    def test_bold(self) -> None:
        """Bold -> **text**."""
        assert as_markdown(Bold("жирный")) == "**жирный**"

    def test_italic(self) -> None:
        """Italic -> _text_."""
        assert as_markdown(Italic("курсив")) == "_курсив_"

    def test_code(self) -> None:
        """Code -> `text`."""
        assert as_markdown(Code("print()")) == "`print()`"

    def test_pre(self) -> None:
        """Pre -> ```text```."""
        assert as_markdown(Pre("code block")) == "```\ncode block\n```"

    def test_link(self) -> None:
        """Link -> [text](url)."""
        assert as_markdown(Link("сайт", url="https://example.com")) == (
            "[сайт](https://example.com)"
        )

    def test_strikethrough(self) -> None:
        """Strikethrough -> ~~text~~."""
        assert as_markdown(Strikethrough("зачёркнуто")) == "~~зачёркнуто~~"

    def test_mixed(self) -> None:
        """Смешанный текст."""
        node = Text("Привет ") + Bold("мир") + Text("!")
        assert as_markdown(node) == "Привет **мир**!"


class TestEdgeCases:
    """Граничные случаи."""

    def test_link_requires_url(self) -> None:
        """Link без url — TypeError."""
        with pytest.raises(TypeError):
            Link("text")  # type: ignore[call-arg]

    def test_user_mention_requires_id_or_link(self) -> None:
        """UserMention без user_id и user_link — ValueError."""
        with pytest.raises(ValueError, match="user_id.*user_link"):
            UserMention("Вася")

    def test_multiline_text(self) -> None:
        """Многострочный текст — offset корректен."""
        node = Text("строка 1\nстрока 2\n") + Bold("жирный")
        text, markup = node.render()
        assert text == "строка 1\nстрока 2\nжирный"
        assert markup[0].from_ == 18  # len("строка 1\nстрока 2\n") == 18
        assert markup[0].length == 6

    def test_render_as_new_message_body_args(self) -> None:
        """render() результат подходит для NewMessageBody(text=..., markup=...)."""
        node = Text("Hello ") + Bold("world")
        text, markup = node.render()
        # Должно быть совместимо с NewMessageBody
        from maxogram.types.message import NewMessageBody

        body = NewMessageBody(text=text)
        assert body.text == "Hello world"

    def test_add_with_plus_str_not_supported(self) -> None:
        """Сложение с обычной строкой не поддерживается (явное лучше неявного)."""
        with pytest.raises(TypeError):
            Text("hello") + " world"  # type: ignore[operator]

    def test_multiple_links(self) -> None:
        """Несколько Link подряд — каждый со своим url."""
        node = (
            Link("google", url="https://google.com") + Text(" ") + Link("ya", url="https://ya.ru")
        )
        text, markup = node.render()
        assert text == "google ya"
        assert len(markup) == 2
        assert isinstance(markup[0], LinkMarkup)
        assert markup[0].url == "https://google.com"
        assert isinstance(markup[1], LinkMarkup)
        assert markup[1].url == "https://ya.ru"
        assert markup[1].from_ == 7
