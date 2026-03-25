"""Тесты sentinel-объектов и исключений."""

from maxogram.dispatcher.event.bases import (
    REJECTED,
    UNHANDLED,
    CancelHandler,
    SkipHandler,
)


class TestSentinels:
    """Тесты для UNHANDLED и REJECTED."""

    def test_unhandled_repr(self) -> None:
        assert "UNHANDLED" in repr(UNHANDLED)

    def test_rejected_repr(self) -> None:
        assert "REJECTED" in repr(REJECTED)

    def test_unhandled_is_not_rejected(self) -> None:
        assert UNHANDLED is not REJECTED

    def test_unhandled_bool_is_false(self) -> None:
        assert not UNHANDLED

    def test_rejected_bool_is_false(self) -> None:
        assert not REJECTED


class TestExceptions:
    """Тесты для SkipHandler и CancelHandler."""

    def test_skip_handler_is_exception(self) -> None:
        assert issubclass(SkipHandler, Exception)

    def test_cancel_handler_is_exception(self) -> None:
        assert issubclass(CancelHandler, Exception)

    def test_skip_handler_can_be_raised(self) -> None:
        try:
            raise SkipHandler
        except SkipHandler:
            pass

    def test_cancel_handler_can_be_raised(self) -> None:
        try:
            raise CancelHandler
        except CancelHandler:
            pass
