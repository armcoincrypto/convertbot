"""
i18n module for Convertbot
Supports: Armenian (hy), English (en), Russian (ru)
Default: Armenian
"""
import os
from typing import Optional

# Import language modules
from app.i18n.hy import MSG as MSG_HY
from app.i18n.en import MSG as MSG_EN
from app.i18n.ru import MSG as MSG_RU

# Language mapping
LANGUAGES = {
    'hy': MSG_HY,
    'en': MSG_EN,
    'ru': MSG_RU,
}

DEFAULT_LANG = 'hy'


def get_msg(lang: str = None):
    """Get MSG class for specified language."""
    if lang is None:
        lang = os.environ.get('BOT_LANG', DEFAULT_LANG)
    return LANGUAGES.get(lang, LANGUAGES[DEFAULT_LANG])


def resolve_lang(update=None) -> str:
    """
    Resolve language for a user/update.
    Priority:
    1. BOT_LANG environment variable (highest)
    2. User's Telegram language_code
    3. Default (Armenian)
    """
    # Check environment override first
    env_lang = os.environ.get('BOT_LANG')
    if env_lang and env_lang in LANGUAGES:
        return env_lang

    # Check user's Telegram language
    if update and hasattr(update, 'effective_user') and update.effective_user:
        user_lang = getattr(update.effective_user, 'language_code', None)
        if user_lang:
            if user_lang.startswith('hy'):
                return 'hy'
            elif user_lang.startswith('ru'):
                return 'ru'
            elif user_lang.startswith('en'):
                return 'en'

    return DEFAULT_LANG


# Default MSG for imports that don't specify language
MSG = MSG_HY
