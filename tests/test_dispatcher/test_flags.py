"""Тесты FlagGenerator, get_flag, check_flag."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from maxogram.dispatcher.event.handler import HandlerObject
from maxogram.dispatcher.flags import FlagGenerator, check_flag, get_flag

# -- Вспомогательные функции --


async def dummy_handler(event: object) -> str:
    return "ok"


def make_data_with_flags(flags: dict[str, Any]) -> dict[str, Any]:
    """Создать data-dict с HandlerObject, содержащим заданные флаги."""
    handler_obj = HandlerObject(callback=dummy_handler, flags=flags)
    return {"handler": handler_obj}


# -- Тесты FlagGenerator --


class TestFlagGenerator:
    """Тесты для FlagGenerator."""

    def test_basic_flag_attribute(self) -> None:
        """FlagGenerator позволяет задавать флаг через атрибут-вызов."""
        flags = FlagGenerator()

        @flags.rate_limit("strict")
        async def handler(event: object) -> str:
            return "ok"

        # Флаг должен быть сохранён на функции
        assert hasattr(handler, "maxogram_flags")
        assert handler.maxogram_flags["rate_limit"] == "strict"

    def test_multiple_flags(self) -> None:
        """Несколько флагов на одном хендлере."""
        flags = FlagGenerator()

        @flags.rate_limit("default")
        @flags.priority(10)
        async def handler(event: object) -> str:
            return "ok"

        assert handler.maxogram_flags["rate_limit"] == "default"
        assert handler.maxogram_flags["priority"] == 10

    def test_flag_with_bool_value(self) -> None:
        """Флаг с булевым значением."""
        flags = FlagGenerator()

        @flags.admin_only(True)
        async def handler(event: object) -> str:
            return "ok"

        assert handler.maxogram_flags["admin_only"] is True

    def test_flag_with_dict_value(self) -> None:
        """Флаг со сложным значением."""
        flags = FlagGenerator()

        @flags.config({"timeout": 30, "retry": True})
        async def handler(event: object) -> str:
            return "ok"

        assert handler.maxogram_flags["config"] == {"timeout": 30, "retry": True}

    def test_flag_no_value_sets_true(self) -> None:
        """Флаг без значения устанавливает True."""
        flags = FlagGenerator()

        @flags.needs_auth()
        async def handler(event: object) -> str:
            return "ok"

        assert handler.maxogram_flags["needs_auth"] is True

    def test_flag_preserves_function(self) -> None:
        """Декоратор не меняет саму функцию."""
        flags = FlagGenerator()

        async def original_handler(event: object) -> str:
            return "original"

        decorated = flags.rate_limit("test")(original_handler)
        assert decorated is original_handler

    def test_flag_on_sync_function(self) -> None:
        """Флаг на синхронной функции."""
        flags = FlagGenerator()

        @flags.throttle("slow")
        def sync_handler(event: object) -> str:
            return "ok"

        assert sync_handler.maxogram_flags["throttle"] == "slow"

    def test_flag_generator_is_reusable(self) -> None:
        """Один FlagGenerator для разных хендлеров."""
        flags = FlagGenerator()

        @flags.rate_limit("fast")
        async def handler_a(event: object) -> str:
            return "a"

        @flags.rate_limit("slow")
        async def handler_b(event: object) -> str:
            return "b"

        assert handler_a.maxogram_flags["rate_limit"] == "fast"
        assert handler_b.maxogram_flags["rate_limit"] == "slow"


# -- Тесты get_flag --


class TestGetFlag:
    """Тесты для get_flag."""

    def test_get_existing_flag(self) -> None:
        """get_flag возвращает значение существующего флага."""
        data = make_data_with_flags({"rate_limit": "strict"})
        assert get_flag(data, "rate_limit") == "strict"

    def test_get_missing_flag_default_none(self) -> None:
        """get_flag для несуществующего флага — None."""
        data = make_data_with_flags({"rate_limit": "strict"})
        assert get_flag(data, "nonexistent") is None

    def test_get_missing_flag_custom_default(self) -> None:
        """get_flag с кастомным default."""
        data = make_data_with_flags({})
        assert get_flag(data, "rate_limit", default="default_val") == "default_val"

    def test_get_flag_no_handler_in_data(self) -> None:
        """get_flag без handler в data — default."""
        data: dict[str, Any] = {}
        assert get_flag(data, "anything") is None

    def test_get_flag_handler_without_flags(self) -> None:
        """get_flag с handler, у которого нет запрошенного флага."""
        data = make_data_with_flags({})
        assert get_flag(data, "rate_limit", default="fallback") == "fallback"


# -- Тесты check_flag --


class TestCheckFlag:
    """Тесты для check_flag."""

    def test_check_existing_flag_true(self) -> None:
        """check_flag для существующего флага — True."""
        data = make_data_with_flags({"rate_limit": "strict"})
        assert check_flag(data, "rate_limit") is True

    def test_check_missing_flag_false(self) -> None:
        """check_flag для несуществующего флага — False."""
        data = make_data_with_flags({})
        assert check_flag(data, "rate_limit") is False

    def test_check_flag_no_handler_false(self) -> None:
        """check_flag без handler в data — False."""
        data: dict[str, Any] = {}
        assert check_flag(data, "anything") is False

    def test_check_flag_with_false_value(self) -> None:
        """check_flag для флага со значением False — True (ключ есть)."""
        data = make_data_with_flags({"disabled": False})
        assert check_flag(data, "disabled") is True

    def test_check_flag_with_none_value(self) -> None:
        """check_flag для флага со значением None — True (ключ есть)."""
        data = make_data_with_flags({"nullable": None})
        assert check_flag(data, "nullable") is True


# -- Интеграционные тесты: FlagGenerator + observer --


class TestFlagsIntegration:
    """Интеграционные тесты: flags на хендлере → observer → middleware."""

    @pytest.mark.asyncio
    async def test_flags_from_decorator_available_in_data(self) -> None:
        """Флаги, заданные через FlagGenerator, доступны через data['handler'].flags."""
        from maxogram.dispatcher.event.max import MaxEventObserver

        flags = FlagGenerator()
        captured_flags: dict[str, Any] = {}

        @flags.rate_limit("strict")
        @flags.priority(5)
        async def handler(event: object, handler: HandlerObject | None = None) -> str:
            if handler:
                captured_flags.update(handler.flags)
            return "ok"

        observer = MaxEventObserver(event_name="test")
        observer.register(handler)

        await observer.trigger(MagicMock())

        assert captured_flags.get("rate_limit") == "strict"
        assert captured_flags.get("priority") == 5

    @pytest.mark.asyncio
    async def test_flags_kwarg_overrides_decorator(self) -> None:
        """Флаги через register(flags=...) имеют приоритет над декоратором."""
        from maxogram.dispatcher.event.max import MaxEventObserver

        flags = FlagGenerator()
        captured_flags: dict[str, Any] = {}

        @flags.rate_limit("from_decorator")
        async def handler(event: object, handler: HandlerObject | None = None) -> str:
            if handler:
                captured_flags.update(handler.flags)
            return "ok"

        observer = MaxEventObserver(event_name="test")
        observer.register(handler, flags={"rate_limit": "from_register"})

        await observer.trigger(MagicMock())

        assert captured_flags["rate_limit"] == "from_register"

    @pytest.mark.asyncio
    async def test_get_flag_in_middleware(self) -> None:
        """get_flag работает в middleware контексте."""
        from maxogram.dispatcher.event.max import MaxEventObserver
        from maxogram.dispatcher.middlewares.base import BaseMiddleware

        captured_value: dict[str, Any] = {}

        class FlagCheckMiddleware(BaseMiddleware):
            async def __call__(
                self,
                handler: Any,
                event: Any,
                data: dict[str, Any],
            ) -> Any:
                captured_value["rate_limit"] = get_flag(data, "rate_limit")
                captured_value["has_flag"] = check_flag(data, "rate_limit")
                return await handler(event, data)

        async def my_handler(event: object) -> str:
            return "ok"

        observer = MaxEventObserver(event_name="test")
        observer.register(my_handler, flags={"rate_limit": "strict"})
        observer.middleware.register(FlagCheckMiddleware())

        await observer.trigger(MagicMock())

        assert captured_value["rate_limit"] == "strict"
        assert captured_value["has_flag"] is True
