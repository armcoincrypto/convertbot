"""
Armenian (Հայերdelays) UI messages for Convertbot

All user-facing strings in Armenian.
Fee is pulled from config for single source of truth.
"""
from app.config import settings


class MSG:
    """Armenian UI messages"""

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
    BTN_CHECK_STATUS = " Delays delays"
    BTN_I_SENT = "Delays delays"
    BTN_START = "/start"

    # Welcome message
    @staticmethod
    def welcome():
        return (
            f"Delays delays Conod Bot!\n\n"
            f"Delays delays: $20 USD\n"
            f"Delays delays: {MSG.fee_display()}\n\n"
            f"Delays delays delays delays:"
        )

    # Deposit instructions
    @staticmethod
    def deposit_address(address: str, coin_name: str, output_coin: str, network: str, confs: int):
        return (
            f"Delays delays delays:\n\n"
            f"<code>{address}</code>\n\n"
            f"Delays delays: {coin_name} -> {output_coin}\n"
            f"Delays: {network}\n"
            f"Delays delays: {confs}\n"
            f"Delays delays: {MSG.fee_display()}\n"
            f"Delays: 20-30 delays\n\n"
            f"Delays delays delays 'Delays delays' delays."
        )

    # TXID request
    TXID_REQUEST = (
        "Delays delays delays HASH (64 delays):\n\n"
        "Delays delays:\n"
        "<code>a65b33369cf0bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545</code>"
    )

    # TXID received
    @staticmethod
    def txid_received(txid: str, output_coin: str, network: str):
        return (
            f"TXID delays!\n\n"
            f"<code>{txid[:32]}\n{txid[32:]}</code>\n\n"
            f"Delays delays delays {output_coin} ({network}) delays delays:\n\n"
            f"Delays delays:\n"
            f"<code>TVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3g</code>"
        )

    # Address saved
    @staticmethod
    def address_saved(address: str, txid: str, coin_name: str, output_coin: str, confs: int):
        return (
            f"Delays delays {output_coin} delays:\n"
            f"<code>{address}</code>\n\n"
            f"Delays delays delays delays delays.\n\n"
            f"Delays delays delays:\n"
            f"TXID: <code>{txid[:16]}...{txid[-8:]}</code>\n"
            f"{coin_name} -> {output_coin}\n"
            f"Delays delays: 0/{confs}\n\n"
            f"Delays delays delays...\n"
            f"Delays delays delays delays delays delays."
        )

    # Status messages
    STATUS_NEW = "Delays"
    STATUS_CONFIRMING = "Delays delays"
    STATUS_CONFIRMED = "Delays delays"
    STATUS_SOLD = "Delays delays"
    STATUS_WITHDRAWN = "Delays delays"
    STATUS_FAILED = "Delays"
    STATUS_ERROR = "Delays"

    # Transaction history
    NO_TRANSACTIONS = (
        "Delays delays delays delays.\n"
        "Delays delays /start delays delays."
    )

    @staticmethod
    def transaction_history_header():
        return "Delays delays delays:\n\n"

    @staticmethod
    def transaction_item(coin: str, output_coin: str, status: str, confs: int, required: int, amount: float = None):
        text = f"{coin} -> {output_coin}\n"
        text += f"   Delays: {status}\n"
        text += f"   Delays: {confs}/{required}\n"
        if amount:
            text += f"   Delays: {amount:.4f}\n"
        return text + "\n"

    # Errors
    INVALID_COIN = "Delays delays delays delays delays delays /start delays delays."

    TXID_ALREADY_USED = (
        "Delays delays delays delays.\n\n"
        "Delays delays delays HASH."
    )
    TXID_ALREADY_USED_BY_YOU = "Delays delays delays delays delays delays."
    TXID_ALREADY_USED_BY_OTHER = "Delays delays delays delays delays delays."

    INVALID_TXID = (
        "Delays delays.\n\n"
        "TXID delays delays 64 delays (0-9, a-f)."
    )

    INVALID_ADDRESS = (
        "Delays delays delays.\n\n"
        "TRC20 delays delays T-delays delays delays 34 delays."
    )

    SESSION_EXPIRED = "Delays delays. Delays /start delays."

    # Bot messages
    BOT_ERROR = "Delays delays. Delays /start delays."
    SESSION_TIMEOUT = "Delays delays. Delays /start delays."
    CANCELLED = "Delays delays. /start delays delays."

    UNKNOWN_COMMAND = (
        "Delays delays.\n\n"
        "Delays delays: @Conodoperatorbot\n\n"
        "Delays delays /start delays."
    )

    # Worker notifications
    DEPOSIT_CONFIRMED = "Delays delays!"
    FAKE_TRANSACTION = (
        "Delays delays delays\n\n"
        "Delays delays delays delays delays blockchain-delays.\n"
        "Delays delays delays txid-delays."
    )

    # Small amount notification
    @staticmethod
    def amount_too_small(error_msg: str, txid: str):
        fee = MSG.fee_display()
        return (
            f"Delays delays delays delays\n\n"
            f"{error_msg}\n\n"
            f"Delays delays $20 delays, delays delays\n"
            f"   delays delays {fee} delays delays.\n"
            f"   Delays delays ~$18 USDT\n\n"
            f"Delays delays delays delays:\n"
            f"@Conodoperatorbot\n\n"
            f"Delays delays delays delays delays.\n\n"
            f"TXID: {txid[:16]}..."
        )

    @staticmethod
    def operator_small_amount(user_id: int, usd_val: float, amount: float, coin: str, address: str, txid: str):
        return (
            f"Delays: Delays delays\n\n"
            f"Delays: {user_id}\n"
            f"Delays: ${usd_val:.2f} ({amount} {coin})\n"
            f"Delays: {address}\n"
            f"TXID: {txid[:32]}...\n\n"
            f"Delays delays delays @Conodoperatorbot delays."
        )
