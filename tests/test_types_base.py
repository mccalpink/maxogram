"""Тесты для types/base.py — MaxObject."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from maxogram.types.base import MaxObject


class ChildObject(MaxObject):
    """Тестовый дочерний тип."""

    name: str
    value: int = 0


class ParentObject(MaxObject):
    """Тестовый родительский тип с вложенными."""

    title: str
    child: ChildObject
    children: list[ChildObject] = []


class TestMaxObject:
    """Тесты MaxObject."""

    def test_is_base_model(self) -> None:
        assert issubclass(MaxObject, BaseModel)

    def test_extra_allow(self) -> None:
        """Новые поля от API не вызывают ошибку."""
        obj = ChildObject.model_validate({"name": "test", "value": 1, "unknown_field": "extra"})
        assert obj.name == "test"

    def test_bot_not_set_raises(self) -> None:
        obj = ChildObject(name="test")
        with pytest.raises(RuntimeError, match="Bot is not set"):
            _ = obj.bot

    def test_set_bot(self) -> None:
        sentinel = object()
        obj = ChildObject(name="test")
        obj.set_bot(sentinel)
        assert obj.bot is sentinel

    def test_set_bot_recursive(self) -> None:
        """set_bot пробрасывается на вложенные объекты."""
        sentinel = object()
        parent = ParentObject(
            title="parent",
            child=ChildObject(name="child1"),
            children=[ChildObject(name="child2"), ChildObject(name="child3")],
        )
        parent.set_bot(sentinel)
        assert parent.bot is sentinel
        assert parent.child.bot is sentinel
        assert parent.children[0].bot is sentinel
        assert parent.children[1].bot is sentinel

    def test_model_validate_and_dump(self) -> None:
        """Round-trip: validate → dump → validate."""
        data = {"name": "test", "value": 42}
        obj = ChildObject.model_validate(data)
        dumped = obj.model_dump()
        obj2 = ChildObject.model_validate(dumped)
        assert obj2.name == obj.name
        assert obj2.value == obj.value
