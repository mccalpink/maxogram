"""Валидация initData от Max WebApp.

Алгоритм идентичен Telegram WebApp: HMAC-SHA256 с ключом ``WebAppData`` + токен бота.

Использование::

    from maxogram.utils.webapp import validate_init_data, parse_init_data

    # Простая проверка
    is_valid = validate_init_data(init_data_string, bot_token)

    # Проверка + парсинг
    data = parse_init_data(init_data_string, bot_token)
    print(data.user.first_name)

.. note::
   Алгоритм валидации Max WebApp **идентичен** Telegram
   (см. analysis/max_api/limitations.md, раздел 14).
   Если в будущем Max изменит алгоритм — потребуется адаптация.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import parse_qs

from pydantic import BaseModel

__all__ = [
    "WebAppInitData",
    "WebAppUser",
    "parse_init_data",
    "validate_init_data",
]


class WebAppUser(BaseModel):
    """Пользователь из WebApp initData."""

    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool | None = None


class WebAppInitData(BaseModel):
    """Разобранные данные initData от WebApp.

    Содержит все поля, передаваемые в query string initData.
    """

    auth_date: int
    hash: str
    user: WebAppUser | None = None
    chat_instance: str | None = None
    start_param: str | None = None
    chat_type: str | None = None
    query_id: str | None = None


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    lifetime: int | None = None,
) -> bool:
    """Проверить HMAC-SHA256 подпись initData.

    Алгоритм:
    1. ``secret_key = HMAC-SHA256("WebAppData", bot_token)``
    2. ``data_check_string`` — все поля (кроме hash), отсортированные по ключу,
       в формате ``key=value``, соединённые через ``\\n``
    3. ``expected_hash = HMAC-SHA256(secret_key, data_check_string)``
    4. Сравнение ``expected_hash`` с переданным ``hash``

    Args:
        init_data: Query string из WebApp.
        bot_token: Токен бота.
        lifetime: Максимальное время жизни в секундах (опционально).
            Если задан — проверяет, что ``auth_date`` не старше ``lifetime`` секунд.

    Returns:
        True если подпись валидна.
    """
    if not init_data:
        return False

    parsed = parse_qs(init_data, keep_blank_values=True)
    hash_list = parsed.pop("hash", None)
    if not hash_list:
        return False

    received_hash = hash_list[0]

    # data_check_string: key=value пары отсортированные по ключу, через \n
    # parse_qs возвращает списки значений, берём первый элемент
    data_check_string = "\n".join(f"{k}={v[0]}" for k, v in sorted(parsed.items()))

    # secret_key = HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()

    # expected_hash = HMAC-SHA256(secret_key, data_check_string)
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        return False

    # Проверка lifetime
    if lifetime is not None:
        auth_date_list = parsed.get("auth_date")
        if not auth_date_list:
            return False
        try:
            auth_date = int(auth_date_list[0])
        except (ValueError, IndexError):
            return False
        if time.time() - auth_date > lifetime:
            return False

    return True


def parse_init_data(
    init_data: str,
    bot_token: str,
    *,
    lifetime: int | None = None,
) -> WebAppInitData:
    """Проверить подпись и разобрать initData в модель.

    Args:
        init_data: Query string из WebApp.
        bot_token: Токен бота.
        lifetime: Максимальное время жизни в секундах (опционально).

    Returns:
        WebAppInitData с разобранными полями.

    Raises:
        ValueError: Если подпись невалидна или данные истекли.
    """
    if not validate_init_data(init_data, bot_token, lifetime=lifetime):
        msg = "WebApp initData is invalid: signature verification failed"
        raise ValueError(msg)

    import json

    parsed = parse_qs(init_data, keep_blank_values=True)
    fields: dict[str, object] = {}

    # auth_date
    if "auth_date" in parsed:
        fields["auth_date"] = int(parsed["auth_date"][0])

    # hash
    if "hash" in parsed:
        fields["hash"] = parsed["hash"][0]

    # user (JSON)
    if "user" in parsed:
        user_json = parsed["user"][0]
        fields["user"] = json.loads(user_json)

    # Строковые поля
    for key in ("chat_instance", "start_param", "chat_type", "query_id"):
        if key in parsed:
            fields[key] = parsed[key][0]

    return WebAppInitData(**fields)  # type: ignore[arg-type]
