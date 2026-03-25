"""Event — инфраструктура хендлеров, фильтров и DI."""

from maxogram.dispatcher.event.bases import (
    REJECTED,
    UNHANDLED,
    CancelHandler,
    SkipHandler,
)
from maxogram.dispatcher.event.event import EventObserver
from maxogram.dispatcher.event.handler import (
    CallableObject,
    CallbackType,
    FilterObject,
    HandlerObject,
)
from maxogram.dispatcher.event.max import MaxEventObserver

__all__ = [
    "REJECTED",
    "UNHANDLED",
    "CallableObject",
    "CallbackType",
    "CancelHandler",
    "EventObserver",
    "FilterObject",
    "HandlerObject",
    "MaxEventObserver",
    "SkipHandler",
]
