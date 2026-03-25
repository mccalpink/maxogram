"""Тесты ChatTypeFilter."""

from __future__ import annotations

import pytest

from maxogram.enums import ChatType
from maxogram.filters.base import Filter
from maxogram.filters.chat_type import ChatTypeFilter
from maxogram.types.message import Message, MessageBody, Recipient


def _make_message(chat_type: str) -> Message:
    """Создать минимальный Message с заданным типом чата."""
    return Message(
        recipient=Recipient(chat_type=chat_type),  # type: ignore[arg-type]
        timestamp=1700000000000,
        body=MessageBody(mid="mid1", seq=1, text="hello"),
    )


class _FakeUpdate:
    """Имитация update с вложенным message."""

    def __init__(self, message: Message) -> None:
        self.update_type = "message_created"
        self.message = message


class TestChatTypeFilterInit:
    """Тесты инициализации ChatTypeFilter."""

    def test_single_enum(self) -> None:
        """Принимает один ChatType enum."""
        f = ChatTypeFilter(ChatType.DIALOG)
        assert ChatType.DIALOG in f.chat_types

    def test_multiple_enums(self) -> None:
        """Принимает несколько ChatType enum."""
        f = ChatTypeFilter(ChatType.DIALOG, ChatType.CHAT)
        assert ChatType.DIALOG in f.chat_types
        assert ChatType.CHAT in f.chat_types

    def test_string_values(self) -> None:
        """Принимает строковые значения."""
        f = ChatTypeFilter("dialog", "chat")
        assert "dialog" in f.chat_types
        assert "chat" in f.chat_types

    def test_is_filter_subclass(self) -> None:
        """ChatTypeFilter — подкласс Filter."""
        assert issubclass(ChatTypeFilter, Filter)

    def test_empty_raises(self) -> None:
        """Пустой ChatTypeFilter — TypeError."""
        with pytest.raises(TypeError):
            ChatTypeFilter()  # type: ignore[call-arg]


class TestChatTypeFilterCall:
    """Тесты вызова ChatTypeFilter."""

    @pytest.mark.asyncio
    async def test_dialog_match(self) -> None:
        """dialog — ChatTypeFilter(DIALOG) -> True."""
        f = ChatTypeFilter(ChatType.DIALOG)
        msg = _make_message("dialog")
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_chat_match(self) -> None:
        """chat — ChatTypeFilter(CHAT) -> True."""
        f = ChatTypeFilter(ChatType.CHAT)
        msg = _make_message("chat")
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_channel_match(self) -> None:
        """channel — ChatTypeFilter(CHANNEL) -> True."""
        f = ChatTypeFilter(ChatType.CHANNEL)
        msg = _make_message("channel")
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_no_match(self) -> None:
        """dialog — ChatTypeFilter(CHAT) -> False."""
        f = ChatTypeFilter(ChatType.CHAT)
        msg = _make_message("dialog")
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_multiple_types_match(self) -> None:
        """dialog — ChatTypeFilter(DIALOG, CHAT) -> True."""
        f = ChatTypeFilter(ChatType.DIALOG, ChatType.CHAT)
        msg = _make_message("dialog")
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_multiple_types_second_match(self) -> None:
        """chat — ChatTypeFilter(DIALOG, CHAT) -> True."""
        f = ChatTypeFilter(ChatType.DIALOG, ChatType.CHAT)
        msg = _make_message("chat")
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_multiple_types_no_match(self) -> None:
        """channel — ChatTypeFilter(DIALOG, CHAT) -> False."""
        f = ChatTypeFilter(ChatType.DIALOG, ChatType.CHAT)
        msg = _make_message("channel")
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_string_match(self) -> None:
        """Строковое значение 'dialog' -> True."""
        f = ChatTypeFilter("dialog")
        msg = _make_message("dialog")
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_from_update(self) -> None:
        """Из Update (с вложенным message) -> True."""
        f = ChatTypeFilter(ChatType.DIALOG)
        msg = _make_message("dialog")
        update = _FakeUpdate(msg)
        result = await f(update)
        assert result is True

    @pytest.mark.asyncio
    async def test_from_update_no_match(self) -> None:
        """Из Update — тип не совпал -> False."""
        f = ChatTypeFilter(ChatType.CHAT)
        msg = _make_message("dialog")
        update = _FakeUpdate(msg)
        result = await f(update)
        assert result is False

    @pytest.mark.asyncio
    async def test_no_args(self) -> None:
        """Без аргументов вызова -> False."""
        f = ChatTypeFilter(ChatType.DIALOG)
        result = await f()
        assert result is False

    @pytest.mark.asyncio
    async def test_invert(self) -> None:
        """~ChatTypeFilter инвертирует результат."""
        f = ~ChatTypeFilter(ChatType.DIALOG)
        msg = _make_message("dialog")
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_invert_no_match(self) -> None:
        """~ChatTypeFilter(DIALOG) на chat -> True."""
        f = ~ChatTypeFilter(ChatType.DIALOG)
        msg = _make_message("chat")
        result = await f(msg)
        assert result is True
