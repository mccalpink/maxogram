"""Интернационализация — переводы через Babel/gettext."""

from maxogram.i18n.core import I18n
from maxogram.i18n.lazy import LazyProxy
from maxogram.i18n.middleware import I18nMiddleware

__all__ = [
    "I18n",
    "I18nMiddleware",
    "LazyProxy",
]
