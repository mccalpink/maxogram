"""Базовый класс для всех типов Max API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, PrivateAttr

if TYPE_CHECKING:
    from collections.abc import Iterator


class MaxObject(BaseModel):
    """Базовый класс всех типов Max API.

    Конфигурация:
    - extra="allow" — новые поля от API не вызывают ошибку (forward-compatibility)
    - use_enum_values=True — enum-ы сериализуются в строковые значения
    - populate_by_name=True — доступ и по alias, и по имени поля
    - validate_default=True — дефолтные значения тоже валидируются
    """

    model_config = ConfigDict(
        use_enum_values=True,
        extra="allow",
        validate_default=True,
        populate_by_name=True,
    )

    _bot: Any = PrivateAttr(default=None)

    def set_bot(self, bot: Any) -> None:
        """Установить ссылку на Bot (для shortcuts: message.answer и т.д.)."""
        self._bot = bot
        for value in self._iter_nested():
            value._bot = bot

    @property
    def bot(self) -> Any:
        """Получить ссылку на Bot."""
        if self._bot is None:
            msg = "Bot is not set. This object was not received from the API."
            raise RuntimeError(msg)
        return self._bot

    def _iter_nested(self) -> Iterator[MaxObject]:
        """Итерировать по вложенным MaxObject (для рекурсивного set_bot)."""
        for field_name in self.__class__.model_fields:
            value = getattr(self, field_name, None)
            if isinstance(value, MaxObject):
                yield value
                yield from value._iter_nested()
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, MaxObject):
                        yield item
                        yield from item._iter_nested()
