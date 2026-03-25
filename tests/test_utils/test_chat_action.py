"""Тесты ChatActionSender — периодическая отправка chat actions."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from maxogram.enums import SenderAction
from maxogram.utils.chat_action import ChatActionSender


def _make_bot() -> AsyncMock:
    """Создать мок бота с send_action."""
    bot = AsyncMock()
    bot.send_action = AsyncMock()
    return bot


class TestBasicUsage:
    """Базовое использование ChatActionSender как async context manager."""

    @pytest.mark.asyncio
    async def test_sends_action_on_enter(self) -> None:
        """При входе в context manager action отправляется сразу."""
        bot = _make_bot()

        async with ChatActionSender(bot=bot, chat_id=123, action=SenderAction.TYPING_ON):
            await asyncio.sleep(0.05)

        # Хотя бы один вызов должен быть
        bot.send_action.assert_awaited()
        first_call = bot.send_action.await_args_list[0]
        assert first_call.kwargs["chat_id"] == 123
        assert first_call.kwargs["action"] == SenderAction.TYPING_ON

    @pytest.mark.asyncio
    async def test_stops_sending_on_exit(self) -> None:
        """При выходе из context manager периодическая отправка прекращается."""
        bot = _make_bot()

        async with ChatActionSender(bot=bot, chat_id=123, action=SenderAction.TYPING_ON):
            pass

        call_count_after_exit = bot.send_action.await_count
        await asyncio.sleep(0.15)
        # После выхода новых вызовов быть не должно
        assert bot.send_action.await_count == call_count_after_exit

    @pytest.mark.asyncio
    async def test_periodic_sending(self) -> None:
        """Action отправляется периодически с заданным интервалом."""
        bot = _make_bot()

        async with ChatActionSender(
            bot=bot,
            chat_id=456,
            action=SenderAction.SENDING_PHOTO,
            interval=0.05,
        ):
            await asyncio.sleep(0.18)

        # За 0.18 сек при интервале 0.05 должно быть >= 3 вызова
        # (один сразу + ~3 периодических)
        assert bot.send_action.await_count >= 3


class TestDifferentActions:
    """ChatActionSender работает с разными SenderAction."""

    @pytest.mark.asyncio
    async def test_sending_file_action(self) -> None:
        """SenderAction.SENDING_FILE отправляется корректно."""
        bot = _make_bot()

        async with ChatActionSender(bot=bot, chat_id=789, action=SenderAction.SENDING_FILE):
            await asyncio.sleep(0.05)

        call = bot.send_action.await_args_list[0]
        assert call.kwargs["action"] == SenderAction.SENDING_FILE

    @pytest.mark.asyncio
    async def test_mark_seen_action(self) -> None:
        """SenderAction.MARK_SEEN отправляется корректно."""
        bot = _make_bot()

        async with ChatActionSender(bot=bot, chat_id=100, action=SenderAction.MARK_SEEN):
            await asyncio.sleep(0.05)

        call = bot.send_action.await_args_list[0]
        assert call.kwargs["action"] == SenderAction.MARK_SEEN


class TestCustomInterval:
    """Кастомный интервал между отправками."""

    @pytest.mark.asyncio
    async def test_default_interval(self) -> None:
        """По умолчанию интервал 5 секунд."""
        sender = ChatActionSender(bot=_make_bot(), chat_id=1, action=SenderAction.TYPING_ON)
        assert sender.interval == 5.0

    @pytest.mark.asyncio
    async def test_custom_interval(self) -> None:
        """Кастомный интервал сохраняется."""
        sender = ChatActionSender(
            bot=_make_bot(), chat_id=1, action=SenderAction.TYPING_ON, interval=2.0
        )
        assert sender.interval == 2.0


class TestErrorHandling:
    """Ошибки API не ломают ChatActionSender."""

    @pytest.mark.asyncio
    async def test_api_error_does_not_stop_sender(self) -> None:
        """Ошибка send_action не прерывает context manager."""
        bot = _make_bot()
        call_count = 0

        async def flaky_send_action(**kwargs: Any) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                msg = "API error"
                raise Exception(msg)  # noqa: TRY002

        bot.send_action.side_effect = flaky_send_action

        # Не должно бросать исключение
        async with ChatActionSender(
            bot=bot, chat_id=1, action=SenderAction.TYPING_ON, interval=0.05
        ):
            await asyncio.sleep(0.15)

        # Были повторные вызовы после ошибки
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_user_exception_propagates(self) -> None:
        """Исключение в пользовательском коде пробрасывается нормально."""
        bot = _make_bot()

        with pytest.raises(ValueError, match="user error"):
            async with ChatActionSender(bot=bot, chat_id=1, action=SenderAction.TYPING_ON):
                msg = "user error"
                raise ValueError(msg)


class TestClassmethods:
    """Фабричные методы для типичных действий."""

    @pytest.mark.asyncio
    async def test_typing(self) -> None:
        """ChatActionSender.typing() — shortcut для TYPING_ON."""
        bot = _make_bot()

        async with ChatActionSender.typing(bot=bot, chat_id=1):
            await asyncio.sleep(0.05)

        call = bot.send_action.await_args_list[0]
        assert call.kwargs["action"] == SenderAction.TYPING_ON

    @pytest.mark.asyncio
    async def test_upload_photo(self) -> None:
        """ChatActionSender.upload_photo() — shortcut для SENDING_PHOTO."""
        bot = _make_bot()

        async with ChatActionSender.upload_photo(bot=bot, chat_id=1):
            await asyncio.sleep(0.05)

        call = bot.send_action.await_args_list[0]
        assert call.kwargs["action"] == SenderAction.SENDING_PHOTO

    @pytest.mark.asyncio
    async def test_upload_video(self) -> None:
        """ChatActionSender.upload_video() — shortcut для SENDING_VIDEO."""
        bot = _make_bot()

        async with ChatActionSender.upload_video(bot=bot, chat_id=1):
            await asyncio.sleep(0.05)

        call = bot.send_action.await_args_list[0]
        assert call.kwargs["action"] == SenderAction.SENDING_VIDEO

    @pytest.mark.asyncio
    async def test_upload_audio(self) -> None:
        """ChatActionSender.upload_audio() — shortcut для SENDING_AUDIO."""
        bot = _make_bot()

        async with ChatActionSender.upload_audio(bot=bot, chat_id=1):
            await asyncio.sleep(0.05)

        call = bot.send_action.await_args_list[0]
        assert call.kwargs["action"] == SenderAction.SENDING_AUDIO

    @pytest.mark.asyncio
    async def test_upload_file(self) -> None:
        """ChatActionSender.upload_file() — shortcut для SENDING_FILE."""
        bot = _make_bot()

        async with ChatActionSender.upload_file(bot=bot, chat_id=1):
            await asyncio.sleep(0.05)

        call = bot.send_action.await_args_list[0]
        assert call.kwargs["action"] == SenderAction.SENDING_FILE
