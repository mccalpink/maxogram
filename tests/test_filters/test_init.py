"""Тесты экспорта пакета filters."""

from __future__ import annotations

from magic_filter import MagicFilter

from maxogram.filters import F, Filter, MagicData


class TestFiltersExports:
    """Тесты для __init__.py пакета filters."""

    def test_f_is_magic_filter(self) -> None:
        """F — экземпляр MagicFilter."""
        assert isinstance(F, MagicFilter)

    def test_filter_accessible(self) -> None:
        """Filter доступен из пакета."""
        from abc import ABC

        assert issubclass(Filter, ABC)

    def test_magic_data_accessible(self) -> None:
        """MagicData доступен из пакета."""
        assert MagicData is not None

    def test_f_has_as_method(self) -> None:
        """F поддерживает .as_() расширение."""
        result = F.text.as_("my_text")
        assert isinstance(result, MagicFilter)
