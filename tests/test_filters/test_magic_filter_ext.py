"""Тесты расширения MagicFilter (.as_())."""

from __future__ import annotations

from typing import Any

from magic_filter import MagicFilter as _OriginalMagicFilter

from maxogram.utils.magic_filter import MagicFilter


class TestMagicFilterAs:
    """Тесты для MagicFilter.as_()."""

    def test_as_returns_magic_filter(self) -> None:
        """as_() возвращает MagicFilter."""
        f = MagicFilter()
        result = f.text.as_("my_text")
        assert isinstance(result, _OriginalMagicFilter)

    def test_as_resolve_with_value(self) -> None:
        """as_() с непустым значением возвращает dict."""
        f = MagicFilter()
        expr = f.text.as_("my_text")

        class Event:
            text = "hello"

        result = expr.resolve(Event())
        assert result == {"my_text": "hello"}

    def test_as_resolve_none_value(self) -> None:
        """as_() с None значением возвращает None."""
        f = MagicFilter()
        expr = f.text.as_("my_text")

        class Event:
            text = None

        result = expr.resolve(Event())
        assert result is None

    def test_as_resolve_empty_iterable(self) -> None:
        """as_() с пустой коллекцией возвращает None."""
        f = MagicFilter()
        expr = f.items.as_("my_items")

        class Event:
            items: list[Any] = []

        result = expr.resolve(Event())
        assert result is None

    def test_as_resolve_non_empty_iterable(self) -> None:
        """as_() с непустой коллекцией возвращает dict."""
        f = MagicFilter()
        expr = f.items.as_("my_items")

        class Event:
            items = [1, 2, 3]

        result = expr.resolve(Event())
        assert result == {"my_items": [1, 2, 3]}

    def test_is_subclass_of_original(self) -> None:
        """MagicFilter — подкласс оригинального MagicFilter."""
        assert issubclass(MagicFilter, _OriginalMagicFilter)
