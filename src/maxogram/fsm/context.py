"""FSMContext — контекст FSM для конкретного пользователя/чата."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

    from maxogram.fsm.state import State
    from maxogram.fsm.storage.base import BaseStorage, StorageKey

__all__ = ["FSMContext"]


class FSMContext:
    """Контекст FSM для конкретного пользователя/чата.

    Предоставляет удобный интерфейс для управления состоянием и данными.
    Создаётся FSMContextMiddleware и передаётся в хендлер как ``state``.
    """

    def __init__(self, storage: BaseStorage, key: StorageKey) -> None:
        self.storage = storage
        self.key = key

    async def set_state(self, state: State | str | None = None) -> None:
        """Установить состояние.

        Принимает State-объект, строку или None.
        """
        raw = state if isinstance(state, str) or state is None else state.state
        await self.storage.set_state(self.key, raw)

    async def get_state(self) -> str | None:
        """Получить текущее состояние."""
        return await self.storage.get_state(self.key)

    async def set_data(self, data: Mapping[str, Any]) -> None:
        """Полностью заменить данные."""
        await self.storage.set_data(self.key, data)

    async def get_data(self) -> dict[str, Any]:
        """Получить все данные."""
        return await self.storage.get_data(self.key)

    async def get_value(self, key: str, default: Any = None) -> Any:
        """Получить одно значение."""
        return await self.storage.get_value(self.key, key, default)

    async def update_data(
        self,
        data: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Обновить данные (merge). Возвращает обновлённый dict."""
        # Объединяем data и kwargs здесь, чтобы избежать конфликта
        # параметра "key" при передаче в storage.update_data(key=StorageKey)
        merged: dict[str, Any] = {}
        if data:
            merged.update(data)
        if kwargs:
            merged.update(kwargs)
        return await self.storage.update_data(self.key, merged)

    async def clear(self) -> None:
        """Очистить состояние и данные."""
        await self.set_state(None)
        await self.set_data({})
