"""Тесты Command фильтра и CommandObject."""

from __future__ import annotations

import pytest

from maxogram.filters.command import Command, CommandObject
from maxogram.types.message import Message, MessageBody, Recipient


def _make_message(text: str | None) -> Message:
    """Создать минимальный Message с заданным текстом."""
    return Message(
        recipient=Recipient(chat_type="dialog"),  # type: ignore[arg-type]
        timestamp=1700000000000,
        body=MessageBody(mid="mid1", seq=1, text=text),
    )


class TestCommandObject:
    """Тесты для CommandObject (dataclass)."""

    def test_defaults(self) -> None:
        """CommandObject с дефолтными значениями."""
        obj = CommandObject()
        assert obj.prefix == "/"
        assert obj.command == ""
        assert obj.args is None
        assert obj.regexp_match is None

    def test_frozen(self) -> None:
        """CommandObject — frozen dataclass."""
        obj = CommandObject(command="start")
        with pytest.raises(AttributeError):
            obj.command = "other"  # type: ignore[misc]

    def test_custom_values(self) -> None:
        """CommandObject с пользовательскими значениями."""
        obj = CommandObject(prefix="!", command="help", args="arg1 arg2")
        assert obj.prefix == "!"
        assert obj.command == "help"
        assert obj.args == "arg1 arg2"


class TestCommandFilter:
    """Тесты для Command фильтра."""

    @pytest.mark.asyncio
    async def test_simple_command_match(self) -> None:
        """/start — Command('start') → True, command.command == 'start'."""
        f = Command("start")
        msg = _make_message("/start")
        result = await f(msg)
        assert isinstance(result, dict)
        assert result["command"].command == "start"
        assert result["command"].prefix == "/"
        assert result["command"].args is None

    @pytest.mark.asyncio
    async def test_command_with_args(self) -> None:
        """/start arg1 arg2 — args == 'arg1 arg2'."""
        f = Command("start")
        msg = _make_message("/start arg1 arg2")
        result = await f(msg)
        assert isinstance(result, dict)
        assert result["command"].command == "start"
        assert result["command"].args == "arg1 arg2"

    @pytest.mark.asyncio
    async def test_wrong_command(self) -> None:
        """/help — Command('start') → False."""
        f = Command("start")
        msg = _make_message("/help")
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_multiple_commands_match(self) -> None:
        """/start — Command('start', 'help') → True."""
        f = Command("start", "help")
        msg = _make_message("/start")
        result = await f(msg)
        assert isinstance(result, dict)
        assert result["command"].command == "start"

    @pytest.mark.asyncio
    async def test_multiple_commands_second(self) -> None:
        """/help — Command('start', 'help') → True."""
        f = Command("start", "help")
        msg = _make_message("/help")
        result = await f(msg)
        assert isinstance(result, dict)
        assert result["command"].command == "help"

    @pytest.mark.asyncio
    async def test_no_prefix_in_text(self) -> None:
        """hello — Command('start') → False (нет prefix)."""
        f = Command("start")
        msg = _make_message("hello")
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_custom_prefix(self) -> None:
        """!start — Command('start', prefix='!') → True."""
        f = Command("start", prefix="!")
        msg = _make_message("!start")
        result = await f(msg)
        assert isinstance(result, dict)
        assert result["command"].command == "start"
        assert result["command"].prefix == "!"

    @pytest.mark.asyncio
    async def test_custom_prefix_wrong(self) -> None:
        """/start — Command('start', prefix='!') → False."""
        f = Command("start", prefix="!")
        msg = _make_message("/start")
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_ignore_case_true(self) -> None:
        """/Start — Command('start', ignore_case=True) → True."""
        f = Command("start", ignore_case=True)
        msg = _make_message("/Start")
        result = await f(msg)
        assert isinstance(result, dict)
        assert result["command"].command == "Start"

    @pytest.mark.asyncio
    async def test_ignore_case_false(self) -> None:
        """/Start — Command('start', ignore_case=False) → False."""
        f = Command("start", ignore_case=False)
        msg = _make_message("/Start")
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_empty_text(self) -> None:
        """Пустой текст → False."""
        f = Command("start")
        msg = _make_message("")
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_none_text(self) -> None:
        """None текст → False."""
        f = Command("start")
        msg = _make_message(None)
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_mention_stripped(self) -> None:
        """/start@bot — command == 'start', mention убран."""
        f = Command("start")
        msg = _make_message("/start@bot")
        result = await f(msg)
        assert isinstance(result, dict)
        assert result["command"].command == "start"

    @pytest.mark.asyncio
    async def test_no_args_returns_none(self) -> None:
        """Команда без аргументов — args == None."""
        f = Command("help")
        msg = _make_message("/help")
        result = await f(msg)
        assert isinstance(result, dict)
        assert result["command"].args is None

    @pytest.mark.asyncio
    async def test_any_command_no_filter(self) -> None:
        """Command() без конкретных команд — любая команда проходит."""
        f = Command()
        msg = _make_message("/anything")
        result = await f(msg)
        assert isinstance(result, dict)
        assert result["command"].command == "anything"

    @pytest.mark.asyncio
    async def test_any_command_no_filter_with_args(self) -> None:
        """Command() — любая команда с аргументами."""
        f = Command()
        msg = _make_message("/test foo bar")
        result = await f(msg)
        assert isinstance(result, dict)
        assert result["command"].command == "test"
        assert result["command"].args == "foo bar"

    @pytest.mark.asyncio
    async def test_only_prefix(self) -> None:
        """Только / без команды → False."""
        f = Command("start")
        msg = _make_message("/")
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_mention_with_args(self) -> None:
        """/start@bot arg1 — command == 'start', args == 'arg1'."""
        f = Command("start")
        msg = _make_message("/start@bot arg1")
        result = await f(msg)
        assert isinstance(result, dict)
        assert result["command"].command == "start"
        assert result["command"].args == "arg1"

    @pytest.mark.asyncio
    async def test_is_filter_subclass(self) -> None:
        """Command — подкласс Filter."""
        from maxogram.filters.base import Filter

        assert issubclass(Command, Filter)

    @pytest.mark.asyncio
    async def test_invert_command(self) -> None:
        """~Command('start') инвертирует результат."""
        f = ~Command("start")
        msg = _make_message("/start")
        result = await f(msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_invert_command_no_match(self) -> None:
        """~Command('start') на другую команду → True."""
        f = ~Command("start")
        msg = _make_message("/help")
        result = await f(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_ignore_case_multiple_commands(self) -> None:
        """/HELP — Command('start', 'help', ignore_case=True) → True."""
        f = Command("start", "help", ignore_case=True)
        msg = _make_message("/HELP")
        result = await f(msg)
        assert isinstance(result, dict)
        assert result["command"].command == "HELP"

    @pytest.mark.asyncio
    async def test_multiword_args(self) -> None:
        """/start hello world foo — args с несколькими словами."""
        f = Command("start")
        msg = _make_message("/start hello world foo")
        result = await f(msg)
        assert isinstance(result, dict)
        assert result["command"].args == "hello world foo"

    @pytest.mark.asyncio
    async def test_command_with_extra_spaces_in_args(self) -> None:
        """/start  arg1  arg2 — внутренние пробелы в args сохраняются."""
        f = Command("start")
        msg = _make_message("/start  arg1  arg2")
        result = await f(msg)
        assert isinstance(result, dict)
        assert result["command"].args == "arg1  arg2"
