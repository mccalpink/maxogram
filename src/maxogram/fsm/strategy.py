"""FSMStrategy — стратегия формирования ключа FSM."""

from __future__ import annotations

from enum import Enum, auto

__all__ = [
    "FSMStrategy",
    "apply_strategy",
]


class FSMStrategy(Enum):
    """Стратегия формирования ключа FSM.

    Определяет, как user_id и chat_id используются в StorageKey.

    - ``USER_IN_CHAT`` — состояние per user per chat (по умолчанию)
    - ``CHAT`` — состояние per chat (общее для всех участников)
    - ``GLOBAL_USER`` — состояние per user глобально
    """

    USER_IN_CHAT = auto()
    CHAT = auto()
    GLOBAL_USER = auto()


def apply_strategy(
    strategy: FSMStrategy,
    chat_id: int,
    user_id: int,
) -> tuple[int, int]:
    """Применить стратегию к chat_id и user_id.

    Возвращает ``(effective_chat_id, effective_user_id)``.
    """
    if strategy == FSMStrategy.CHAT:
        return chat_id, chat_id
    if strategy == FSMStrategy.GLOBAL_USER:
        return user_id, user_id
    # USER_IN_CHAT (default)
    return chat_id, user_id
