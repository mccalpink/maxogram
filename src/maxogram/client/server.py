"""Конфигурация Max Bot API сервера."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaxAPIServer:
    """Конфигурация Max Bot API сервера.

    Отличие от aiogram TelegramAPIServer:
    - Нет file_url (Max не имеет отдельного file API)
    - Нет is_local (Max не поддерживает Local Bot API)
    """

    base_url: str = "https://platform-api.max.ru"

    def api_url(self, path: str) -> str:
        """Полный URL для API endpoint."""
        return f"{self.base_url}{path}"
