from .base import MaxObject


class User(MaxObject):
    user_id: int
    name: str
    username: str | None = None
