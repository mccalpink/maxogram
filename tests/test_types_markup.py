"""Тесты для types/markup.py — MarkupElement discriminated union."""

from __future__ import annotations

from pydantic import TypeAdapter

from maxogram.types.markup import (
    EmphasizedMarkup,
    HeadingMarkup,
    HighlightedMarkup,
    LinkMarkup,
    MarkupElement,
    MonospacedMarkup,
    StrikethroughMarkup,
    StrongMarkup,
    UnderlineMarkup,
    UserMentionMarkup,
)

markup_adapter = TypeAdapter(MarkupElement)


class TestMarkupDiscriminator:
    """Discriminated union по полю type."""

    def test_strong(self) -> None:
        obj = markup_adapter.validate_python({"type": "strong", "from": 0, "length": 5})
        assert isinstance(obj, StrongMarkup)
        assert obj.from_ == 0
        assert obj.length == 5

    def test_emphasized(self) -> None:
        obj = markup_adapter.validate_python({"type": "emphasized", "from": 2, "length": 3})
        assert isinstance(obj, EmphasizedMarkup)

    def test_monospaced(self) -> None:
        obj = markup_adapter.validate_python({"type": "monospaced", "from": 0, "length": 10})
        assert isinstance(obj, MonospacedMarkup)

    def test_link(self) -> None:
        obj = markup_adapter.validate_python(
            {"type": "link", "from": 0, "length": 4, "url": "https://example.com"}
        )
        assert isinstance(obj, LinkMarkup)
        assert obj.url == "https://example.com"

    def test_strikethrough(self) -> None:
        obj = markup_adapter.validate_python(
            {"type": "strikethrough", "from": 0, "length": 3}
        )
        assert isinstance(obj, StrikethroughMarkup)

    def test_underline(self) -> None:
        obj = markup_adapter.validate_python({"type": "underline", "from": 0, "length": 3})
        assert isinstance(obj, UnderlineMarkup)

    def test_user_mention(self) -> None:
        obj = markup_adapter.validate_python(
            {"type": "user_mention", "from": 0, "length": 5, "user_id": 123}
        )
        assert isinstance(obj, UserMentionMarkup)
        assert obj.user_id == 123

    def test_heading(self) -> None:
        obj = markup_adapter.validate_python({"type": "heading", "from": 0, "length": 10})
        assert isinstance(obj, HeadingMarkup)

    def test_highlighted(self) -> None:
        obj = markup_adapter.validate_python(
            {"type": "highlighted", "from": 0, "length": 5}
        )
        assert isinstance(obj, HighlightedMarkup)


class TestMarkupFromAlias:
    """Поле 'from' использует alias (from_ в Python)."""

    def test_from_alias_in_dump(self) -> None:
        obj = StrongMarkup(from_=0, length=5)
        dumped = obj.model_dump(by_alias=True)
        assert "from" in dumped
        assert dumped["from"] == 0

    def test_round_trip(self) -> None:
        data = {"type": "strong", "from": 10, "length": 20}
        obj = markup_adapter.validate_python(data)
        dumped = obj.model_dump(by_alias=True)
        obj2 = markup_adapter.validate_python(dumped)
        assert isinstance(obj2, StrongMarkup)
        assert obj2.from_ == 10
        assert obj2.length == 20
