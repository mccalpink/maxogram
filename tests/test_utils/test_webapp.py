"""Тесты валидации WebApp initData."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from maxogram.utils.webapp import (
    WebAppInitData,
    WebAppUser,
    parse_init_data,
    validate_init_data,
)

BOT_TOKEN = "1234567890:ABCDEFghijklmnopqrstuvwxyz123456789"


def _make_init_data(
    *,
    bot_token: str = BOT_TOKEN,
    user: dict[str, object] | None = None,
    chat_instance: str = "123456",
    auth_date: int | None = None,
    extra_fields: dict[str, str] | None = None,
    tamper_hash: bool = False,
) -> str:
    """Сгенерировать валидную initData строку для тестов.

    Алгоритм:
    1. secret_key = HMAC-SHA256("WebAppData", bot_token)
    2. data_check_string = поля отсортированные по ключу (без hash), через '\\n'
    3. hash = HMAC-SHA256(secret_key, data_check_string)
    """
    if auth_date is None:
        auth_date = int(time.time())

    if user is None:
        user = {"id": 123456, "first_name": "Test", "last_name": "User"}

    fields: dict[str, str] = {
        "user": json.dumps(user, ensure_ascii=False),
        "chat_instance": chat_instance,
        "auth_date": str(auth_date),
    }
    if extra_fields:
        fields.update(extra_fields)

    # data_check_string: sorted by key, joined with \n
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(fields.items())
    )

    # secret_key = HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode(), hashlib.sha256
    ).digest()

    # hash = HMAC-SHA256(secret_key, data_check_string)
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if tamper_hash:
        computed_hash = "a" * 64

    fields["hash"] = computed_hash

    return urlencode(fields)


class TestValidateInitData:
    """validate_init_data — проверка HMAC подписи."""

    def test_valid_data(self) -> None:
        """Валидная initData — True."""
        init_data = _make_init_data()
        assert validate_init_data(init_data, BOT_TOKEN) is True

    def test_invalid_hash(self) -> None:
        """Подменённый hash — False."""
        init_data = _make_init_data(tamper_hash=True)
        assert validate_init_data(init_data, BOT_TOKEN) is False

    def test_wrong_token(self) -> None:
        """Неверный токен — False."""
        init_data = _make_init_data()
        assert validate_init_data(init_data, "wrong:token") is False

    def test_missing_hash(self) -> None:
        """Отсутствует hash — False."""
        fields = {"auth_date": str(int(time.time())), "user": "{}"}
        init_data = urlencode(fields)
        assert validate_init_data(init_data, BOT_TOKEN) is False

    def test_empty_string(self) -> None:
        """Пустая строка — False."""
        assert validate_init_data("", BOT_TOKEN) is False

    def test_with_extra_fields(self) -> None:
        """Дополнительные поля учитываются в подписи."""
        init_data = _make_init_data(extra_fields={"start_param": "abc"})
        assert validate_init_data(init_data, BOT_TOKEN) is True

    def test_tampered_field(self) -> None:
        """Изменённое поле после подписи — False."""
        init_data = _make_init_data()
        # Подменяем chat_instance
        init_data = init_data.replace("chat_instance=123456", "chat_instance=hacked")
        assert validate_init_data(init_data, BOT_TOKEN) is False

    def test_with_lifetime_valid(self) -> None:
        """auth_date в пределах lifetime — True."""
        auth_date = int(time.time()) - 60  # 1 минута назад
        init_data = _make_init_data(auth_date=auth_date)
        assert validate_init_data(init_data, BOT_TOKEN, lifetime=300) is True

    def test_with_lifetime_expired(self) -> None:
        """auth_date за пределами lifetime — False."""
        auth_date = int(time.time()) - 600  # 10 минут назад
        init_data = _make_init_data(auth_date=auth_date)
        assert validate_init_data(init_data, BOT_TOKEN, lifetime=300) is False

    def test_without_lifetime_old_date_ok(self) -> None:
        """Без lifetime — любая дата валидна."""
        auth_date = int(time.time()) - 86400  # сутки назад
        init_data = _make_init_data(auth_date=auth_date)
        assert validate_init_data(init_data, BOT_TOKEN) is True


class TestParseInitData:
    """parse_init_data — парсинг и валидация."""

    def test_parse_valid(self) -> None:
        """Успешный парсинг валидных данных."""
        user_data = {"id": 123, "first_name": "Вася", "last_name": "Пупкин"}
        init_data = _make_init_data(user=user_data)
        result = parse_init_data(init_data, BOT_TOKEN)
        assert isinstance(result, WebAppInitData)
        assert result.auth_date > 0
        assert result.hash is not None

    def test_parse_user(self) -> None:
        """Парсинг поля user."""
        user_data = {
            "id": 42,
            "first_name": "Тест",
            "last_name": "Юзер",
            "username": "testuser",
        }
        init_data = _make_init_data(user=user_data)
        result = parse_init_data(init_data, BOT_TOKEN)
        assert result.user is not None
        assert result.user.id == 42
        assert result.user.first_name == "Тест"
        assert result.user.last_name == "Юзер"
        assert result.user.username == "testuser"

    def test_parse_invalid_raises(self) -> None:
        """Невалидная подпись — ValueError."""
        init_data = _make_init_data(tamper_hash=True)
        with pytest.raises(ValueError, match="invalid"):
            parse_init_data(init_data, BOT_TOKEN)

    def test_parse_chat_instance(self) -> None:
        """Парсинг chat_instance."""
        init_data = _make_init_data(chat_instance="99999")
        result = parse_init_data(init_data, BOT_TOKEN)
        assert result.chat_instance == "99999"

    def test_parse_start_param(self) -> None:
        """Парсинг start_param из extra fields."""
        init_data = _make_init_data(extra_fields={"start_param": "hello"})
        result = parse_init_data(init_data, BOT_TOKEN)
        assert result.start_param == "hello"


class TestWebAppInitData:
    """Модель WebAppInitData."""

    def test_model_fields(self) -> None:
        """Все обязательные поля присутствуют."""
        data = WebAppInitData(auth_date=123, hash="abc")
        assert data.auth_date == 123
        assert data.hash == "abc"
        assert data.user is None
        assert data.chat_instance is None
        assert data.start_param is None

    def test_model_with_user(self) -> None:
        """С пользователем."""
        user = WebAppUser(id=1, first_name="Test")
        data = WebAppInitData(auth_date=123, hash="abc", user=user)
        assert data.user is not None
        assert data.user.id == 1


class TestWebAppUser:
    """Модель WebAppUser."""

    def test_required_fields(self) -> None:
        """id и first_name обязательны."""
        user = WebAppUser(id=42, first_name="Тест")
        assert user.id == 42
        assert user.first_name == "Тест"
        assert user.last_name is None
        assert user.username is None
        assert user.language_code is None
        assert user.is_premium is None

    def test_all_fields(self) -> None:
        """Все поля."""
        user = WebAppUser(
            id=1,
            first_name="Тест",
            last_name="Юзер",
            username="test",
            language_code="ru",
            is_premium=True,
        )
        assert user.username == "test"
        assert user.language_code == "ru"
        assert user.is_premium is True
