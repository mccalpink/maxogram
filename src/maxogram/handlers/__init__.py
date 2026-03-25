"""Class-based handlers для maxogram.

Предоставляют альтернативу функциональным хендлерам —
организация логики в классах с типизированным доступом к event и data.
"""

from maxogram.handlers.base import BaseHandler, CallbackHandler, MessageHandler

__all__ = [
    "BaseHandler",
    "CallbackHandler",
    "MessageHandler",
]
