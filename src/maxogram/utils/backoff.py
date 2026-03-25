"""Exponential backoff для повторных попыток при ошибках."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

__all__ = ["BackoffConfig", "Backoff"]


@dataclass
class BackoffConfig:
    """Конфигурация exponential backoff.

    Параметры задержки между повторными попытками:
    min_delay — начальная задержка (секунды),
    max_delay — максимальная задержка (секунды),
    factor — множитель увеличения,
    jitter — добавлять случайный разброс.
    """

    min_delay: float = 1.0
    max_delay: float = 60.0
    factor: float = 2.0
    jitter: bool = True


class Backoff:
    """Exponential backoff с jitter.

    Каждый вызов wait() ожидает текущий delay и увеличивает его
    для следующего вызова. reset() сбрасывает delay к начальному.
    """

    def __init__(self, config: BackoffConfig | None = None) -> None:
        self.config = config or BackoffConfig()
        self._delay = self.config.min_delay

    @property
    def current_delay(self) -> float:
        """Текущая задержка (без jitter)."""
        return self._delay

    async def wait(self) -> None:
        """Ждать текущий delay и увеличить для следующего вызова."""
        delay = self._delay
        if self.config.jitter:
            delay *= random.uniform(0.5, 1.5)  # noqa: S311
        await asyncio.sleep(delay)
        self._delay = min(self._delay * self.config.factor, self.config.max_delay)

    def reset(self) -> None:
        """Сбросить delay после успешного запроса."""
        self._delay = self.config.min_delay
