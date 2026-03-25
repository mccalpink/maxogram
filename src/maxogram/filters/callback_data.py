"""CallbackData — типизированные callback_data с pack/unpack."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel

from maxogram.filters.base import Filter

__all__ = [
    "CallbackData",
]

# Ограничение Max API на длину callback payload
_MAX_CALLBACK_LENGTH = 1024
_SEPARATOR = ":"


class CallbackData(BaseModel):
    """Базовый класс для типизированных callback_data.

    Предоставляет pack/unpack для сериализации в строку ``prefix:val1:val2``.
    Ограничение Max API: payload до 1024 символов.

    Пример::

        class ItemAction(CallbackData, prefix="item"):
            id: int
            action: str

        cb = ItemAction(id=42, action="delete")
        cb.pack()  # "item:42:delete"

        restored = ItemAction.unpack("item:42:delete")
        # restored.id == 42, restored.action == "delete"

        # Фильтр для router
        router.callback(ItemAction.filter())
    """

    __prefix__: ClassVar[str]

    def __init_subclass__(cls, prefix: str | None = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if prefix is not None:
            if _SEPARATOR in prefix:
                msg = f"CallbackData prefix must not contain '{_SEPARATOR}'"
                raise ValueError(msg)
            cls.__prefix__ = prefix

    def pack(self) -> str:
        """Сериализовать в строку ``prefix:val1:val2:...``.

        Raises:
            ValueError: Если результат превышает 1024 символов.
        """
        parts = [self.__prefix__]
        for field_name in self.__class__.model_fields:
            value = getattr(self, field_name)
            parts.append("" if value is None else str(value))
        result = _SEPARATOR.join(parts)
        if len(result) > _MAX_CALLBACK_LENGTH:
            msg = (
                f"Packed callback_data exceeds {_MAX_CALLBACK_LENGTH} characters "
                f"({len(result)} chars). Max API limit."
            )
            raise ValueError(msg)
        return result

    @classmethod
    def unpack(cls, data: str) -> CallbackData:
        """Десериализовать из строки ``prefix:val1:val2:...``.

        Raises:
            ValueError: Если prefix не совпадает или количество полей неверное.
        """
        if not data:
            msg = "Empty callback data string"
            raise ValueError(msg)

        parts = data.split(_SEPARATOR)
        prefix = parts[0]

        if prefix != cls.__prefix__:
            msg = f"Wrong prefix: expected '{cls.__prefix__}', got '{prefix}'"
            raise ValueError(msg)

        field_names = list(cls.model_fields.keys())
        values = parts[1:]

        if len(values) != len(field_names):
            msg = f"Wrong number of fields: expected {len(field_names)}, got {len(values)}"
            raise ValueError(msg)

        # Собрать kwargs для конструктора
        kwargs: dict[str, Any] = {}
        for name, raw_value in zip(field_names, values, strict=True):
            field_info = cls.model_fields[name]
            # Пустая строка -> None для optional полей
            if raw_value == "" and not field_info.is_required():
                kwargs[name] = None
            else:
                kwargs[name] = raw_value

        return cls(**kwargs)

    @classmethod
    def filter(cls) -> _CallbackDataFilter:
        """Создать фильтр для использования в router.

        Возвращает фильтр, который парсит payload из Callback
        и возвращает ``{"callback_data": <parsed>}`` при совпадении.
        """
        return _CallbackDataFilter(callback_data_cls=cls)


class _CallbackDataFilter(Filter):
    """Внутренний фильтр для CallbackData.filter()."""

    __slots__ = ("callback_data_cls",)

    def __init__(self, callback_data_cls: type[CallbackData]) -> None:
        self.callback_data_cls = callback_data_cls

    async def __call__(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:
        """Проверить callback payload.

        Первый аргумент — Callback или MessageCallbackUpdate.
        """
        event = args[0] if args else None
        if event is None:
            return False

        # Извлечь callback из Update
        callback = event
        if hasattr(event, "update_type") and hasattr(event, "callback"):
            callback = event.callback

        payload = getattr(callback, "payload", None)
        if payload is None:
            return False

        try:
            parsed = self.callback_data_cls.unpack(payload)
        except (ValueError, Exception):
            return False

        return {"callback_data": parsed}
