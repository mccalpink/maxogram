"""API-методы Max Bot API."""

from maxogram.methods.base import MaxMethod
from maxogram.methods.bot import EditMyInfo, GetMyInfo
from maxogram.methods.callback import AnswerOnCallback, Construct
from maxogram.methods.chat import (
    DeleteChat,
    EditChat,
    GetChat,
    GetChatByLink,
    GetChats,
    LeaveChat,
    SendAction,
)
from maxogram.methods.member import (
    AddAdmins,
    AddMembers,
    GetAdmins,
    GetMembers,
    GetMembership,
    RemoveMember,
)
from maxogram.methods.message import (
    DeleteMessage,
    EditMessage,
    GetMessageById,
    GetMessages,
    SendMessage,
)
from maxogram.methods.pin import GetPinnedMessage, PinMessage, UnpinMessage
from maxogram.methods.subscription import GetSubscriptions, Subscribe, Unsubscribe
from maxogram.methods.update import GetUpdates
from maxogram.methods.upload import GetUploadUrl

__all__ = [
    # base
    "MaxMethod",
    # bot
    "GetMyInfo",
    "EditMyInfo",
    # chat
    "GetChats",
    "GetChat",
    "GetChatByLink",
    "EditChat",
    "DeleteChat",
    "SendAction",
    "LeaveChat",
    # pin
    "GetPinnedMessage",
    "PinMessage",
    "UnpinMessage",
    # member
    "GetMembers",
    "AddMembers",
    "RemoveMember",
    "GetMembership",
    "GetAdmins",
    "AddAdmins",
    # message
    "SendMessage",
    "EditMessage",
    "DeleteMessage",
    "GetMessages",
    "GetMessageById",
    # callback
    "AnswerOnCallback",
    "Construct",
    # subscription
    "GetSubscriptions",
    "Subscribe",
    "Unsubscribe",
    # upload
    "GetUploadUrl",
    # update
    "GetUpdates",
]
