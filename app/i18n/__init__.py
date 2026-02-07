"""
i18n module for Convertbot
Supports Armenian (hy) and English (en) languages
"""
from app.i18n.hy import MSG as MSG_HY
from app.i18n.en import MSG as MSG_EN

# Default language - Armenian
MSG = MSG_HY

def get_messages(lang: str = "hy"):
    """Get messages for specified language"""
    if lang == "en":
        return MSG_EN
    return MSG_HY
