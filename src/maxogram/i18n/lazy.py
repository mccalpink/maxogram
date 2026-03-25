"""LazyProxy — ленивая строка, вычисляемая при обращении к str/format."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


__all__ = ["LazyProxy"]


class LazyProxy:
    """Прокси-объект, который вызывает функцию при каждом обращении к строковому значению.

    Позволяет определять переводы на этапе загрузки модуля,
    а вычислять их в момент фактического использования (когда locale уже установлен).

    Пример::

        from maxogram.i18n import I18n

        i18n = I18n(path="locales")
        _ = i18n.lazy_gettext
        WELCOME = _("Welcome!")  # LazyProxy, не строка
        # При str(WELCOME) — вычислится с текущей локалью
    """

    __slots__ = ("_func", "_args", "_kwargs")

    _func: Callable[..., str]
    _args: tuple[Any, ...]
    _kwargs: dict[str, Any]

    def __init__(
        self,
        func: Callable[..., str],
        /,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        object.__setattr__(self, "_func", func)
        object.__setattr__(self, "_args", args)
        object.__setattr__(self, "_kwargs", kwargs)

    def _resolve(self) -> str:
        """Вызвать функцию и получить строковое значение."""
        return str(self._func(*self._args, **self._kwargs))

    def __str__(self) -> str:
        return self._resolve()

    def __repr__(self) -> str:
        return f"LazyProxy({self._resolve()!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, LazyProxy):
            return self._resolve() == other._resolve()
        if isinstance(other, str):
            return self._resolve() == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._resolve())

    def __add__(self, other: str) -> str:
        return self._resolve() + other

    def __radd__(self, other: str) -> str:
        return other + self._resolve()

    def __mod__(self, args: Any) -> str:
        result: str = self._resolve() % args
        return result

    def __len__(self) -> int:
        return len(self._resolve())

    def __contains__(self, item: str) -> bool:
        return item in self._resolve()

    def __getitem__(self, key: Any) -> str:
        result: str = self._resolve()[key]
        return result

    def __bool__(self) -> bool:
        return bool(self._resolve())

    def __iter__(self) -> Iterator[str]:
        return iter(self._resolve())

    def format(self, *args: Any, **kwargs: Any) -> str:
        """Форматирование строки."""
        return self._resolve().format(*args, **kwargs)

    def upper(self) -> str:
        """Перевод в верхний регистр."""
        return self._resolve().upper()

    def lower(self) -> str:
        """Перевод в нижний регистр."""
        return self._resolve().lower()
