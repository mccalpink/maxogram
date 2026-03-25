"""Тесты LazyProxy — ленивая строка, вычисляемая при обращении."""

from __future__ import annotations

from maxogram.i18n.lazy import LazyProxy


def _make_proxy(value: str = "hello") -> LazyProxy:
    """Создать proxy с простой функцией."""
    return LazyProxy(lambda: value)


class TestLazyProxyStr:
    """LazyProxy.__str__ — вычисление при приведении к строке."""

    def test_str_returns_value(self) -> None:
        proxy = _make_proxy("test")
        assert str(proxy) == "test"

    def test_str_calls_func_each_time(self) -> None:
        """Каждый вызов str() вызывает функцию заново."""
        counter = {"n": 0}

        def factory() -> str:
            counter["n"] += 1
            return f"call-{counter['n']}"

        proxy = LazyProxy(factory)
        assert str(proxy) == "call-1"
        assert str(proxy) == "call-2"


class TestLazyProxyRepr:
    """LazyProxy.__repr__ — отладочное представление."""

    def test_repr_includes_value(self) -> None:
        proxy = _make_proxy("hello")
        r = repr(proxy)
        assert "LazyProxy" in r
        assert "hello" in r


class TestLazyProxyComparison:
    """LazyProxy — сравнение с обычными строками."""

    def test_eq_string(self) -> None:
        proxy = _make_proxy("hello")
        assert proxy == "hello"

    def test_eq_proxy(self) -> None:
        proxy1 = _make_proxy("hello")
        proxy2 = _make_proxy("hello")
        assert proxy1 == proxy2

    def test_ne(self) -> None:
        proxy = _make_proxy("hello")
        assert proxy != "world"

    def test_hash_matches_string(self) -> None:
        proxy = _make_proxy("hello")
        assert hash(proxy) == hash("hello")


class TestLazyProxyStringOperations:
    """LazyProxy — строковые операции."""

    def test_add(self) -> None:
        proxy = _make_proxy("hello")
        assert proxy + " world" == "hello world"

    def test_radd(self) -> None:
        proxy = _make_proxy("world")
        assert "hello " + proxy == "hello world"

    def test_mod_format(self) -> None:
        proxy = LazyProxy(lambda: "Hello %s")
        assert proxy % "world" == "Hello world"

    def test_format_method(self) -> None:
        proxy = LazyProxy(lambda: "Hello {name}")
        result = proxy.format(name="world")
        assert result == "Hello world"

    def test_len(self) -> None:
        proxy = _make_proxy("hello")
        assert len(proxy) == 5

    def test_contains(self) -> None:
        proxy = _make_proxy("hello world")
        assert "world" in proxy

    def test_getitem(self) -> None:
        proxy = _make_proxy("hello")
        assert proxy[0] == "h"
        assert proxy[1:3] == "el"

    def test_upper(self) -> None:
        proxy = _make_proxy("hello")
        assert proxy.upper() == "HELLO"

    def test_lower(self) -> None:
        proxy = _make_proxy("HELLO")
        assert proxy.lower() == "hello"

    def test_bool_true(self) -> None:
        proxy = _make_proxy("hello")
        assert bool(proxy) is True

    def test_bool_false(self) -> None:
        proxy = _make_proxy("")
        assert bool(proxy) is False

    def test_iter(self) -> None:
        proxy = _make_proxy("abc")
        assert list(proxy) == ["a", "b", "c"]


class TestLazyProxyWithArgs:
    """LazyProxy с аргументами для функции."""

    def test_args_passed(self) -> None:
        def translate(key: str, locale: str) -> str:
            return f"{key}:{locale}"

        proxy = LazyProxy(translate, "Hello", "ru")
        assert str(proxy) == "Hello:ru"

    def test_kwargs_passed(self) -> None:
        def translate(key: str, *, locale: str = "en") -> str:
            return f"{key}:{locale}"

        proxy = LazyProxy(translate, "Hello", locale="ru")
        assert str(proxy) == "Hello:ru"
