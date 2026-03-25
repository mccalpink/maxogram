"""Методы обновлений (long polling) — /updates."""

from __future__ import annotations

from typing import ClassVar

from maxogram.methods.base import MaxMethod
from maxogram.types.update import GetUpdatesResult


class GetUpdates(MaxMethod["GetUpdatesResult"]):
    """GET /updates — Long polling для получения обновлений."""

    __api_path__: ClassVar[str] = "/updates"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = GetUpdatesResult
    __query_params__: ClassVar[frozenset[str]] = frozenset({"limit", "timeout", "marker", "types"})

    limit: int | None = None
    timeout: int | None = None
    marker: int | None = None
    types: list[str] | None = None
