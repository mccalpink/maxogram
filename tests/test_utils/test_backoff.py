"""Тесты Backoff — exponential backoff с jitter."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from maxogram.utils.backoff import Backoff, BackoffConfig


class TestBackoffConfig:
    """Тесты конфигурации BackoffConfig."""

    def test_default_values(self) -> None:
        cfg = BackoffConfig()
        assert cfg.min_delay == 1.0
        assert cfg.max_delay == 60.0
        assert cfg.factor == 2.0
        assert cfg.jitter is True

    def test_custom_values(self) -> None:
        cfg = BackoffConfig(min_delay=0.5, max_delay=30.0, factor=3.0, jitter=False)
        assert cfg.min_delay == 0.5
        assert cfg.max_delay == 30.0
        assert cfg.factor == 3.0
        assert cfg.jitter is False


class TestBackoff:
    """Тесты Backoff — задержки, рост, лимит, сброс."""

    def test_default_config(self) -> None:
        b = Backoff()
        assert b.config == BackoffConfig()
        assert b.current_delay == 1.0

    def test_custom_config(self) -> None:
        cfg = BackoffConfig(min_delay=2.0)
        b = Backoff(cfg)
        assert b.current_delay == 2.0

    @pytest.mark.asyncio
    async def test_delay_increases_exponentially(self) -> None:
        cfg = BackoffConfig(min_delay=1.0, factor=2.0, jitter=False)
        b = Backoff(cfg)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await b.wait()
            mock_sleep.assert_awaited_once_with(1.0)
            assert b.current_delay == 2.0

            mock_sleep.reset_mock()
            await b.wait()
            mock_sleep.assert_awaited_once_with(2.0)
            assert b.current_delay == 4.0

            mock_sleep.reset_mock()
            await b.wait()
            mock_sleep.assert_awaited_once_with(4.0)
            assert b.current_delay == 8.0

    @pytest.mark.asyncio
    async def test_delay_capped_at_max(self) -> None:
        cfg = BackoffConfig(min_delay=10.0, max_delay=20.0, factor=3.0, jitter=False)
        b = Backoff(cfg)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await b.wait()  # delay=10, next=20 (capped at 20)
            assert b.current_delay == 20.0

            await b.wait()  # delay=20, next=20 (already at max)
            assert b.current_delay == 20.0

    @pytest.mark.asyncio
    async def test_reset_restores_min_delay(self) -> None:
        cfg = BackoffConfig(min_delay=1.0, factor=2.0, jitter=False)
        b = Backoff(cfg)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await b.wait()
            await b.wait()
            assert b.current_delay == 4.0

            b.reset()
            assert b.current_delay == 1.0

    @pytest.mark.asyncio
    async def test_jitter_varies_delay(self) -> None:
        cfg = BackoffConfig(min_delay=10.0, factor=1.0, jitter=True)
        b = Backoff(cfg)

        delays: list[float] = []

        async def capture_sleep(d: float) -> None:
            delays.append(d)

        with patch("asyncio.sleep", side_effect=capture_sleep):
            for _ in range(20):
                b.reset()
                await b.wait()

        # С jitter задержки должны варьироваться (не все одинаковые)
        unique_delays = set(delays)
        assert len(unique_delays) > 1, "Jitter должен давать разные значения задержки"

        # Все задержки в диапазоне [min*0.5, min*1.5]
        for d in delays:
            assert 5.0 <= d <= 15.0, f"Delay {d} вне диапазона jitter"

    @pytest.mark.asyncio
    async def test_no_jitter_exact_delay(self) -> None:
        cfg = BackoffConfig(min_delay=5.0, factor=1.0, jitter=False)
        b = Backoff(cfg)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await b.wait()
            mock_sleep.assert_awaited_once_with(5.0)
