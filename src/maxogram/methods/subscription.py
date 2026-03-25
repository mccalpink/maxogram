"""Методы подписок (webhooks) — /subscriptions."""

from __future__ import annotations

from typing import ClassVar

from maxogram.methods.base import MaxMethod
from maxogram.types.misc import GetSubscriptionsResult, SimpleQueryResult


class GetSubscriptions(MaxMethod["GetSubscriptionsResult"]):
    """GET /subscriptions — Список подписок."""

    __api_path__: ClassVar[str] = "/subscriptions"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = GetSubscriptionsResult


class Subscribe(MaxMethod["SimpleQueryResult"]):
    """POST /subscriptions — Создать webhook-подписку."""

    __api_path__: ClassVar[str] = "/subscriptions"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = SimpleQueryResult

    url: str
    update_types: list[str]
    version: str | None = None


class Unsubscribe(MaxMethod["SimpleQueryResult"]):
    """DELETE /subscriptions — Удалить webhook-подписку."""

    __api_path__: ClassVar[str] = "/subscriptions"
    __http_method__: ClassVar[str] = "DELETE"
    __returning__: ClassVar[type] = SimpleQueryResult
    __query_params__: ClassVar[frozenset[str]] = frozenset({"url"})

    url: str
