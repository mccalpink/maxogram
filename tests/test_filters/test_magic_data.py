"""Тесты MagicData фильтра."""

from __future__ import annotations

import pytest
from magic_filter import MagicFilter

from maxogram.filters.magic_data import MagicData


class TestMagicData:
    """Тесты для MagicData."""

    @pytest.mark.asyncio
    async def test_matching_value(self) -> None:
        """MagicData с F.key == value — True при совпадении."""
        f = MagicFilter()
        md = MagicData(magic=f.key == "expected")
        result = await md(key="expected")
        assert result is True

    @pytest.mark.asyncio
    async def test_not_matching_value(self) -> None:
        """MagicData с F.key == value — False при несовпадении."""
        f = MagicFilter()
        md = MagicData(magic=f.key == "expected")
        result = await md(key="other")
        assert result is False

    @pytest.mark.asyncio
    async def test_missing_attribute_returns_false(self) -> None:
        """MagicData с несуществующим атрибутом — False, не exception."""
        f = MagicFilter()
        md = MagicData(magic=f.nonexistent == "value")
        result = await md(key="something")
        assert result is False

    @pytest.mark.asyncio
    async def test_nested_attribute(self) -> None:
        """MagicData с вложенным доступом через kwargs."""
        f = MagicFilter()

        class ChatInfo:
            chat_type = "dialog"

        md = MagicData(magic=f.event_chat.chat_type == "dialog")
        result = await md(event_chat=ChatInfo())
        assert result is True

    @pytest.mark.asyncio
    async def test_truthy_non_bool_value(self) -> None:
        """MagicData возвращает bool, даже если MagicFilter возвращает truthy-значение."""
        f = MagicFilter()
        md = MagicData(magic=f.items)
        result = await md(items=[1, 2, 3])
        # MagicFilter.resolve вернёт [1, 2, 3] (truthy), MagicData должен вернуть bool
        assert result is True

    @pytest.mark.asyncio
    async def test_falsy_value(self) -> None:
        """MagicData с пустым значением — False."""
        f = MagicFilter()
        md = MagicData(magic=f.items)
        result = await md(items=[])
        assert result is False
