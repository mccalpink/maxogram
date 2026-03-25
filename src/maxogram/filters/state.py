"""Фильтр по FSM-состоянию."""

from __future__ import annotations

from typing import Any

from maxogram.filters.base import Filter
from maxogram.fsm.state import State

__all__ = ["StateFilter"]


class StateFilter(Filter):
    """Фильтр по FSM-состоянию.

    Проверяет raw_state (инжектируется FSMContextMiddleware) на совпадение
    с одним из указанных состояний.

    Примеры:
        # Одно состояние
        StateFilter(MyStates.waiting_for_name)

        # Несколько состояний
        StateFilter(MyStates.waiting_for_name, MyStates.waiting_for_age)

        # Любое активное состояние (wildcard)
        StateFilter("*")

        # Отсутствие состояния (дефолт)
        StateFilter(None)
    """

    def __init__(self, *states: State | str | None) -> None:
        if not states:
            msg = "StateFilter requires at least one state"
            raise TypeError(msg)
        self._state_names: frozenset[str | None] = frozenset(
            s.state if isinstance(s, State) else s for s in states
        )

    async def __call__(self, *args: Any, **kwargs: Any) -> bool:
        """Проверить текущее FSM-состояние."""
        raw_state: str | None = kwargs.get("raw_state")
        if "*" in self._state_names:
            return raw_state is not None
        return raw_state in self._state_names
