"""Webhook модуль — приём обновлений через HTTP server."""

from maxogram.webhook.handler import WebhookHandler
from maxogram.webhook.manager import WebhookManager

__all__ = ["WebhookHandler", "WebhookManager"]
