"""Тесты IPWhitelistMiddleware — защита webhook от поддельных запросов."""

from __future__ import annotations

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from maxogram.webhook.security import IPWhitelistMiddleware

# -- Фикстуры --


def _make_app(
    trusted_ips: list[str],
    *,
    trust_x_forwarded_for: bool = False,
) -> web.Application:
    """Создать тестовое aiohttp-приложение с IPWhitelistMiddleware."""
    mw = IPWhitelistMiddleware(
        trusted_ips=trusted_ips,
        trust_x_forwarded_for=trust_x_forwarded_for,
    )
    app = web.Application(middlewares=[mw.middleware()])

    async def ok_handler(request: web.Request) -> web.Response:
        return web.json_response({"ok": True})

    app.router.add_post("/webhook", ok_handler)
    return app


# -- Тесты парсинга IP/CIDR --


class TestIPWhitelistInit:
    """Тесты инициализации IPWhitelistMiddleware."""

    def test_single_ip(self) -> None:
        """Одиночный IP парсится корректно."""
        mw = IPWhitelistMiddleware(trusted_ips=["10.0.0.1"])
        assert mw._contains("10.0.0.1")
        assert not mw._contains("10.0.0.2")

    def test_cidr_network(self) -> None:
        """CIDR-нотация парсится корректно."""
        mw = IPWhitelistMiddleware(trusted_ips=["192.168.1.0/24"])
        assert mw._contains("192.168.1.1")
        assert mw._contains("192.168.1.254")
        assert not mw._contains("192.168.2.1")

    def test_multiple_entries(self) -> None:
        """Несколько записей (IP + CIDR)."""
        mw = IPWhitelistMiddleware(
            trusted_ips=["10.0.0.1", "192.168.0.0/16"]
        )
        assert mw._contains("10.0.0.1")
        assert mw._contains("192.168.100.50")
        assert not mw._contains("172.16.0.1")

    def test_max_webhook_ips(self) -> None:
        """IP-адреса Max (185.16.150.0/30) — 4 адреса."""
        mw = IPWhitelistMiddleware(trusted_ips=["185.16.150.0/30"])
        assert mw._contains("185.16.150.0")
        assert mw._contains("185.16.150.1")
        assert mw._contains("185.16.150.2")
        assert mw._contains("185.16.150.3")
        assert not mw._contains("185.16.150.4")

    def test_ipv6_address(self) -> None:
        """IPv6-адрес парсится корректно."""
        mw = IPWhitelistMiddleware(trusted_ips=["::1"])
        assert mw._contains("::1")
        assert not mw._contains("::2")

    def test_ipv6_network(self) -> None:
        """IPv6-подсеть парсится корректно."""
        mw = IPWhitelistMiddleware(trusted_ips=["fd00::/8"])
        assert mw._contains("fd00::1")
        assert mw._contains("fdff::1")
        assert not mw._contains("fe80::1")

    def test_empty_trusted_ips_blocks_all(self) -> None:
        """Пустой список — блокирует все запросы."""
        mw = IPWhitelistMiddleware(trusted_ips=[])
        assert not mw._contains("10.0.0.1")
        assert not mw._contains("127.0.0.1")

    def test_invalid_ip_raises(self) -> None:
        """Невалидный IP/CIDR вызывает ValueError."""
        with pytest.raises(ValueError):
            IPWhitelistMiddleware(trusted_ips=["not-an-ip"])

    def test_localhost(self) -> None:
        """127.0.0.1 (localhost)."""
        mw = IPWhitelistMiddleware(trusted_ips=["127.0.0.0/8"])
        assert mw._contains("127.0.0.1")
        assert mw._contains("127.255.255.255")


# -- Тесты HTTP-уровня --


