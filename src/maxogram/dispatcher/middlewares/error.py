"""ErrorsMiddleware — перехват исключений и перенаправление к error handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from maxogram.dispatcher.event.bases import UNHANDLED, CancelHandler, SkipHandler
from maxogram.dispatcher.middlewares.base import BaseMiddleware

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

__all__ = ["ErrorEvent", "ErrorsMiddleware"]


class ErrorEvent:
    """Событие ошибки — оборачивает исключение и оригинальный update.

    Атрибуты:
        update: оригинальное событие, при обработке которого произошла ошибка.
        exception: перехваченное исключение.
    """

    __slots__ = ("exception", "update")

    def __init__(self, update: Any, exception: BaseException) -> None:
        self.update = update
        self.exception = exception

    def __repr__(self) -> str:
        return (
            f"ErrorEvent(update={self.update!r}, "
            f"exception={self.exception!r})"
        )


class ErrorsMiddleware(BaseMiddleware):
    """Перехват ошибок в хендлерах и перенаправление к error observers.

    Поведение:
    - SkipHandler и CancelHandler пробрасываются без обработки (flow-control).
    - BaseException (KeyboardInterrupt и т.д.) пробрасываются без обработки.
    - Остальные Exception оборачиваются в ErrorEvent и передаются
      через ``router.propagate_event("error", ...)``.
    - Если error handler не найден (UNHANDLED) — исключение пробрасывается.
    """

    def __init__(self, router: Any) -> None:
        self.router = router

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        """Вызвать handler, перехватить исключения и передать error observers."""
        try:
            return await handler(event, data)
        except (SkipHandler, CancelHandler):
            raise
        except Exception as e:
            response = await self.router.propagate_event(
                update_type="error",
                event=ErrorEvent(update=event, exception=e),
                **data,
            )
            if response is not UNHANDLED:
                return response
            raise
