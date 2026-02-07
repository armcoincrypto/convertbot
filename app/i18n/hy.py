"""
Armenian UI messages for Convertbot

NOTE: This file contains English placeholders.
Run on VPS to generate real Armenian:
    python3 scripts/generate_armenian_i18n.py

The script extracts Armenian from git history (commit d693785).
"""
from app.config import fee_display


class MSG:
    """Armenian UI messages (placeholders - generate on VPS)"""

    # Button labels
    BTN_BTC_USDT = "Bitcoin -> USDT"
    BTN_LTC_USDT = "Litecoin -> USDT"
    BTN_DASH_USDT = "Dash -> USDT"
    BTN_DASH_TRX = "Dash -> TRON"
    BTN_XMR_USDT = "Monero -> USDT"
    BTN_CHECK_STATUS = "Check Status"
    BTN_I_SENT = "I sent"
    BTN_NEW_EXCHANGE = "New /start"
    BTN_CHECK = "Check"
    BTN_START = "/start"

    @staticmethod
    def welcome():
        return (
            f"Welcome!\n"
            f"\nMinimum: $20 USD\n"
            f"Fee: {fee_display()}\n"
            f"Select type:"
        )

    @staticmethod
    def deposit_address(address: str, coin_name: str, output_coin: str, network: str, confs: int):
        return (
            f"Your address:\n\n"
            f"<code>{address}</code>\n\n"
            f"Selected: {coin_name} -> {output_coin}\n"
            f"Network: {network}\n"
            f"Confirmations: {confs}\n"
            f"Fee: {fee_display()}\n"
            f"Time: 20-30 min\n\n"
            f"After sending click 'I sent'."
        )

    TXID_REQUEST = (
        "Received!\n\n"
        "Send HASH (64 chars):\n\n"
        "Example:\n"
        "<code>a65b33369cf0bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545</code>"
    )

    @staticmethod
    def txid_received(txid: str, output_coin: str, network: str):
        return (
            f"TXID received!\n\n"
            f"<code>{txid[:32]}\n{txid[32:]}</code>\n\n"
            f"Send your {output_coin} ({network}) address:\n\n"
            f"Example:\n"
            f"<code>TVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3g</code>"
        )

    @staticmethod
    def address_saved(address: str, txid: str, coin_name: str, output_coin: str, confs: int):
        return (
            f"Saved {output_coin} address:\n"
            f"<code>{address}</code>\n\n"
            f"Checking transfer...\n\n"
            f"Details:\n"
            f"* TXID: <code>{txid[:16]}...{txid[-8:]}</code>\n"
            f"* {coin_name} -> {output_coin}\n"
            f"* Confs: 0/{confs}\n\n"
            f"Please wait...\n"
            f"Notifications here."
        )

    STATUS_NEW = "New"
    STATUS_CONFIRMING = "Confirming"
    STATUS_CONFIRMED = "Confirmed"
    STATUS_SOLD = "Sold"
    STATUS_WITHDRAWN = "Done"
    STATUS_FAILED = "Failed"
    STATUS_ERROR = "Error"

    STATUS_EMOJI = {
        "NEW": "new",
        "CONFIRMING": "wait",
        "CONFIRMED": "ok",
        "SOLD": "sold",
        "WITHDRAWN": "done",
        "TRADE_FAILED": "fail",
        "PROCESSING_ERROR": "err"
    }

    NO_TRANSACTIONS = (
        "No transactions.\n"
        "Click /start to begin."
    )

    @staticmethod
    def transaction_history_header():
        return "Transactions:\n\n"

    @staticmethod
    def transaction_item(coin: str, output_coin: str, status: str, confs: int, required: int, amount: float = None):
        emoji = MSG.STATUS_EMOJI.get(status, "?")
        text = f"* {coin} -> {output_coin}\n"
        text += f"   Status: {emoji} {status}\n"
        text += f"   Confs: {confs}/{required}\n"
        if amount:
            text += f"   Amount: {amount:.4f}\n"
        return text + "\n"

    INVALID_COIN = "Select from buttons:"

    TXID_ALREADY_USED = (
        "Transaction used.\n\n"
        "Send NEW HASH:\n\n"
        "Example:\n"
        "<code>6559ce2924b306bde3ca6433b92e9bac94821f587fda74ada758fd8477cf4f16</code>"
    )

    TXID_ALREADY_USED_BY_YOU = "Already used by you.\nSend NEW."
    TXID_ALREADY_USED_BY_OTHER = "Used by another user."

    INVALID_TXID = (
        "Invalid format.\n\n"
        "TXID: 64 chars (0-9, a-f)."
    )

    INVALID_ADDRESS = (
        "Invalid address.\n\n"
        "TRC20: starts T, 34 chars."
    )

    SESSION_EXPIRED = "Session expired. /start"
    BOT_ERROR = "Error. Try /start"
    SESSION_TIMEOUT = "Timeout. /start"
    CANCELLED = "Cancelled. /start"

    UNKNOWN_COMMAND = (
        "Unknown command.\n\n"
        "Contact operator:\n\n"
        "@Conodoperatorbot\n\n"
        "Or /start for new exchange."
    )

    DEPOSIT_CONFIRMED = "Deposit confirmed!"

    FAKE_TRANSACTION = (
        "Invalid transaction.\n\n"
        "Not found on blockchain.\n"
        "Check txid."
    )

    @staticmethod
    def amount_too_small(error_msg: str, txid: str):
        return (
            f"Amount insufficient.\n\n"
            f"{error_msg}\n\n"
            f"Minimum $20, after {fee_display()} fee\n"
            f"you get ~$18 USDT\n\n"
            f"Contact:\n"
            f"@Conodoperatorbot\n\n"
            f"Manual processing.\n\n"
            f"TXID: {txid[:16]}..."
        )

    @staticmethod
    def operator_small_amount(user_id: int, usd_val: float, amount: float, coin: str, address: str, txid: str):
        return (
            f"ATTENTION: Small\n\n"
            f"User: {user_id}\n"
            f"Amount: ${usd_val:.2f} ({amount} {coin})\n"
            f"Address: {address}\n"
            f"TXID: {txid[:32]}...\n\n"
            f"Contact @Conodoperatorbot."
        )

    @staticmethod
    def status_response(txid: str, coin: str, status: str, confs: int, required: int):
        emoji = MSG.STATUS_EMOJI.get(status, "?")
        status_text = {
            "NEW": "New",
            "CONFIRMING": "Confirming",
            "CONFIRMED": "Confirmed",
            "SOLD": "Sold",
            "WITHDRAWN": "Done",
            "TRADE_FAILED": "Failed",
            "PROCESSING_ERROR": "Error"
        }.get(status, status)

        if status in ["CONFIRMED", "SOLD"]:
            progress_msg = "Soon!"
        elif status == "CONFIRMING":
            progress_msg = "Wait..."
        else:
            progress_msg = "Checking..."

        return (
            f"Status\n\n"
            f"TXID: <code>{txid[:16]}...{txid[-8:]}</code>\n"
            f"Coin: {coin}\n"
            f"Status: {emoji} {status_text}\n"
            f"Confs: {confs}/{required}\n\n"
            f"{progress_msg}"
        )
