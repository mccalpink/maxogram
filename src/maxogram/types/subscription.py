"""Типы подписок (webhooks) Max API."""

from __future__ import annotations

from maxogram.types.base import MaxObject


class Subscription(MaxObject):
    """Подписка на webhook."""

    url: str
    time: int
    update_types: list[str] | None = None
    version: str | None = None


class SubscriptionRequestBody(MaxObject):
    """Тело запроса создания подписки."""

    url: str
    update_types: list[str]
    version: str | None = None
