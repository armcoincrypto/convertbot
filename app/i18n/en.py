"""
English UI messages for Convertbot

All user-facing strings in English.
Fee is pulled from config for single source of truth.
"""
from app.config import settings


class MSG:
    """English UI messages"""

    # Fee display (from config)
    @staticmethod
    def fee_display():
        return f"{settings.commission_percent:.0f}% + ${settings.fee_fixed_usd}"

    # Button labels
    BTN_BTC_USDT = "Bitcoin -> USDT"
    BTN_LTC_USDT = "Litecoin -> USDT"
    BTN_DASH_USDT = "Dash -> USDT"
    BTN_DASH_TRX = "Dash -> TRON"
    BTN_XMR_USDT = "Monero -> USDT"
    BTN_CHECK_STATUS = "Check Status"
    BTN_I_SENT = "I have sent"
    BTN_START = "/start"

    # Welcome message
    @staticmethod
    def welcome():
        return (
            f"Welcome to Conod Bot!\n\n"
            f"Minimum: $20 USD\n"
            f"Fee: {MSG.fee_display()}\n\n"
            f"Select exchange type:"
        )

    # Deposit instructions
    @staticmethod
    def deposit_address(address: str, coin_name: str, output_coin: str, network: str, confs: int):
        return (
            f"Your deposit address:\n\n"
            f"<code>{address}</code>\n\n"
            f"You selected: {coin_name} -> {output_coin}\n"
            f"Network: {network}\n"
            f"Confirmations: {confs}\n"
            f"Fee: {MSG.fee_display()}\n"
            f"Time: 20-30 minutes\n\n"
            f"After sending, click 'I have sent'."
        )

    # TXID request
    TXID_REQUEST = (
        "Please send the transaction HASH (64 characters):\n\n"
        "Example:\n"
        "<code>a65b33369cf0bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545</code>"
    )

    # TXID received
    @staticmethod
    def txid_received(txid: str, output_coin: str, network: str):
        return (
            f"TXID received!\n\n"
            f"<code>{txid[:32]}\n{txid[32:]}</code>\n\n"
            f"Now please send your {output_coin} ({network}) receiving address:\n\n"
            f"Example:\n"
            f"<code>TVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3g</code>"
        )

    # Address saved
    @staticmethod
    def address_saved(address: str, txid: str, coin_name: str, output_coin: str, confs: int):
        return (
            f"Saved {output_coin} address:\n"
            f"<code>{address}</code>\n\n"
            f"Starting to check your transfer.\n\n"
            f"Transaction details:\n"
            f"TXID: <code>{txid[:16]}...{txid[-8:]}</code>\n"
            f"{coin_name} -> {output_coin}\n"
            f"Confirmations: 0/{confs}\n\n"
            f"Please wait...\n"
            f"You will receive notifications here."
        )

    # Status messages
    STATUS_NEW = "NEW"
    STATUS_CONFIRMING = "CONFIRMING"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_SOLD = "SOLD"
    STATUS_WITHDRAWN = "DONE"
    STATUS_FAILED = "FAILED"
    STATUS_ERROR = "ERROR"

    # Transaction history
    NO_TRANSACTIONS = (
        "No transactions found.\n"
        "Click /start to begin."
    )

    @staticmethod
    def transaction_history_header():
        return "Your recent transactions:\n\n"

    @staticmethod
    def transaction_item(coin: str, output_coin: str, status: str, confs: int, required: int, amount: float = None):
        text = f"{coin} -> {output_coin}\n"
        text += f"   Status: {status}\n"
        text += f"   Confs: {confs}/{required}\n"
        if amount:
            text += f"   Amount: {amount:.4f}\n"
        return text + "\n"

    # Errors
    INVALID_COIN = "Please select from the buttons above or /start to restart."

    TXID_ALREADY_USED = (
        "This transaction has already been used.\n\n"
        "Please send a NEW transaction HASH."
    )
    TXID_ALREADY_USED_BY_YOU = "This transaction has already been used by you."
    TXID_ALREADY_USED_BY_OTHER = "This transaction has already been used by another user."

    INVALID_TXID = (
        "Invalid format.\n\n"
        "TXID must be 64 characters (0-9, a-f)."
    )

    INVALID_ADDRESS = (
        "Invalid address.\n\n"
        "TRC20 address must start with T and be 34 characters."
    )

    SESSION_EXPIRED = "Session expired. Please /start again."

    # Bot messages
    BOT_ERROR = "An error occurred. Please try /start again."
    SESSION_TIMEOUT = "Session timed out. Please /start again."
    CANCELLED = "Cancelled. /start to begin again."

    UNKNOWN_COMMAND = (
        "Unknown command.\n\n"
        "Contact support: @Conodoperatorbot\n\n"
        "Or click /start for new exchange."
    )

    # Worker notifications
    DEPOSIT_CONFIRMED = "Deposit confirmed!"
    FAKE_TRANSACTION = (
        "Invalid transaction\n\n"
        "This transaction was not found on the blockchain.\n"
        "Please check the txid."
    )

    # Small amount notification
    @staticmethod
    def amount_too_small(error_msg: str, txid: str):
        fee = MSG.fee_display()
        return (
            f"Amount is not sufficient\n\n"
            f"{error_msg}\n\n"
            f"Minimum $20 is required, so that\n"
            f"   after we deduct {fee} commission.\n"
            f"   You will receive ~$18 USDT\n\n"
            f"Contact operator:\n"
            f"@Conodoperatorbot\n\n"
            f"We will process the exchange manually.\n\n"
            f"TXID: {txid[:16]}..."
        )

    @staticmethod
    def operator_small_amount(user_id: int, usd_val: float, amount: float, coin: str, address: str, txid: str):
        return (
            f"ATTENTION: Small amount\n\n"
            f"User: {user_id}\n"
            f"Amount: ${usd_val:.2f} ({amount} {coin})\n"
            f"Address: {address}\n"
            f"TXID: {txid[:32]}...\n\n"
            f"User will contact @Conodoperatorbot."
        )
