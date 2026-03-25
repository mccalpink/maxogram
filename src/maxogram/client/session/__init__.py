"""HTTP-сессии maxogram."""

from maxogram.client.session.aiohttp import AiohttpSession
from maxogram.client.session.base import BaseSession

__all__ = ["AiohttpSession", "BaseSession"]
