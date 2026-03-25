"""MemoryStorage, DisabledEventIsolation — in-memory FSM-хранилище."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping

from maxogram.fsm.storage.base import BaseEventIsolation, BaseStorage, StorageKey

__all__ = [
    "DisabledEventIsolation",
    "MemoryStorage",
]


class MemoryStorage(BaseStorage):
    """In-memory FSM storage.

    Данные теряются при перезапуске. Подходит для разработки и тестов.
    """

    def __init__(self) -> None:
        self._states: dict[StorageKey, str | None] = {}
        self._data: dict[StorageKey, dict[str, Any]] = {}

    async def set_state(
        self,
        key: StorageKey,
        state: str | None = None,
    ) -> None:
        """Установить состояние."""
        self._states[key] = state

    async def get_state(self, key: StorageKey) -> str | None:
        """Получить текущее состояние."""
        return self._states.get(key)

    async def set_data(
        self,
        key: StorageKey,
        data: Mapping[str, Any],
    ) -> None:
        """Полностью заменить данные."""
        self._data[key] = dict(data)

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        """Получить все данные."""
        return self._data.get(key, {}).copy()

    async def close(self) -> None:
        """Очистить хранилище."""
        self._states.clear()
        self._data.clear()


class DisabledEventIsolation(BaseEventIsolation):
    """No-op изоляция событий (без блокировки)."""

    @asynccontextmanager
    async def lock(
        self,
        key: StorageKey,
    ) -> AsyncGenerator[None, None]:
        """No-op lock — пропускает без блокировки."""
        yield

    async def close(self) -> None:
        """Ничего не делает."""
