"""Тесты I18nMiddleware — middleware для интернационализации."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from maxogram.i18n.core import I18n
from maxogram.i18n.middleware import I18nMiddleware
from tests.test_i18n.test_core import _create_mo_file

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def locale_dir(tmp_path: Path) -> Path:
    """Создать временную директорию с переводами."""
    _create_mo_file("ru", "messages", {"Hello": "Привет"}, tmp_path)
    _create_mo_file("en", "messages", {"Hello": "Hello!"}, tmp_path)
    return tmp_path


@pytest.fixture()
def i18n(locale_dir: Path) -> I18n:
    """Создать I18n менеджер."""
    return I18n(path=locale_dir, default_locale="en")


async def _capture_handler(event: Any, data: dict[str, Any]) -> dict[str, Any]:
    """Хендлер-заглушка, возвращающий data для проверки."""
    return dict(data)


class TestI18nMiddlewareIsBaseMiddleware:
    """I18nMiddleware наследует BaseMiddleware."""

    def test_is_subclass(self, i18n: I18n) -> None:
        from maxogram.dispatcher.middlewares.base import BaseMiddleware

        mw = I18nMiddleware(i18n=i18n)
        assert isinstance(mw, BaseMiddleware)


class TestI18nMiddlewareLocaleFromEvent:
    """Middleware извлекает user_locale из события."""

    @pytest.mark.asyncio
    async def test_uses_user_locale_from_event(self, i18n: I18n) -> None:
        """user_locale из event → устанавливается в контекст."""

        class FakeEvent:
            user_locale: str | None = "ru"

        mw = I18nMiddleware(i18n=i18n)
        result = await mw(_capture_handler, FakeEvent(), {})

        assert result["i18n"] is i18n
        assert result["i18n_locale"] == "ru"

    @pytest.mark.asyncio
    async def test_no_user_locale_uses_default(self, i18n: I18n) -> None:
        """Без user_locale — fallback на default_locale."""

        class FakeEvent:
            user_locale: str | None = None

        mw = I18nMiddleware(i18n=i18n)
        result = await mw(_capture_handler, FakeEvent(), {})

        assert result["i18n_locale"] == "en"

    @pytest.mark.asyncio
    async def test_no_user_locale_attr_uses_default(self, i18n: I18n) -> None:
        """Событие без атрибута user_locale — fallback на default_locale."""

        class FakeEvent:
            pass

        mw = I18nMiddleware(i18n=i18n)
        result = await mw(_capture_handler, FakeEvent(), {})

        assert result["i18n_locale"] == "en"


class TestI18nMiddlewareCustomLocaleResolver:
    """I18nMiddleware с пользовательским locale resolver."""

    @pytest.mark.asyncio
    async def test_custom_resolver(self, i18n: I18n) -> None:
        """Пользовательский resolver определяет локаль."""

        async def my_resolver(event: Any, data: dict[str, Any]) -> str:
            return "ru"

        class FakeEvent:
            pass

        mw = I18nMiddleware(i18n=i18n, locale_resolver=my_resolver)
        result = await mw(_capture_handler, FakeEvent(), {})

        assert result["i18n_locale"] == "ru"

    @pytest.mark.asyncio
    async def test_custom_resolver_overrides_event(self, i18n: I18n) -> None:
        """Если есть resolver — event.user_locale игнорируется."""

        async def my_resolver(event: Any, data: dict[str, Any]) -> str:
            return "en"

        class FakeEvent:
            user_locale: str = "ru"

        mw = I18nMiddleware(i18n=i18n, locale_resolver=my_resolver)
        result = await mw(_capture_handler, FakeEvent(), {})

        assert result["i18n_locale"] == "en"


class TestI18nMiddlewareSetsContextvar:
    """Middleware устанавливает current_locale через contextvars."""

    @pytest.mark.asyncio
    async def test_current_locale_set_during_handler(self, i18n: I18n) -> None:
        """Внутри handler current_locale установлен."""
        captured_locale: str | None = None

        async def handler(event: Any, data: dict[str, Any]) -> None:
            nonlocal captured_locale
            captured_locale = i18n.current_locale.get()

        class FakeEvent:
            user_locale: str = "ru"

        mw = I18nMiddleware(i18n=i18n)
        await mw(handler, FakeEvent(), {})

        assert captured_locale == "ru"

    @pytest.mark.asyncio
    async def test_current_locale_reset_after_handler(self, i18n: I18n) -> None:
        """После завершения handler current_locale сбрасывается."""

        class FakeEvent:
            user_locale: str = "ru"

        mw = I18nMiddleware(i18n=i18n)
        await mw(_capture_handler, FakeEvent(), {})

        # current_locale должен быть сброшен (LookupError или default)
        # По умолчанию contextvar не установлен после reset
        with pytest.raises(LookupError):
            i18n.current_locale.get()


class TestI18nMiddlewareInjectsGettext:
    """Middleware добавляет gettext/ngettext функции в data."""

    @pytest.mark.asyncio
    async def test_gettext_in_data(self, i18n: I18n) -> None:
        """data содержит gettext, привязанный к текущей локали."""

        class FakeEvent:
            user_locale: str = "ru"

        captured_gettext: Any = None

        async def handler(event: Any, data: dict[str, Any]) -> None:
            nonlocal captured_gettext
            captured_gettext = data.get("gettext")

        mw = I18nMiddleware(i18n=i18n)
        await mw(handler, FakeEvent(), {})

        assert captured_gettext is not None

    @pytest.mark.asyncio
    async def test_gettext_translates(self, i18n: I18n) -> None:
        """gettext из data переводит строку."""
        translated: str | None = None

        async def handler(event: Any, data: dict[str, Any]) -> None:
            nonlocal translated
            _ = data["gettext"]
            translated = _("Hello")

        class FakeEvent:
            user_locale: str = "ru"

        mw = I18nMiddleware(i18n=i18n)
        await mw(handler, FakeEvent(), {})

        assert translated == "Привет"


class TestI18nMiddlewarePassesThrough:
    """Middleware вызывает handler и возвращает результат."""

    @pytest.mark.asyncio
    async def test_returns_handler_result(self, i18n: I18n) -> None:
        async def handler(event: Any, data: dict[str, Any]) -> str:
            return "handler_result"

        class FakeEvent:
            user_locale: str = "ru"

        mw = I18nMiddleware(i18n=i18n)
        result = await mw(handler, FakeEvent(), {})

        assert result == "handler_result"

    @pytest.mark.asyncio
    async def test_preserves_existing_data(self, i18n: I18n) -> None:
        """Middleware не затирает существующие ключи в data."""

        async def handler(event: Any, data: dict[str, Any]) -> dict[str, Any]:
            return dict(data)

        class FakeEvent:
            user_locale: str = "ru"

        mw = I18nMiddleware(i18n=i18n)
        result = await mw(handler, FakeEvent(), {"existing_key": "value"})

        assert result["existing_key"] == "value"
        assert "i18n" in result
