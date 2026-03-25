"""Smoke-тест: пакет импортируется и версия корректна."""


def test_import() -> None:
    """Проверяем что maxogram импортируется."""
    import maxogram

    assert maxogram.__version__ == "1.1.0"
