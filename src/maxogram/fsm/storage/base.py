"""BaseStorage, StorageKey, BaseEventIsolation — абстракции FSM-хранилища."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping

__all__ = [
    "BaseEventIsolation",
    "BaseStorage",
    "StorageKey",
]

DEFAULT_DESTINY = "default"


@dataclass(frozen=True)
class StorageKey:
    """Ключ для идентификации FSM-контекста.

    Отличие от aiogram: нет ``thread_id`` и ``business_connection_id``
    (Max не поддерживает Forum Topics).
    """

    bot_id: int
    chat_id: int
    user_id: int
    destiny: str = DEFAULT_DESTINY


class BaseStorage(ABC):
    """Абстрактный базовый класс FSM-хранилища."""

    @abstractmethod
    async def set_state(
        self,
        key: StorageKey,
        state: str | None = None,
    ) -> None:
        """Установить состояние."""

    @abstractmethod
    async def get_state(self, key: StorageKey) -> str | None:
        """Получить текущее состояние."""

    @abstractmethod
    async def set_data(
        self,
        key: StorageKey,
        data: Mapping[str, Any],
    ) -> None:
        """Полностью заменить данные."""

    @abstractmethod
    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        """Получить все данные."""

    @abstractmethod
    async def close(self) -> None:
        """Закрыть хранилище и освободить ресурсы."""

    async def get_value(
        self,
        key: StorageKey,
        dict_key: str,
        default: Any = None,
    ) -> Any:
        """Получить одно значение из данных."""
        data = await self.get_data(key)
        return data.get(dict_key, default)

    async def update_data(
        self,
        key: StorageKey,
        data: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Обновить данные (merge). Возвращает обновлённый dict."""
        current = await self.get_data(key)
        if data:
            current.update(data)
        if kwargs:
            current.update(kwargs)
        await self.set_data(key, current)
        return current


class BaseEventIsolation(ABC):
    """Абстрактный базовый класс для изоляции FSM-событий."""

    @abstractmethod
    @asynccontextmanager
    async def lock(
        self,
        key: StorageKey,
    ) -> AsyncGenerator[None, None]:
        """Захватить lock для ключа."""
        yield

    @abstractmethod
    async def close(self) -> None:
        """Закрыть и освободить ресурсы."""
