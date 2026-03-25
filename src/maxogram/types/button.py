"""Типы кнопок Max API."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field

from maxogram.enums import Intent
from maxogram.types.base import MaxObject


class CallbackButton(MaxObject):
    """Кнопка с callback-данными."""

    type: Literal["callback"] = "callback"
    text: str
    payload: str
    intent: Intent = Intent.DEFAULT


class LinkButton(MaxObject):
    """Кнопка-ссылка."""

    type: Literal["link"] = "link"
    text: str
    url: str


class RequestContactButton(MaxObject):
    """Кнопка запроса контакта."""

    type: Literal["request_contact"] = "request_contact"
    text: str


class RequestGeoLocationButton(MaxObject):
    """Кнопка запроса геолокации."""

    type: Literal["request_geo_location"] = "request_geo_location"
    text: str
    quick: bool = False


class ChatButton(MaxObject):
    """Кнопка создания чата."""

    type: Literal["chat"] = "chat"
    text: str
    chat_title: str | None = None
    chat_description: str | None = None
    start_payload: str | None = None
    uuid: int | None = None


Button = Annotated[
    Union[
        CallbackButton,
        LinkButton,
        RequestContactButton,
        RequestGeoLocationButton,
        ChatButton,
    ],
    Field(discriminator="type"),
]
