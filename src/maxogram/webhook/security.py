"""IP whitelist middleware для защиты webhook от поддельных запросов.

Проверяет IP-адрес отправителя webhook-запроса по whitelist.
Запросы с недоверенных IP получают 403 Forbidden.

Пример::

    from maxogram.webhook.security import IPWhitelistMiddleware

    # Вариант 1: с IP-адресами Max
    ip_mw = IPWhitelistMiddleware.for_max()

    # Вариант 2: кастомный whitelist
    ip_mw = IPWhitelistMiddleware(trusted_ips=["10.0.0.0/8", "192.168.1.1"])

    # Добавить в aiohttp-приложение
    app = web.Application(middlewares=[ip_mw.middleware()])
"""

from __future__ import annotations

import logging
from ipaddress import IPv4Network, IPv6Network, ip_address, ip_network
from typing import TYPE_CHECKING, Any

from aiohttp import web

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["IPWhitelistMiddleware"]

logger = logging.getLogger(__name__)

#: Известные IP-подсети Max для webhook-уведомлений.
MAX_WEBHOOK_IPS: list[str] = [
    "185.16.150.0/30",
]


class IPWhitelistMiddleware:
    """Aiohttp middleware для проверки IP-адреса webhook-запроса.

    Блокирует запросы с IP-адресов, не входящих в whitelist,
    возвращая 403 Forbidden.

    Args:
        trusted_ips: Список IP-адресов и/или CIDR-подсетей.
        trust_x_forwarded_for: Если True, IP берётся из заголовка
            X-Forwarded-For (первый в цепочке). Использовать только
            за доверенным reverse proxy.
    """

    def __init__(
        self,
        trusted_ips: list[str],
        *,
        trust_x_forwarded_for: bool = False,
    ) -> None:
        self._networks: list[IPv4Network | IPv6Network] = []
        for entry in trusted_ips:
            try:
                self._networks.append(ip_network(entry, strict=False))
            except ValueError:
                msg = f"Невалидный IP-адрес или CIDR: {entry!r}"
                raise ValueError(msg) from None
        self._trust_xff = trust_x_forwarded_for

    @classmethod
    def for_max(
        cls,
        *,
        extra_ips: list[str] | None = None,
        trust_x_forwarded_for: bool = False,
    ) -> IPWhitelistMiddleware:
        """Создать middleware с известными IP-адресами Max.

        Args:
            extra_ips: Дополнительные IP/CIDR (например, для dev-окружения).
            trust_x_forwarded_for: Доверять заголовку X-Forwarded-For.
        """
        all_ips = list(MAX_WEBHOOK_IPS)
        if extra_ips:
            all_ips.extend(extra_ips)
        return cls(
            trusted_ips=all_ips,
            trust_x_forwarded_for=trust_x_forwarded_for,
        )

    def _contains(self, ip_str: str) -> bool:
        """Проверить, входит ли IP-адрес в whitelist."""
        try:
            addr = ip_address(ip_str)
        except ValueError:
            return False
        return any(addr in network for network in self._networks)

    def _get_client_ip(self, request: web.Request) -> str:
        """Получить IP-адрес клиента из запроса.

        При trust_x_forwarded_for=True берёт первый (leftmost) IP
        из заголовка X-Forwarded-For. Иначе — request.remote.
        """
        if self._trust_xff:
            xff = request.headers.get("X-Forwarded-For")
            if xff:
                # Первый IP в цепочке — оригинальный клиент
                return xff.split(",")[0].strip()
        return request.remote or ""

    def middleware(
        self,
    ) -> Callable[
        [web.Request, Callable[[web.Request], Any]],
        Any,
    ]:
        """Вернуть aiohttp middleware-функцию."""
        ip_mw = self

        @web.middleware
        async def ip_whitelist_middleware(
            request: web.Request,
            handler: Callable[[web.Request], Any],
        ) -> web.StreamResponse:
            client_ip = ip_mw._get_client_ip(request)
            if not ip_mw._contains(client_ip):
                logger.warning(
                    "Webhook: запрос с недоверенного IP %s заблокирован",
                    client_ip,
                )
                return web.json_response(
                    {"ok": False, "error": "Forbidden: IP not in whitelist"},
                    status=403,
                )
            response: web.StreamResponse = await handler(request)
            return response

        return ip_whitelist_middleware
