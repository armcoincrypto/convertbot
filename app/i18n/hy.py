"""
Armenian UI messages for Convertbot

IMPORTANT: This file contains placeholder text.
On VPS, run: bash scripts/install_armenian.sh
to populate with real Armenian from git history.

Fee is pulled from config for single source of truth.
"""
from app.config import settings


class MSG:
    """Armenian UI messages"""

    @staticmethod
    def fee_display():
        return f"{settings.commission_percent:.0f}% + ${settings.fee_fixed_usd:.0f}"

    # Button labels (symbols/English are OK)
    BTN_BTC_USDT = "Bitcoin -> USDT"
    BTN_LTC_USDT = "Litecoin -> USDT"
    BTN_DASH_USDT = "Dash -> USDT"
    BTN_DASH_TRX = "Dash -> TRON"
    BTN_XMR_USDT = "Monero -> USDT"
    BTN_CHECK_STATUS = "Check Status"
    BTN_I_SENT = "I sent"
    BTN_NEW_EXCHANGE = "New exchange /start"
    BTN_CHECK = "Check"
    BTN_START = "/start"

    @staticmethod
    def welcome():
        fee = MSG.fee_display()
        return (
            f"Welcome to Conod Bot!\n"
            f"\nMinimum: $20 USD\n"
            f"Fee: {fee}\n"
            f"Select exchange type:"
        )

    @staticmethod
    def deposit_address(address: str, coin_name: str, output_coin: str, network: str, confs: int):
        fee = MSG.fee_display()
        return (
            f"Your deposit address:\n\n"
            f"<code>{address}</code>\n\n"
            f"You selected: {coin_name} -> {output_coin}\n"
            f"Network: {network}\n"
            f"Confirmations: {confs}\n"
            f"Fee: {fee}\n"
            f"Time: 20-30 minutes\n\n"
            f"After sending, click 'I sent'."
        )

    TXID_REQUEST = (
        "Received!\n\n"
        "Please send transaction HASH (64 chars):\n\n"
        "Example:\n"
        "<code>a65b33369cf0bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545</code>"
    )

    @staticmethod
    def txid_received(txid: str, output_coin: str, network: str):
        return (
            f"TXID received!\n\n"
            f"<code>{txid[:32]}\n{txid[32:]}</code>\n\n"
            f"Now send your {output_coin} ({network}) address:\n\n"
            f"Example:\n"
            f"<code>TVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3g</code>"
        )

    @staticmethod
    def address_saved(address: str, txid: str, coin_name: str, output_coin: str, confs: int):
        return (
            f"Saved {output_coin} address:\n"
            f"<code>{address}</code>\n\n"
            f"Checking your transfer...\n\n"
            f"Transaction details:\n"
            f"* TXID: <code>{txid[:16]}...{txid[-8:]}</code>\n"
            f"* {coin_name} -> {output_coin}\n"
            f"* Confirmations: 0/{confs}\n\n"
            f"Please wait...\n"
            f"You will receive notifications here."
        )

    STATUS_NEW = "New"
    STATUS_CONFIRMING = "Confirming"
    STATUS_CONFIRMED = "Confirmed"
    STATUS_SOLD = "Sold"
    STATUS_WITHDRAWN = "Done"
    STATUS_FAILED = "Failed"
    STATUS_ERROR = "Error"

    STATUS_EMOJI = {
        "NEW": "NEW",
        "CONFIRMING": "WAIT",
        "CONFIRMED": "OK",
        "SOLD": "SOLD",
        "WITHDRAWN": "DONE",
        "TRADE_FAILED": "FAIL",
        "PROCESSING_ERROR": "ERR"
    }

    NO_TRANSACTIONS = (
        "No transactions found.\n"
        "Click /start to begin."
    )

    @staticmethod
    def transaction_history_header():
        return "Your transactions:\n\n"

    @staticmethod
    def transaction_item(coin: str, output_coin: str, status: str, confs: int, required: int, amount: float = None):
        emoji = MSG.STATUS_EMOJI.get(status, "?")
        text = f"* {coin} -> {output_coin}\n"
        text += f"   Status: {emoji} {status}\n"
        text += f"   Confs: {confs}/{required}\n"
        if amount:
            text += f"   Amount: {amount:.4f}\n"
        return text + "\n"

    INVALID_COIN = "Please select from buttons above."

    TXID_ALREADY_USED = (
        "This transaction already used.\n\n"
        "Please send NEW transaction HASH:\n\n"
        "Example:\n"
        "<code>6559ce2924b306bde3ca6433b92e9bac94821f587fda74ada758fd8477cf4f16</code>"
    )

    TXID_ALREADY_USED_BY_YOU = "This transaction already used by you.\nPlease send NEW transaction."
    TXID_ALREADY_USED_BY_OTHER = "This transaction used by another user."

    INVALID_TXID = (
        "Invalid format.\n\n"
        "TXID must be 64 chars (0-9, a-f)."
    )

    INVALID_ADDRESS = (
        "Invalid address.\n\n"
        "TRC20 address must start with T and be 34 chars."
    )

    SESSION_EXPIRED = "Session expired. Click /start"
    BOT_ERROR = "Error occurred. Click /start"
    SESSION_TIMEOUT = "Session timed out. Click /start"
    CANCELLED = "Cancelled. /start"

    UNKNOWN_COMMAND = (
        "Unknown command.\n\n"
        "If you need help with Conod bot,\n"
        "contact our operator:\n\n"
        "@Conodoperatorbot\n\n"
        "Or click /start for new exchange."
    )

    DEPOSIT_CONFIRMED = "Deposit confirmed!"

    FAKE_TRANSACTION = (
        "Invalid transaction.\n\n"
        "This transaction not found on blockchain.\n"
        "Please check the txid."
    )

    @staticmethod
    def amount_too_small(error_msg: str, txid: str):
        fee = MSG.fee_display()
        return (
            f"Amount not sufficient.\n\n"
            f"{error_msg}\n\n"
            f"Minimum $20 required, so that\n"
            f"   after {fee} fee\n"
            f"   you receive ~$18 USDT\n\n"
            f"Contact operator:\n"
            f"@Conodoperatorbot\n\n"
            f"We will process manually.\n\n"
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
