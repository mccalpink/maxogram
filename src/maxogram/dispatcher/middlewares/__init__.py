"""Middleware pipeline — onion-style обработка событий."""

from maxogram.dispatcher.middlewares.base import BaseMiddleware
from maxogram.dispatcher.middlewares.context import EventChat, MaxContextMiddleware
from maxogram.dispatcher.middlewares.error import ErrorEvent, ErrorsMiddleware
from maxogram.dispatcher.middlewares.manager import MiddlewareManager

__all__ = [
    "BaseMiddleware",
    "ErrorEvent",
    "ErrorsMiddleware",
    "EventChat",
    "MaxContextMiddleware",
    "MiddlewareManager",
]
