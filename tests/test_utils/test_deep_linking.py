"""Тесты утилит deep linking."""

from __future__ import annotations

import pytest

from maxogram.utils.deep_linking import (
    create_start_link,
    decode_payload,
    encode_payload,
)


class TestCreateStartLink:
    """Генерация deep link URL."""

    def test_basic_link(self) -> None:
        """Ссылка с username и payload."""
        link = create_start_link(username="mybot", payload="hello")
        assert link == "https://max.ru/mybot?start=hello"

    def test_link_without_payload(self) -> None:
        """Ссылка без payload."""
        link = create_start_link(username="mybot")
        assert link == "https://max.ru/mybot"

    def test_link_with_real_username(self) -> None:
        """Ссылка с реальным username бота Max."""
        link = create_start_link(username="id025404324718_3_bot")
        assert link == "https://max.ru/id025404324718_3_bot"

    def test_link_with_encoded_payload(self) -> None:
        """Ссылка с base64url-encoded payload."""
        encoded = encode_payload("user_42_promo")
        link = create_start_link(username="mybot", payload=encoded)
        assert "mybot" in link
        assert f"start={encoded}" in link

    def test_link_payload_with_special_chars(self) -> None:
        """Payload с символами, требующими URL-кодирования."""
        link = create_start_link(username="mybot", payload="a=b&c=d")
        # Спецсимволы должны быть закодированы
        assert "start=" in link
        assert "a%3Db%26c%3Dd" in link

    def test_empty_payload_treated_as_no_payload(self) -> None:
        """Пустая строка payload — как если бы не указан."""
        link = create_start_link(username="mybot", payload="")
        assert link == "https://max.ru/mybot"

    def test_payload_max_length(self) -> None:
        """Payload ровно 128 символов — допустимо."""
        payload = "a" * 128
        link = create_start_link(username="mybot", payload=payload)
        assert f"start={payload}" in link

    def test_payload_exceeds_max_length_raises(self) -> None:
        """Payload больше 128 символов — ValueError."""
        payload = "a" * 129
        with pytest.raises(ValueError, match="128"):
            create_start_link(username="mybot", payload=payload)


class TestEncodePayload:
    """Кодирование payload в base64url."""

    def test_encode_simple(self) -> None:
        """Простая строка."""
        result = encode_payload("hello")
        assert isinstance(result, str)
        # base64url не содержит +, /, =
        assert "+" not in result
        assert "/" not in result

    def test_encode_cyrillic(self) -> None:
        """Кириллица."""
        result = encode_payload("привет")
        assert isinstance(result, str)
        decoded = decode_payload(result)
        assert decoded == "привет"

    def test_encode_empty_raises(self) -> None:
        """Пустая строка — ошибка."""
        with pytest.raises(ValueError, match="пуст"):
            encode_payload("")

    def test_encode_special_chars(self) -> None:
        """Спецсимволы."""
        data = "user:42|action=promo&ref=123"
        encoded = encode_payload(data)
        assert decode_payload(encoded) == data


class TestDecodePayload:
    """Декодирование payload из base64url."""

    def test_decode_roundtrip(self) -> None:
        """Encode → decode — исходные данные."""
        original = "test_data_12345"
        assert decode_payload(encode_payload(original)) == original

    def test_decode_invalid_base64_raises(self) -> None:
        """Невалидный base64 — ошибка."""
        with pytest.raises(ValueError, match="декодировать"):
            decode_payload("!!!not-base64!!!")

    def test_decode_empty_raises(self) -> None:
        """Пустая строка — ошибка."""
        with pytest.raises(ValueError, match="пуст"):
            decode_payload("")

    def test_decode_none_like(self) -> None:
        """Whitespace — ошибка."""
        with pytest.raises(ValueError, match="пуст"):
            decode_payload("   ")

    def test_decode_complex_data(self) -> None:
        """Сложные данные с разными символами."""
        original = '{"user_id": 42, "ref": "promo-2025"}'
        encoded = encode_payload(original)
        assert decode_payload(encoded) == original
