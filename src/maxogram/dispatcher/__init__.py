"""Dispatcher — маршрутизация событий и обработка хендлеров."""

from maxogram.dispatcher.dispatcher import Dispatcher
from maxogram.dispatcher.router import Router

__all__ = [
    "Dispatcher",
    "Router",
]
