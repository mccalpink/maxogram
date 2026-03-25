"""Тесты FSMStrategy и apply_strategy."""

from __future__ import annotations

from maxogram.fsm.strategy import FSMStrategy, apply_strategy


class TestApplyStrategy:
    """apply_strategy — преобразование chat_id и user_id."""

    def test_user_in_chat(self) -> None:
        """USER_IN_CHAT: chat_id и user_id без изменений."""
        result = apply_strategy(FSMStrategy.USER_IN_CHAT, chat_id=100, user_id=42)
        assert result == (100, 42)

    def test_chat(self) -> None:
        """CHAT: user_id заменяется на chat_id."""
        result = apply_strategy(FSMStrategy.CHAT, chat_id=100, user_id=42)
        assert result == (100, 100)

    def test_global_user(self) -> None:
        """GLOBAL_USER: chat_id заменяется на user_id."""
        result = apply_strategy(FSMStrategy.GLOBAL_USER, chat_id=100, user_id=42)
        assert result == (42, 42)


class TestFSMStrategy:
    """FSMStrategy — перечисление стратегий."""

    def test_has_three_values(self) -> None:
        """В Max три стратегии (без topic-стратегий)."""
        assert len(FSMStrategy) == 3

    def test_members(self) -> None:
        """Все три стратегии существуют."""
        assert FSMStrategy.USER_IN_CHAT is not None
        assert FSMStrategy.CHAT is not None
        assert FSMStrategy.GLOBAL_USER is not None
