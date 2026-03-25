"""Тесты CallbackData фильтра."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from maxogram.filters.base import Filter
from maxogram.filters.callback_data import CallbackData

# -- Тестовые CallbackData классы --


class ItemAction(CallbackData, prefix="item"):
    """Действие с товаром."""

    id: int
    action: str


class SimplePrefix(CallbackData, prefix="s"):
    """Минимальный callback."""

    value: int


class WithOptional(CallbackData, prefix="opt"):
    """Callback с опциональным полем."""

    id: int
    label: str | None = None


class EmptyFields(CallbackData, prefix="empty"):
    """Callback без полей (только prefix)."""

    pass


class WithDefault(CallbackData, prefix="def"):
    """Callback с полем по умолчанию."""

    id: int
    mode: str = "view"


# -- Тесты pack/unpack --


class TestCallbackDataPack:
    """Тесты сериализации (pack)."""

    def test_simple_pack(self) -> None:
        """item:42:delete."""
        cb = ItemAction(id=42, action="delete")
        assert cb.pack() == "item:42:delete"

    def test_pack_with_string_value(self) -> None:
        """item:1:edit."""
        cb = ItemAction(id=1, action="edit")
        assert cb.pack() == "item:1:edit"

    def test_empty_fields_pack(self) -> None:
        """Только prefix -> 'empty'."""
        cb = EmptyFields()
        assert cb.pack() == "empty"

    def test_optional_none_pack(self) -> None:
        """Опциональное None -> пустая строка."""
        cb = WithOptional(id=1, label=None)
        assert cb.pack() == "opt:1:"

    def test_optional_value_pack(self) -> None:
        """Опциональное со значением."""
        cb = WithOptional(id=1, label="test")
        assert cb.pack() == "opt:1:test"

    def test_default_value_pack(self) -> None:
        """Поле с дефолтом -> дефолтное значение в pack."""
        cb = WithDefault(id=1)
        assert cb.pack() == "def:1:view"

    def test_default_overridden_pack(self) -> None:
        """Переопределённый дефолт."""
        cb = WithDefault(id=1, mode="edit")
        assert cb.pack() == "def:1:edit"


class TestCallbackDataUnpack:
    """Тесты десериализации (unpack)."""

    def test_simple_unpack(self) -> None:
        """item:42:delete -> ItemAction(id=42, action='delete')."""
        cb = ItemAction.unpack("item:42:delete")
        assert cb.id == 42
        assert cb.action == "delete"

    def test_wrong_prefix(self) -> None:
        """Неправильный prefix -> ValueError."""
        with pytest.raises(ValueError, match="prefix"):
            ItemAction.unpack("wrong:42:delete")

    def test_wrong_field_count(self) -> None:
        """Неправильное количество полей -> ValueError."""
        with pytest.raises(ValueError):
            ItemAction.unpack("item:42")

    def test_invalid_type(self) -> None:
        """Невалидный тип (str вместо int) -> ValueError."""
        with pytest.raises((ValueError, ValidationError)):
            ItemAction.unpack("item:abc:delete")

    def test_empty_fields_unpack(self) -> None:
        """Только prefix -> EmptyFields()."""
        cb = EmptyFields.unpack("empty")
        assert isinstance(cb, EmptyFields)

    def test_optional_none_unpack(self) -> None:
        """opt:1: -> label=None."""
        cb = WithOptional.unpack("opt:1:")
        assert cb.id == 1
        assert cb.label is None

    def test_optional_value_unpack(self) -> None:
        """opt:1:test -> label='test'."""
        cb = WithOptional.unpack("opt:1:test")
        assert cb.id == 1
        assert cb.label == "test"

    def test_roundtrip(self) -> None:
        """pack -> unpack -> тот же объект."""
        original = ItemAction(id=99, action="view")
        packed = original.pack()
        restored = ItemAction.unpack(packed)
        assert restored.id == original.id
        assert restored.action == original.action

    def test_roundtrip_with_optional(self) -> None:
        """Roundtrip с опциональными."""
        original = WithOptional(id=5, label="hello")
        restored = WithOptional.unpack(original.pack())
        assert restored.id == original.id
        assert restored.label == original.label

    def test_empty_string_payload(self) -> None:
        """Пустая строка -> ValueError."""
        with pytest.raises(ValueError):
            ItemAction.unpack("")


class TestCallbackDataMaxLimit:
    """Тесты ограничения Max API на 1024 символа."""

    def test_within_limit(self) -> None:
        """Нормальная длина -> ok."""
        cb = ItemAction(id=1, action="x" * 100)
        packed = cb.pack()
        assert len(packed) <= 1024

    def test_exceeds_limit(self) -> None:
        """Превышение 1024 символов -> ValueError."""
        with pytest.raises(ValueError, match="1024"):
            ItemAction(id=1, action="x" * 1020).pack()


class TestCallbackDataFilter:
    """Тесты CallbackData.filter() — фильтр для router."""

    def test_filter_is_filter_subclass(self) -> None:
        """filter() возвращает подкласс Filter."""
        f = ItemAction.filter()
        assert isinstance(f, Filter)

    @pytest.mark.asyncio
    async def test_filter_match(self) -> None:
        """Правильный payload -> dict с callback_data."""
        f = ItemAction.filter()
        # Имитируем Callback
        callback = _FakeCallback(payload="item:42:delete")
        result = await f(callback)
        assert isinstance(result, dict)
        assert result["callback_data"].id == 42
        assert result["callback_data"].action == "delete"

    @pytest.mark.asyncio
    async def test_filter_wrong_prefix(self) -> None:
        """Неправильный prefix -> False."""
        f = ItemAction.filter()
        callback = _FakeCallback(payload="wrong:42:delete")
        result = await f(callback)
        assert result is False

    @pytest.mark.asyncio
    async def test_filter_none_payload(self) -> None:
        """payload=None -> False."""
        f = ItemAction.filter()
        callback = _FakeCallback(payload=None)
        result = await f(callback)
        assert result is False

    @pytest.mark.asyncio
    async def test_filter_invalid_data(self) -> None:
        """Невалидные данные -> False."""
        f = ItemAction.filter()
        callback = _FakeCallback(payload="item:abc:delete")
        result = await f(callback)
        assert result is False

    @pytest.mark.asyncio
    async def test_filter_from_update(self) -> None:
        """Из MessageCallbackUpdate (с вложенным callback)."""
        f = ItemAction.filter()
        callback = _FakeCallback(payload="item:42:delete")
        update = _FakeCallbackUpdate(callback)
        result = await f(update)
        assert isinstance(result, dict)
        assert result["callback_data"].id == 42

    @pytest.mark.asyncio
    async def test_filter_no_args(self) -> None:
        """Без аргументов -> False."""
        f = ItemAction.filter()
        result = await f()
        assert result is False

    @pytest.mark.asyncio
    async def test_filter_no_payload_attr(self) -> None:
        """Объект без payload -> False."""
        f = ItemAction.filter()
        result = await f("not a callback")
        assert result is False


class TestCallbackDataPrefix:
    """Тесты prefix-механизма."""

    def test_prefix_stored(self) -> None:
        """prefix сохраняется в классе."""
        assert ItemAction.__prefix__ == "item"

    def test_different_prefixes(self) -> None:
        """Разные классы — разные prefix."""
        assert ItemAction.__prefix__ != SimplePrefix.__prefix__

    def test_colon_in_prefix_raises(self) -> None:
        """Двоеточие в prefix запрещено."""
        with pytest.raises(ValueError, match=":"):

            class Bad(CallbackData, prefix="a:b"):
                pass


# -- Хелперы --


class _FakeCallback:
    """Имитация Callback с payload."""

    def __init__(self, payload: str | None) -> None:
        self.payload = payload


class _FakeCallbackUpdate:
    """Имитация MessageCallbackUpdate."""

    def __init__(self, callback: _FakeCallback) -> None:
        self.update_type = "message_callback"
        self.callback = callback
