"""I18n — менеджер переводов на основе GNU gettext / Babel."""

from __future__ import annotations

import gettext as gettext_module
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from maxogram.i18n.lazy import LazyProxy

__all__ = ["I18n"]


class I18n:
    """Менеджер интернационализации.

    Загружает .mo файлы из указанной директории, предоставляет
    функции gettext/ngettext и ленивый gettext через LazyProxy.

    Пример::

        i18n = I18n(path=Path("locales"), default_locale="ru")
        _ = i18n.gettext
        print(_("Hello", locale="ru"))  # → "Привет"

    Структура директории переводов::

        locales/
        ├── ru/
        │   └── LC_MESSAGES/
        │       └── messages.mo
        └── en/
            └── LC_MESSAGES/
                └── messages.mo
    """

    def __init__(
        self,
        *,
        path: Path | str,
        domain: str = "messages",
        default_locale: str = "en",
    ) -> None:
        self.path = Path(path)
        self.domain = domain
        self.default_locale = default_locale
        self.current_locale: ContextVar[str] = ContextVar("i18n_current_locale")

        # Кэш загруженных переводов: locale → NullTranslations/GNUTranslations
        self._translations: dict[str, gettext_module.NullTranslations] = {}

    def _get_translations(self, locale: str) -> gettext_module.NullTranslations:
        """Получить объект переводов для указанной локали.

        Загружает .mo файл при первом обращении и кэширует.
        При отсутствии файла возвращает NullTranslations (passthrough).
        """
        if locale in self._translations:
            return self._translations[locale]

        try:
            translations = gettext_module.translation(
                domain=self.domain,
                localedir=str(self.path),
                languages=[locale],
            )
            self._translations[locale] = translations
            return translations
        except FileNotFoundError:
            # Fallback на default_locale (если не рекурсия)
            if locale != self.default_locale:
                return self._get_translations(self.default_locale)
            return gettext_module.NullTranslations()

    def _resolve_locale(self, locale: str | None) -> str:
        """Определить активную локаль.

        Приоритет:
        1. Явно переданный параметр locale
        2. current_locale из contextvars
        3. default_locale
        """
        if locale is not None:
            return locale
        try:
            return self.current_locale.get()
        except LookupError:
            return self.default_locale

    def gettext(self, message: str, *, locale: str | None = None) -> str:
        """Перевести строку.

        Args:
            message: Строка для перевода (msgid).
            locale: Локаль. Если не указана — берётся из current_locale или default_locale.

        Returns:
            Переведённая строка или оригинал, если перевод не найден.
        """
        resolved_locale = self._resolve_locale(locale)
        translations = self._get_translations(resolved_locale)
        return translations.gettext(message)

    def ngettext(
        self,
        singular: str,
        plural: str,
        n: int,
        *,
        locale: str | None = None,
    ) -> str:
        """Перевести строку с учётом множественного числа.

        Args:
            singular: Форма единственного числа (msgid).
            plural: Форма множественного числа (msgid_plural).
            n: Число для определения формы.
            locale: Локаль.

        Returns:
            Правильная форма перевода.
        """
        resolved_locale = self._resolve_locale(locale)
        translations = self._get_translations(resolved_locale)
        return translations.ngettext(singular, plural, n)

    def lazy_gettext(self, message: str, **kwargs: Any) -> LazyProxy:
        """Ленивый перевод — вычисляется при обращении к str().

        Используется для определения переводов на уровне модуля,
        когда locale ещё не известен.

        Args:
            message: Строка для перевода.
            **kwargs: Дополнительные аргументы для gettext.

        Returns:
            LazyProxy, который при str() вызовет gettext с текущей локалью.
        """
        return LazyProxy(self.gettext, message, **kwargs)
