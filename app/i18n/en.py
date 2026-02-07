"""
English UI messages for Convertbot
"""
from app.config import fee_display


class MSG:
    """English UI messages"""

    # Button labels
    BTN_BTC_USDT = "Bitcoin -> USDT"
    BTN_LTC_USDT = "Litecoin -> USDT"
    BTN_DASH_USDT = "Dash -> USDT"
    BTN_DASH_TRX = "Dash -> TRON"
    BTN_XMR_USDT = "Monero -> USDT"
    BTN_CHECK_STATUS = "Check transaction"
    BTN_I_SENT = "I have sent"
    BTN_NEW_EXCHANGE = "New exchange /start"
    BTN_CHECK = "Check"
    BTN_START = "/start"

    # Welcome message
    @staticmethod
    def welcome():
        return (
            f"Welcome! Happy to work for you.\n"
            f"\nMinimum amount: $20 USD\n"
            f"Fee: {fee_display()}\n"
            f"Select exchange type:"
        )

    # Deposit address message
    @staticmethod
    def deposit_address(address: str, coin_name: str, output_coin: str, network: str, confs: int):
        return (
            f"Your payment address:\n\n"
            f"<code>{address}</code>\n\n"
            f"You selected: {coin_name} -> {output_coin}\n"
            f"Network: {network}\n"
            f"Confirmations: {confs}\n"
            f"Fee: {fee_display()}\n"
            f"Average time: 20-30 minutes\n\n"
            f"After sending, click the 'I have sent' button."
        )

    # TXID request
    TXID_REQUEST = (
        "Received!\n\n"
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
            f"* TXID: <code>{txid[:16]}...{txid[-8:]}</code>\n"
            f"* {coin_name} -> {output_coin}\n"
            f"* Confirmations: 0/{confs}\n\n"
            f"Please wait...\n"
            f"You will receive notifications here."
        )

    # Status labels
    STATUS_NEW = "New"
    STATUS_CONFIRMING = "Confirming"
    STATUS_CONFIRMED = "Confirmed"
    STATUS_SOLD = "Sold"
    STATUS_WITHDRAWN = "Completed"
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

    # No transactions
    NO_TRANSACTIONS = (
        "No transactions found.\n"
        "Click /start to begin a new exchange."
    )

    @staticmethod
    def transaction_history_header():
        return "Your recent transactions:\n\n"

    @staticmethod
    def transaction_item(coin: str, output_coin: str, status: str, confs: int, required: int, amount: float = None):
        emoji = MSG.STATUS_EMOJI.get(status, "?")
        text = f"* {coin} -> {output_coin}\n"
        text += f"   Status: {emoji} {status}\n"
        text += f"   Confirmations: {confs}/{required}\n"
        if amount:
            text += f"   Amount: {amount:.4f}\n"
        return text + "\n"

    # Errors
    INVALID_COIN = "Please select from the buttons above:"

    TXID_ALREADY_USED = (
        "This transaction has already been used.\n\n"
        "Please send a NEW transaction HASH:\n\n"
        "Example:\n"
        "<code>6559ce2924b306bde3ca6433b92e9bac94821f587fda74ada758fd8477cf4f16</code>"
    )

    TXID_ALREADY_USED_BY_YOU = "This transaction has already been used by you.\nPlease send a NEW transaction."
    TXID_ALREADY_USED_BY_OTHER = "This transaction has already been used by another user."

    INVALID_TXID = (
        "Invalid format.\n\n"
        "TXID must be 64 characters (0-9, a-f)."
    )

    INVALID_ADDRESS = (
        "Invalid address.\n\n"
        "TRC20 address must start with T and be 34 characters."
    )

    SESSION_EXPIRED = "Session expired. Please click /start"
    BOT_ERROR = "An error occurred. Please try /start"
    SESSION_TIMEOUT = "Session timed out. Please click /start"
    CANCELLED = "Cancelled. /start to begin again."

    UNKNOWN_COMMAND = (
        "Unknown command.\n\n"
        "If you don't know how to use Conod bot,\n"
        "you can contact our operator:\n\n"
        "@Conodoperatorbot\n\n"
        "Or click /start for a new exchange."
    )

    # Worker notifications
    DEPOSIT_CONFIRMED = "Deposit confirmed!"

    FAKE_TRANSACTION = (
        "Invalid transaction.\n\n"
        "This transaction was not found on the blockchain.\n"
        "Please check the txid."
    )

    # Small amount notification
    @staticmethod
    def amount_too_small(error_msg: str, txid: str):
        return (
            f"Amount is not sufficient.\n\n"
            f"{error_msg}\n\n"
            f"Minimum $20 is required, so that\n"
            f"   after {fee_display()} fee,\n"
            f"   you will receive ~$18 USDT\n\n"
            f"Please contact operator:\n"
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

    # Status check response
    @staticmethod
    def status_response(txid: str, coin: str, status: str, confs: int, required: int):
        emoji = MSG.STATUS_EMOJI.get(status, "?")
        status_text = {
            "NEW": "New",
            "CONFIRMING": "Confirming",
            "CONFIRMED": "Confirmed",
            "SOLD": "Sold",
            "WITHDRAWN": "Completed",
            "TRADE_FAILED": "Failed",
            "PROCESSING_ERROR": "Error"
        }.get(status, status)

        if status in ["CONFIRMED", "SOLD"]:
            progress_msg = "Will complete soon!"
        elif status == "CONFIRMING":
            progress_msg = "Please wait..."
        else:
            progress_msg = "Checking..."

        return (
            f"Transaction status\n\n"
            f"TXID: <code>{txid[:16]}...{txid[-8:]}</code>\n"
            f"Coin: {coin}\n"
            f"Status: {emoji} {status_text}\n"
            f"Confirmations: {confs}/{required}\n\n"
            f"{progress_msg}"
        )
