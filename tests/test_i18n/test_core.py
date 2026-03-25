"""Тесты I18n — менеджер переводов, gettext, ngettext."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from maxogram.i18n.core import I18n


def _create_mo_file(
    locale: str,
    domain: str,
    translations: dict[str, str],
    base_dir: Path,
    *,
    plural_translations: dict[tuple[str, str, int], list[str]] | None = None,
) -> None:
    """Создать .mo файл из словаря переводов.

    Для plural_translations ключ — (singular, plural, n),
    значение — список форм [форма0, форма1, ...].
    """
    locale_dir = base_dir / locale / "LC_MESSAGES"
    locale_dir.mkdir(parents=True, exist_ok=True)
    po_path = locale_dir / f"{domain}.po"

    # Minimal PO header
    lines = [
        'msgid ""',
        'msgstr ""',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '"Plural-Forms: nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 '
        '&& (n%100<10 || n%100>=20) ? 1 : 2);\\n"',
        "",
    ]

    for msgid, msgstr in translations.items():
        lines.append(f'msgid "{msgid}"')
        lines.append(f'msgstr "{msgstr}"')
        lines.append("")

    if plural_translations:
        for (singular, plural, _n), forms in plural_translations.items():
            lines.append(f'msgid "{singular}"')
            lines.append(f'msgid_plural "{plural}"')
            for i, form in enumerate(forms):
                lines.append(f'msgstr[{i}] "{form}"')
            lines.append("")

    po_path.write_text("\n".join(lines), encoding="utf-8")

    # Compile PO → MO using msgfmt from babel
    from babel.messages.mofile import write_mo
    from babel.messages.pofile import read_po

    with open(po_path, "rb") as po_file:
        catalog = read_po(po_file, locale=locale)

    mo_path = locale_dir / f"{domain}.mo"
    with open(mo_path, "wb") as mo_file:
        write_mo(mo_file, catalog)


@pytest.fixture()
def locale_dir(tmp_path: Path) -> Path:
    """Создать временную директорию с переводами для ru и en."""
    _create_mo_file(
        "ru",
        "messages",
        {"Hello": "Привет", "Goodbye": "До свидания"},
        tmp_path,
        plural_translations={
            ("{n} apple", "{n} apples", 3): [
                "{n} яблоко",
                "{n} яблока",
                "{n} яблок",
            ],
        },
    )
    _create_mo_file(
        "en",
        "messages",
        {"Hello": "Hello!", "Goodbye": "Bye!"},
        tmp_path,
    )
    return tmp_path


@pytest.fixture()
def custom_domain_dir(tmp_path: Path) -> Path:
    """Создать переводы с кастомным domain."""
    _create_mo_file("ru", "bot_messages", {"Start": "Начало"}, tmp_path)
    return tmp_path


class TestI18nInit:
    """Инициализация I18n менеджера."""

    def test_creates_with_path(self, locale_dir: Path) -> None:
        i18n = I18n(path=locale_dir)
        assert i18n.path == locale_dir

    def test_default_domain(self, locale_dir: Path) -> None:
        i18n = I18n(path=locale_dir)
        assert i18n.domain == "messages"

    def test_custom_domain(self, custom_domain_dir: Path) -> None:
        i18n = I18n(path=custom_domain_dir, domain="bot_messages")
        assert i18n.domain == "bot_messages"

    def test_default_locale(self, locale_dir: Path) -> None:
        i18n = I18n(path=locale_dir, default_locale="en")
        assert i18n.default_locale == "en"

    def test_default_locale_fallback(self, locale_dir: Path) -> None:
        """Без указания default_locale — 'en'."""
        i18n = I18n(path=locale_dir)
        assert i18n.default_locale == "en"


class TestI18nGettext:
    """I18n.gettext() — получение перевода."""

    def test_gettext_returns_translation(self, locale_dir: Path) -> None:
        i18n = I18n(path=locale_dir)
        result = i18n.gettext("Hello", locale="ru")
        assert result == "Привет"

    def test_gettext_different_locale(self, locale_dir: Path) -> None:
        i18n = I18n(path=locale_dir)
        result = i18n.gettext("Hello", locale="en")
        assert result == "Hello!"

    def test_gettext_unknown_key_returns_key(self, locale_dir: Path) -> None:
        """Неизвестный ключ — возвращается оригинальная строка."""
        i18n = I18n(path=locale_dir)
        result = i18n.gettext("Unknown key", locale="ru")
        assert result == "Unknown key"

    def test_gettext_unknown_locale_uses_default(self, locale_dir: Path) -> None:
        """Неизвестная локаль — fallback на default_locale."""
        i18n = I18n(path=locale_dir, default_locale="en")
        result = i18n.gettext("Hello", locale="fr")
        assert result == "Hello!"

    def test_gettext_no_locale_uses_default(self, locale_dir: Path) -> None:
        """Без указания locale — используется default_locale."""
        i18n = I18n(path=locale_dir, default_locale="ru")
        result = i18n.gettext("Hello")
        assert result == "Привет"

    def test_gettext_custom_domain(self, custom_domain_dir: Path) -> None:
        i18n = I18n(path=custom_domain_dir, domain="bot_messages")
        result = i18n.gettext("Start", locale="ru")
        assert result == "Начало"


class TestI18nNgettext:
    """I18n.ngettext() — plural forms."""

    def test_ngettext_singular(self, locale_dir: Path) -> None:
        i18n = I18n(path=locale_dir)
        result = i18n.ngettext("{n} apple", "{n} apples", 1, locale="ru")
        assert result == "{n} яблоко"

    def test_ngettext_few(self, locale_dir: Path) -> None:
        i18n = I18n(path=locale_dir)
        result = i18n.ngettext("{n} apple", "{n} apples", 3, locale="ru")
        assert result == "{n} яблока"

    def test_ngettext_many(self, locale_dir: Path) -> None:
        i18n = I18n(path=locale_dir)
        result = i18n.ngettext("{n} apple", "{n} apples", 5, locale="ru")
        assert result == "{n} яблок"

    def test_ngettext_unknown_locale_fallback(self, locale_dir: Path) -> None:
        """Неизвестная локаль — fallback возвращает singular/plural по n."""
        i18n = I18n(path=locale_dir, default_locale="en")
        result = i18n.ngettext("{n} apple", "{n} apples", 1, locale="xx")
        # en locale не имеет plural translations, fallback на оригинал
        assert "{n} apple" in result


class TestI18nCurrentLocale:
    """I18n.current_locale — контекстная переменная."""

    def test_set_and_get_current_locale(self, locale_dir: Path) -> None:
        i18n = I18n(path=locale_dir)
        token = i18n.current_locale.set("ru")
        try:
            assert i18n.current_locale.get() == "ru"
        finally:
            i18n.current_locale.reset(token)

    def test_gettext_uses_current_locale(self, locale_dir: Path) -> None:
        """gettext() без параметра locale берёт current_locale из contextvars."""
        i18n = I18n(path=locale_dir, default_locale="en")
        token = i18n.current_locale.set("ru")
        try:
            result = i18n.gettext("Hello")
            assert result == "Привет"
        finally:
            i18n.current_locale.reset(token)


class TestI18nLazyGettext:
    """I18n.lazy_gettext() — ленивые переводы через LazyProxy."""

    def test_lazy_gettext_resolves_on_str(self, locale_dir: Path) -> None:
        i18n = I18n(path=locale_dir, default_locale="ru")
        lazy = i18n.lazy_gettext("Hello")
        token = i18n.current_locale.set("ru")
        try:
            assert str(lazy) == "Привет"
        finally:
            i18n.current_locale.reset(token)

    def test_lazy_gettext_changes_with_locale(self, locale_dir: Path) -> None:
        i18n = I18n(path=locale_dir)
        lazy = i18n.lazy_gettext("Hello")

        token = i18n.current_locale.set("ru")
        try:
            assert str(lazy) == "Привет"
        finally:
            i18n.current_locale.reset(token)

        token = i18n.current_locale.set("en")
        try:
            assert str(lazy) == "Hello!"
        finally:
            i18n.current_locale.reset(token)
