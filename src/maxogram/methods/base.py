"""Базовый класс API-методов Max Bot API."""

from __future__ import annotations

from typing import ClassVar, Generic, TypeVar

from maxogram.types.base import MaxObject

T = TypeVar("T")


class MaxMethod(MaxObject, Generic[T]):
    """Базовый класс для всех API-методов Max.

    Каждый метод определяет:
    - __api_path__: URL path (например, "/messages", "/chats/{chatId}")
    - __http_method__: HTTP-метод (GET, POST, PUT, PATCH, DELETE)
    - __returning__: тип возвращаемого значения (Pydantic-модель)
    - __query_params__: frozenset имён полей, которые передаются как
      URL query string параметры (а не в JSON body). Поля с alias
      автоматически конвертируются в API-имена (from_ → from).
      Поля со значением None пропускаются (exclude_none).
      Списки сериализуются как comma-separated, bool — как lowercase строка.
    - __path_params__: маппинг python_field → api_name для подстановки
      в URL path (например, {"chat_id": "chatId"} → /chats/123)

    Чистый data-объект. Вся логика разбора параметров — в BaseSession.
    """

    __api_path__: ClassVar[str]
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type]
    __query_params__: ClassVar[frozenset[str]] = frozenset()
    __path_params__: ClassVar[dict[str, str]] = {}
