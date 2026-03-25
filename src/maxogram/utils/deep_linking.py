"""Утилиты deep linking для Max ботов.

Deep linking позволяет передавать данные при старте бота через URL.
Формат ссылки: ``https://max.ru/{username}?start={payload}``

При переходе по ссылке Max отправляет ``bot_started`` update
с полем ``payload``, содержащим переданные данные.

Для безопасной передачи структурированных данных используйте
:func:`encode_payload` / :func:`decode_payload` (base64url).
"""

from __future__ import annotations

import base64
from urllib.parse import quote

__all__ = [
    "create_start_link",
    "decode_payload",
    "encode_payload",
]

_BASE_URL = "https://max.ru"
_MAX_PAYLOAD_LENGTH = 128


def create_start_link(
    username: str,
    payload: str | None = None,
) -> str:
    """Сгенерировать deep link URL для запуска бота.

    Args:
        username: Username бота (например, ``id025404324718_3_bot``).
        payload: Данные для передачи (опционально, макс. 128 символов).

    Returns:
        URL вида ``https://max.ru/{username}?start={payload}``.

    Raises:
        ValueError: Если payload превышает 128 символов.
    """
    url = f"{_BASE_URL}/{username}"
    if payload:
        if len(payload) > _MAX_PAYLOAD_LENGTH:
            msg = (
                f"Payload не может превышать {_MAX_PAYLOAD_LENGTH} "
                f"символов (получено {len(payload)})"
            )
            raise ValueError(msg)
        url += f"?start={quote(payload, safe='')}"
    return url


def encode_payload(data: str) -> str:
    """Закодировать данные в base64url для использования в payload.

    Args:
        data: Строка для кодирования.

    Returns:
        Base64url-кодированная строка (без padding ``=``).

    Raises:
        ValueError: Если data пуста.
    """
    if not data or not data.strip():
        msg = "Данные для кодирования не могут быть пустыми."
        raise ValueError(msg)
    encoded = base64.urlsafe_b64encode(data.encode("utf-8"))
    return encoded.rstrip(b"=").decode("ascii")


def decode_payload(encoded: str) -> str:
    """Декодировать base64url payload обратно в строку.

    Args:
        encoded: Base64url-кодированная строка.

    Returns:
        Декодированная строка.

    Raises:
        ValueError: Если строка пуста или невалидна.
    """
    if not encoded or not encoded.strip():
        msg = "Payload не может быть пустым."
        raise ValueError(msg)
    # Восстановить padding
    padded = encoded + "=" * (-len(encoded) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded)
    except Exception as exc:
        msg = f"Не удалось декодировать payload: {exc}"
        raise ValueError(msg) from exc
    return decoded.decode("utf-8")
