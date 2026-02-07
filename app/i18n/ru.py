"""
Russian UI messages for Convertbot
"""
from app.config import fee_display


class MSG:
    """Russian UI messages"""

    # Button labels
    BTN_BTC_USDT = "Bitcoin -> USDT"
    BTN_LTC_USDT = "Litecoin -> USDT"
    BTN_DASH_USDT = "Dash -> USDT"
    BTN_DASH_TRX = "Dash -> TRON"
    BTN_XMR_USDT = "Monero -> USDT"
    BTN_CHECK_STATUS = "Проверить транзакцию"
    BTN_I_SENT = "Я отправил"
    BTN_NEW_EXCHANGE = "Новый обмен /start"
    BTN_CHECK = "Проверить"
    BTN_START = "/start"

    # Welcome message
    @staticmethod
    def welcome():
        return (
            f"Добро пожаловать! Рад работать для вас.\n"
            f"\nМинимальная сумма: $20 USD\n"
            f"Комиссия: {fee_display()}\n"
            f"Выберите тип обмена:"
        )

    # Deposit address message
    @staticmethod
    def deposit_address(address: str, coin_name: str, output_coin: str, network: str, confs: int):
        return (
            f"Ваш адрес для оплаты:\n\n"
            f"<code>{address}</code>\n\n"
            f"Вы выбрали: {coin_name} -> {output_coin}\n"
            f"Сеть: {network}\n"
            f"Подтверждений: {confs}\n"
            f"Комиссия: {fee_display()}\n"
            f"Среднее время: 20-30 минут\n\n"
            f"После отправки нажмите кнопку 'Я отправил'."
        )

    # TXID request
    TXID_REQUEST = (
        "Получено!\n\n"
        "Пожалуйста, отправьте HASH транзакции (64 символа):\n\n"
        "Пример:\n"
        "<code>a65b33369cf0bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545</code>"
    )

    # TXID received
    @staticmethod
    def txid_received(txid: str, output_coin: str, network: str):
        return (
            f"TXID получен!\n\n"
            f"<code>{txid[:32]}\n{txid[32:]}</code>\n\n"
            f"Теперь отправьте ваш {output_coin} ({network}) адрес для получения:\n\n"
            f"Пример:\n"
            f"<code>TVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3g</code>"
        )

    # Address saved
    @staticmethod
    def address_saved(address: str, txid: str, coin_name: str, output_coin: str, confs: int):
        return (
            f"Сохранён {output_coin} адрес:\n"
            f"<code>{address}</code>\n\n"
            f"Начинаем проверку вашего перевода.\n\n"
            f"Детали транзакции:\n"
            f"* TXID: <code>{txid[:16]}...{txid[-8:]}</code>\n"
            f"* {coin_name} -> {output_coin}\n"
            f"* Подтверждений: 0/{confs}\n\n"
            f"Пожалуйста, подождите...\n"
            f"Вы получите уведомления здесь."
        )

    # Status labels
    STATUS_NEW = "Новый"
    STATUS_CONFIRMING = "Подтверждается"
    STATUS_CONFIRMED = "Подтверждён"
    STATUS_SOLD = "Продан"
    STATUS_WITHDRAWN = "Завершён"
    STATUS_FAILED = "Ошибка"
    STATUS_ERROR = "Ошибка"

    STATUS_EMOJI = {
        "NEW": "🆕",
        "CONFIRMING": "⏳",
        "CONFIRMED": "✅",
        "SOLD": "💱",
        "WITHDRAWN": "🎉",
        "TRADE_FAILED": "❌",
        "PROCESSING_ERROR": "❌"
    }

    # No transactions
    NO_TRANSACTIONS = (
        "Транзакции не найдены.\n"
        "Нажмите /start для начала нового обмена."
    )

    @staticmethod
    def transaction_history_header():
        return "Ваши недавние транзакции:\n\n"

    @staticmethod
    def transaction_item(coin: str, output_coin: str, status: str, confs: int, required: int, amount: float = None):
        emoji = MSG.STATUS_EMOJI.get(status, "❓")
        text = f"• {coin} -> {output_coin}\n"
        text += f"   Статус: {emoji} {status}\n"
        text += f"   Подтверждений: {confs}/{required}\n"
        if amount:
            text += f"   Сумма: {amount:.4f}\n"
        return text + "\n"

    # Errors
    INVALID_COIN = "Пожалуйста, выберите из кнопок выше:"

    TXID_ALREADY_USED = (
        "Эта транзакция уже использована.\n\n"
        "Пожалуйста, отправьте НОВЫЙ HASH транзакции:\n\n"
        "Пример:\n"
        "<code>6559ce2924b306bde3ca6433b92e9bac94821f587fda74ada758fd8477cf4f16</code>"
    )

    TXID_ALREADY_USED_BY_YOU = "Эта транзакция уже использована вами.\nПожалуйста, отправьте НОВУЮ транзакцию."
    TXID_ALREADY_USED_BY_OTHER = "Эта транзакция уже использована другим пользователем."

    INVALID_TXID = (
        "Неверный формат.\n\n"
        "TXID должен быть 64 символа (0-9, a-f)."
    )

    INVALID_ADDRESS = (
        "Неверный адрес.\n\n"
        "TRC20 адрес должен начинаться с T и быть 34 символа."
    )

    SESSION_EXPIRED = "Сессия истекла. Нажмите /start"
    BOT_ERROR = "Произошла ошибка. Попробуйте /start"
    SESSION_TIMEOUT = "Сессия истекла. Нажмите /start"
    CANCELLED = "Отменено. /start для начала."

    UNKNOWN_COMMAND = (
        "Неизвестная команда.\n\n"
        "Если вы не знаете как пользоваться Conod ботом,\n"
        "вы можете связаться с нашим оператором:\n\n"
        "📞 @Conodoperatorbot\n\n"
        "Или нажмите /start для нового обмена."
    )

    # Worker notifications
    DEPOSIT_CONFIRMED = "Депозит подтверждён!"

    FAKE_TRANSACTION = (
        "Неверная транзакция.\n\n"
        "Эта транзакция не найдена в блокчейне.\n"
        "Пожалуйста, проверьте txid."
    )

    # Small amount notification
    @staticmethod
    def amount_too_small(error_msg: str, txid: str):
        return (
            f"Сумма недостаточна.\n\n"
            f"{error_msg}\n\n"
            f"Требуется минимум $20, чтобы\n"
            f"   после комиссии {fee_display()},\n"
            f"   вы получили ~$18 USDT\n\n"
            f"Свяжитесь с оператором:\n"
            f"@Conodoperatorbot\n\n"
            f"Мы обработаем обмен вручную.\n\n"
            f"TXID: {txid[:16]}..."
        )

    @staticmethod
    def operator_small_amount(user_id: int, usd_val: float, amount: float, coin: str, address: str, txid: str):
        return (
            f"🔔 ВНИМАНИЕ: Маленькая сумма\n\n"
            f"👤 Пользователь: {user_id}\n"
            f"💰 Сумма: ${usd_val:.2f} ({amount} {coin})\n"
            f"📍 Адрес: {address}\n"
            f"🔗 TXID: {txid[:32]}...\n\n"
            f"Пользователь свяжется с @Conodoperatorbot."
        )

    # Status check response
    @staticmethod
    def status_response(txid: str, coin: str, status: str, confs: int, required: int):
        emoji = MSG.STATUS_EMOJI.get(status, "❓")
        status_text = {
            "NEW": "Новый",
            "CONFIRMING": "Подтверждается",
            "CONFIRMED": "Подтверждён",
            "SOLD": "Продан",
            "WITHDRAWN": "Завершён",
            "TRADE_FAILED": "Ошибка",
            "PROCESSING_ERROR": "Ошибка"
        }.get(status, status)

        if status in ["CONFIRMED", "SOLD"]:
            progress_msg = "✅ Скоро завершится!"
        elif status == "CONFIRMING":
            progress_msg = "⏳ Пожалуйста, подождите..."
        else:
            progress_msg = "🔍 Проверяется..."

        return (
            f"📊 Статус транзакции\n\n"
            f"TXID: <code>{txid[:16]}...{txid[-8:]}</code>\n"
            f"Монета: {coin}\n"
            f"Статус: {emoji} {status_text}\n"
            f"Подтверждений: {confs}/{required}\n\n"
            f"{progress_msg}"
        )
