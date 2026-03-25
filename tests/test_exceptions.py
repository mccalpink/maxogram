"""Тесты для исключений maxogram."""

from maxogram.exceptions import (
    ClientDecodeError,
    MaxAPIError,
    MaxBadRequestError,
    MaxForbiddenError,
    MaxNetworkError,
    MaxNotFoundError,
    MaxogramError,
    MaxServerError,
    MaxTooManyRequestsError,
    MaxUnauthorizedError,
)


class TestExceptionHierarchy:
    """Тесты иерархии исключений."""

    def test_maxogram_error_is_base(self) -> None:
        assert issubclass(MaxogramError, Exception)

    def test_api_error_inherits_maxogram(self) -> None:
        assert issubclass(MaxAPIError, MaxogramError)

    def test_bad_request_inherits_api_error(self) -> None:
        assert issubclass(MaxBadRequestError, MaxAPIError)

    def test_forbidden_inherits_api_error(self) -> None:
        assert issubclass(MaxForbiddenError, MaxAPIError)

    def test_not_found_inherits_api_error(self) -> None:
        assert issubclass(MaxNotFoundError, MaxAPIError)

    def test_too_many_requests_inherits_api_error(self) -> None:
        assert issubclass(MaxTooManyRequestsError, MaxAPIError)

    def test_unauthorized_inherits_api_error(self) -> None:
        assert issubclass(MaxUnauthorizedError, MaxAPIError)

    def test_server_error_inherits_api_error(self) -> None:
        assert issubclass(MaxServerError, MaxAPIError)

    def test_network_error_inherits_maxogram(self) -> None:
        assert issubclass(MaxNetworkError, MaxogramError)

    def test_client_decode_error_inherits_maxogram(self) -> None:
        assert issubclass(ClientDecodeError, MaxogramError)

    def test_client_decode_error_not_api_error(self) -> None:
        assert not issubclass(ClientDecodeError, MaxAPIError)


class TestMaxogramError:
    """Тесты базового исключения."""

    def test_message(self) -> None:
        err = MaxogramError("something went wrong")
        assert str(err) == "something went wrong"


class TestMaxAPIError:
    """Тесты API-ошибки."""

    def test_with_status_and_body(self) -> None:
        err = MaxAPIError(
            status_code=400,
            error="validation.error",
            error_message="Invalid chat_id",
        )
        assert err.status_code == 400
        assert err.error == "validation.error"
        assert err.error_message == "Invalid chat_id"
        assert "400" in str(err)
        assert "Invalid chat_id" in str(err)

    def test_without_error_field(self) -> None:
        err = MaxAPIError(
            status_code=500,
            error=None,
            error_message="Internal server error",
        )
        assert err.error is None
        assert err.status_code == 500


class TestMaxBadRequestError:
    """Тесты 400 Bad Request."""

    def test_default_status_code(self) -> None:
        err = MaxBadRequestError(error="bad.request", error_message="Missing field")
        assert err.status_code == 400


class TestMaxForbiddenError:
    """Тесты 403 Forbidden."""

    def test_default_status_code(self) -> None:
        err = MaxForbiddenError(error="forbidden", error_message="Access denied")
        assert err.status_code == 403


class TestMaxNotFoundError:
    """Тесты 404 Not Found."""

    def test_default_status_code(self) -> None:
        err = MaxNotFoundError(error="not.found", error_message="Chat not found")
        assert err.status_code == 404


class TestMaxTooManyRequestsError:
    """Тесты 429 Too Many Requests."""

    def test_default_status_code(self) -> None:
        err = MaxTooManyRequestsError(
            error="too.many.requests",
            error_message="Rate limit exceeded",
        )
        assert err.status_code == 429

    def test_retry_after_float(self) -> None:
        err = MaxTooManyRequestsError(
            error="too.many.requests",
            error_message="Rate limit exceeded",
            retry_after=1.5,
        )
        assert err.retry_after == 1.5
        assert err.status_code == 429

    def test_retry_after_none_by_default(self) -> None:
        err = MaxTooManyRequestsError(
            error="too.many.requests",
            error_message="Rate limit exceeded",
        )
        assert err.retry_after is None


class TestMaxUnauthorizedError:
    """Тесты 401 Unauthorized."""

    def test_default_status_code(self) -> None:
        err = MaxUnauthorizedError(error="unauthorized", error_message="Invalid token")
        assert err.status_code == 401

    def test_attributes(self) -> None:
        err = MaxUnauthorizedError(error="unauthorized", error_message="Invalid token")
        assert err.error == "unauthorized"
        assert err.error_message == "Invalid token"
        assert "401" in str(err)


class TestMaxServerError:
    """Тесты 5xx Server Error."""

    def test_status_code_500(self) -> None:
        err = MaxServerError(
            status_code=500, error=None, error_message="Internal server error"
        )
        assert err.status_code == 500
        assert err.error is None
        assert "500" in str(err)

    def test_status_code_502(self) -> None:
        err = MaxServerError(
            status_code=502, error="bad.gateway", error_message="Bad Gateway"
        )
        assert err.status_code == 502
        assert err.error == "bad.gateway"

    def test_status_code_503(self) -> None:
        err = MaxServerError(
            status_code=503,
            error="service.unavailable",
            error_message="Service Unavailable",
        )
        assert err.status_code == 503
        assert err.error_message == "Service Unavailable"


class TestClientDecodeError:
    """Тесты ошибки парсинга JSON."""

    def test_message(self) -> None:
        err = ClientDecodeError("Failed to decode JSON")
        assert str(err) == "Failed to decode JSON"

    def test_wraps_original(self) -> None:
        original = ValueError("Expecting value: line 1 column 1")
        err = ClientDecodeError("Failed to decode JSON", original_error=original)
        assert err.original_error is original

    def test_original_error_none_by_default(self) -> None:
        err = ClientDecodeError("Failed to decode JSON")
        assert err.original_error is None

    def test_not_instance_of_api_error(self) -> None:
        err = ClientDecodeError("Failed to decode JSON")
        assert not isinstance(err, MaxAPIError)
        assert isinstance(err, MaxogramError)


class TestMaxNetworkError:
    """Тесты сетевой ошибки."""

    def test_wraps_original(self) -> None:
        original = ConnectionError("Connection refused")
        err = MaxNetworkError("Connection failed", original_error=original)
        assert err.original_error is original
        assert "Connection failed" in str(err)
