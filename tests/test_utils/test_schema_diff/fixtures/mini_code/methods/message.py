from typing import ClassVar

from .base import MaxMethod


class SendMessage(MaxMethod):
    __api_path__: ClassVar[str] = "/messages"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = "SendMessageResult"
    __query_params__: ClassVar[frozenset] = frozenset({"chat_id"})
    __path_params__: ClassVar[dict] = {}
    chat_id: int | None = None
    text: str | None = None
