"""I18nMiddleware — middleware для интернационализации."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from maxogram.dispatcher.middlewares.base import BaseMiddleware

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from maxogram.i18n.core import I18n

__all__ = ["I18nMiddleware"]


class I18nMiddleware(BaseMiddleware):
    """Middleware для автоматического определения локали и настройки переводов.

    Определяет локаль из event data (user_locale из webhook payload),
    устанавливает текущий перевод в contextvars, добавляет в data:
    - ``i18n``: экземпляр :class:`I18n`
    - ``i18n_locale``: определённая локаль
    - ``gettext``: функция перевода, привязанная к текущей локали

    Пример::

        from maxogram.i18n import I18n, I18nMiddleware

        i18n = I18n(path="locales", default_locale="ru")
        dp.update.outer_middleware(I18nMiddleware(i18n=i18n))

        @router.message_created()
        async def handler(event, gettext, **kwargs):
            _ = gettext
            await event.message.answer(_("Hello!"))
    """

    def __init__(
        self,
        *,
        i18n: I18n,
        locale_resolver: (Callable[[Any, dict[str, Any]], Awaitable[str]] | None) = None,
    ) -> None:
        self._i18n = i18n
        self._locale_resolver = locale_resolver

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        """Определить локаль, установить контекст, вызвать handler."""
        locale = await self._resolve_locale(event, data)

        # Установить current_locale в contextvars
        token = self._i18n.current_locale.set(locale)
        try:
            # Добавить в data для DI
            data["i18n"] = self._i18n
            data["i18n_locale"] = locale
            data["gettext"] = self._make_gettext(locale)

            return await handler(event, data)
        finally:
            self._i18n.current_locale.reset(token)

    async def _resolve_locale(self, event: Any, data: dict[str, Any]) -> str:
        """Определить локаль для текущего запроса.

        Приоритет:
        1. Пользовательский locale_resolver (если задан)
        2. event.user_locale (из webhook payload)
        3. default_locale из I18n
        """
        if self._locale_resolver is not None:
            return await self._locale_resolver(event, data)

        user_locale: str | None = getattr(event, "user_locale", None)
        if user_locale:
            return user_locale

        return self._i18n.default_locale

    def _make_gettext(self, locale: str) -> Callable[[str], str]:
        """Создать функцию gettext, привязанную к конкретной локали."""

        def gettext(message: str) -> str:
            return self._i18n.gettext(message, locale=locale)

        return gettext