class TestIPWhitelistHTTP:
    """Тесты middleware на уровне HTTP-запросов."""

    @pytest.mark.asyncio
    async def test_trusted_ip_allowed(self) -> None:
        """Запрос с доверенного IP — 200 OK."""
        app = _make_app(["127.0.0.0/8"])
        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/webhook", json={"data": "test"})
            assert resp.status == 200
            body = await resp.json()
            assert body["ok"] is True

    @pytest.mark.asyncio
    async def test_untrusted_ip_blocked(self) -> None:
        """Запрос с недоверенного IP — 403 Forbidden."""
        # TestClient подключается через 127.0.0.1, поэтому whitelist без localhost
        app = _make_app(["10.0.0.0/8"])
        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/webhook", json={"data": "test"})
            assert resp.status == 403
            body = await resp.json()
            assert body["ok"] is False
            assert "ip" in body["error"].lower() or "forbidden" in body["error"].lower()

    @pytest.mark.asyncio
    async def test_non_webhook_routes_not_affected(self) -> None:
        """Middleware не блокирует routes вне webhook (если route зарегистрирован)."""
        # Middleware применяется ко всему приложению, это ожидаемое поведение
        # Тест проверяет, что 403 возвращается для любого route
        app = _make_app(["10.0.0.0/8"])

        async def health_handler(request: web.Request) -> web.Response:
            return web.json_response({"status": "ok"})

        app.router.add_get("/health", health_handler)

        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/health")
            # Middleware блокирует по IP — все routes заблокированы
            assert resp.status == 403

    @pytest.mark.asyncio
    async def test_x_forwarded_for_ignored_by_default(self) -> None:
        """X-Forwarded-For игнорируется если trust_x_forwarded_for=False."""
        app = _make_app(["10.0.0.1"])  # не localhost
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/webhook",
                json={"data": "test"},
                headers={"X-Forwarded-For": "10.0.0.1"},
            )
            # Реальный IP — 127.0.0.1, X-Forwarded-For игнорируется
            assert resp.status == 403

    @pytest.mark.asyncio
    async def test_x_forwarded_for_used_when_trusted(self) -> None:
        """X-Forwarded-For используется при trust_x_forwarded_for=True."""
        app = _make_app(
            ["10.0.0.1", "127.0.0.0/8"],
            trust_x_forwarded_for=True,
        )
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/webhook",
                json={"data": "test"},
                headers={"X-Forwarded-For": "10.0.0.1"},
            )
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_x_forwarded_for_first_ip_used(self) -> None:
        """X-Forwarded-For: берётся первый (leftmost) IP из цепочки."""
        app = _make_app(
            ["10.0.0.1", "127.0.0.0/8"],
            trust_x_forwarded_for=True,
        )
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/webhook",
                json={"data": "test"},
                headers={"X-Forwarded-For": "10.0.0.1, 192.168.1.1, 172.16.0.1"},
            )
            assert resp.status == 200

    @pytest.mark.asyncio
    async def test_x_forwarded_for_untrusted_ip_blocked(self) -> None:
        """X-Forwarded-For с недоверенным IP — 403."""
        app = _make_app(
            ["10.0.0.1", "127.0.0.0/8"],
            trust_x_forwarded_for=True,
        )
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/webhook",
                json={"data": "test"},
                headers={"X-Forwarded-For": "192.168.1.100"},
            )
            assert resp.status == 403


# -- Тест factory-метода --


class TestDefaultMaxIPs:
    """Тесты factory-метода для Max IPs."""

    def test_for_max_creates_with_known_ips(self) -> None:
        """for_max() создаёт middleware с известными IP-адресами Max."""
        mw = IPWhitelistMiddleware.for_max()
        # 185.16.150.0/30 — 4 адреса
        assert mw._contains("185.16.150.0")
        assert mw._contains("185.16.150.1")
        assert mw._contains("185.16.150.2")
        assert mw._contains("185.16.150.3")
        assert not mw._contains("185.16.150.4")

    def test_for_max_with_extra_ips(self) -> None:
        """for_max() с дополнительными IP."""
        mw = IPWhitelistMiddleware.for_max(extra_ips=["10.0.0.0/8"])
        assert mw._contains("185.16.150.1")
        assert mw._contains("10.0.0.1")
        assert not mw._contains("172.16.0.1")
