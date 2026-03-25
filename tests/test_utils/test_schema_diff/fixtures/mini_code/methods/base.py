from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class MaxMethod(BaseModel, Generic[T]):
    __api_path__: ClassVar[str]
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type]
    __query_params__: ClassVar[frozenset] = frozenset()
    __path_params__: ClassVar[dict] = {}
