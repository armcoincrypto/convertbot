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

# Language display names for UI
LANG_NAMES = {
    'hy': '\u0540\u0561\u0575\u0565\u0580\u0565\u0576',  # Hayeren in Armenian
    'en': 'English',
    'ru': '\u0420\u0443\u0441\u0441\u043a\u0438\u0439',  # Russkiy in Russian
}

DEFAULT_LANG = 'hy'


def get_msg(lang: str = None):
    """Get MSG class for specified language."""
    if lang is None:
        lang = os.environ.get('BOT_LANG', DEFAULT_LANG)
    return LANGUAGES.get(lang, LANGUAGES[DEFAULT_LANG])


def resolve_lang_sync(update=None) -> str:
    """
    Synchronous language resolution (no DB check).
    Priority:
    1. BOT_LANG environment variable
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


async def resolve_lang(update=None, user_id: int = None) -> str:
    """
    Resolve language for a user/update (async, checks DB).
    Priority:
    1. User's saved preference in database (highest)
    2. BOT_LANG environment variable
    3. User's Telegram language_code
    4. Default (Armenian)
    """
    from app.db import get_user_lang

    # Get user_id from update if not provided
    if user_id is None and update:
        if hasattr(update, 'effective_user') and update.effective_user:
            user_id = update.effective_user.id

    # Check database first (highest priority)
    if user_id:
        db_lang = await get_user_lang(user_id)
        if db_lang and db_lang in LANGUAGES:
            return db_lang

    # Check environment override
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
