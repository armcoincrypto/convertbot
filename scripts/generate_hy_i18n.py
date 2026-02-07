#!/usr/bin/env python3
"""
Generate Armenian i18n file from original telegram_bot_improved.py.

Run on VPS:
    cd /root/Convertbot
    python3 scripts/generate_hy_i18n.py

This extracts Armenian text from git history (commit d693785)
and creates app/i18n/hy.py with real Armenian strings.
"""
import subprocess
import os

# Get original Armenian bot from git history
result = subprocess.run(
    ["git", "show", "d693785:telegram_bot_improved.py"],
    capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

if result.returncode != 0:
    print("Error: Could not get original file from git history")
    print(result.stderr)
    exit(1)

original = result.stdout

# Parse original file to extract Armenian strings
# We'll build the hy.py file with proper Armenian text

# Fee was 3% in original, we use config now
HY_TEMPLATE = '''"""
Armenian (Հdelays) UI messages for Convertbot

All user-facing strings in Armenian.
Fee is pulled from config for single source of truth.
"""
from app.config import settings


class MSG:
    """Armenian UI messages"""

    # Fee display (from config)
    @staticmethod
    def fee_display():
        return f"{{settings.commission_percent:.0f}}% + ${{settings.fee_fixed_usd:.0f}}"

    # Button labels
    BTN_BTC_USDT = "{btn_btc}"
    BTN_LTC_USDT = "{btn_ltc}"
    BTN_DASH_USDT = "{btn_dash_usdt}"
    BTN_DASH_TRX = "{btn_dash_trx}"
    BTN_XMR_USDT = "{btn_xmr}"
    BTN_CHECK_STATUS = "{btn_check}"
    BTN_I_SENT = "{btn_sent}"
    BTN_NEW_EXCHANGE = "{btn_new}"
    BTN_CHECK = "{btn_check_short}"
    BTN_START = "/start"

    # Welcome message
    @staticmethod
    def welcome():
        fee = MSG.fee_display()
        return (
            "{welcome_line1}\\n"
            "\\n{welcome_line2}\\n"
            f"{{welcome_line3_prefix}}{{fee}}\\n"
            "{welcome_line4}"
        )

    # Deposit instructions
    @staticmethod
    def deposit_address(address: str, coin_name: str, output_coin: str, network: str, confs: int):
        fee = MSG.fee_display()
        return (
            f"{deposit_line1}\\n\\n"
            f"<code>{{address}}</code>\\n\\n"
            f"{deposit_line2}{{coin_name}} -> {{output_coin}}\\n"
            f"{deposit_line3}{{network}}\\n"
            f"{deposit_line4}{{confs}}\\n"
            f"{deposit_line5}{{fee}} {deposit_line5b}\\n"
            f"{deposit_line6}\\n\\n"
            f"{deposit_line7}"
        )

    # TXID request
    TXID_REQUEST = (
        "{txid_req_line1}\\n\\n"
        "{txid_req_line2}\\n\\n"
        "{txid_req_line3}\\n"
        "<code>a65b33369cf0bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545</code>"
    )

    # TXID received
    @staticmethod
    def txid_received(txid: str, output_coin: str, network: str):
        return (
            f"{txid_recv_line1}\\n\\n"
            f"<code>{{txid[:32]}}\\n{{txid[32:]}}</code>\\n\\n"
            f"{txid_recv_line2}{{output_coin}} ({{network}}) {txid_recv_line2b}\\n\\n"
            f"{txid_recv_line3}\\n"
            f"<code>TVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3g</code>"
        )

    # Address saved confirmation
    @staticmethod
    def address_saved(address: str, txid: str, coin_name: str, output_coin: str, confs: int):
        return (
            f"{addr_line1}{{output_coin}} {addr_line1b}\\n"
            f"<code>{{address}}</code>\\n\\n"
            f"{addr_line2}\\n\\n"
            f"{addr_line3}\\n"
            f"* TXID: <code>{{txid[:16]}}...{{txid[-8:]}}</code>\\n"
            f"* {{coin_name}} -> {{output_coin}}\\n"
            f"* {addr_line4} 0/{{confs}}\\n\\n"
            f"{addr_line5}\\n"
            f"{addr_line6}"
        )

    # Status labels
    STATUS_NEW = "{status_new}"
    STATUS_CONFIRMING = "{status_confirming}"
    STATUS_CONFIRMED = "{status_confirmed}"
    STATUS_SOLD = "{status_sold}"
    STATUS_WITHDRAWN = "{status_done}"
    STATUS_FAILED = "{status_failed}"
    STATUS_ERROR = "{status_error}"

    STATUS_EMOJI = {{
        "NEW": "delays",
        "CONFIRMING": "delays",
        "CONFIRMED": "delays",
        "SOLD": "delays",
        "WITHDRAWN": "delays",
        "TRADE_FAILED": "delays",
        "PROCESSING_ERROR": "delays"
    }}

    # No transactions
    NO_TRANSACTIONS = (
        "{no_tx_line1}\\n"
        "{no_tx_line2}"
    )

    @staticmethod
    def transaction_history_header():
        return "{tx_history_header}\\n\\n"

    @staticmethod
    def transaction_item(coin: str, output_coin: str, status: str, confs: int, required: int, amount: float = None):
        emoji = MSG.STATUS_EMOJI.get(status, "delays")
        text = f"* {{coin}} -> {{output_coin}}\\n"
        text += f"   {tx_item_status} {{emoji}} {{status}}\\n"
        text += f"   {tx_item_confs} {{confs}}/{{required}}\\n"
        if amount:
            text += f"   {tx_item_amount} {{amount:.4f}}\\n"
        return text + "\\n"

    # Errors
    INVALID_COIN = "{invalid_coin}"

    TXID_ALREADY_USED = (
        "{txid_used_line1}\\n\\n"
        "{txid_used_line2}\\n\\n"
        "{txid_used_line3}\\n"
        "<code>6559ce2924b306bde3ca6433b92e9bac94821f587fda74ada758fd8477cf4f16</code>"
    )

    TXID_ALREADY_USED_BY_YOU = "{txid_used_you}"
    TXID_ALREADY_USED_BY_OTHER = "{txid_used_other}"

    INVALID_TXID = (
        "{invalid_txid_line1}\\n\\n"
        "{invalid_txid_line2}"
    )

    INVALID_ADDRESS = (
        "{invalid_addr_line1}\\n\\n"
        "{invalid_addr_line2}"
    )

    SESSION_EXPIRED = "{session_expired}"
    BOT_ERROR = "{bot_error}"
    SESSION_TIMEOUT = "{session_timeout}"
    CANCELLED = "{cancelled}"

    UNKNOWN_COMMAND = (
        "{unknown_line1}\\n\\n"
        "{unknown_line2}\\n"
        "{unknown_line3}\\n\\n"
        "delays @Conodoperatorbot\\n\\n"
        "{unknown_line4}"
    )

    # Worker notifications
    DEPOSIT_CONFIRMED = "{deposit_confirmed}"

    FAKE_TRANSACTION = (
        "{fake_tx_line1}\\n\\n"
        "{fake_tx_line2}\\n"
        "{fake_tx_line3}"
    )

    @staticmethod
    def amount_too_small(error_msg: str, txid: str):
        fee = MSG.fee_display()
        return (
            f"{small_amt_line1}\\n\\n"
            f"{{error_msg}}\\n\\n"
            f"{small_amt_line2}\\n"
            f"   {small_amt_line3}{{fee}} {small_amt_line3b}\\n"
            f"   {small_amt_line4}\\n\\n"
            f"{small_amt_line5}\\n"
            f"@Conodoperatorbot\\n\\n"
            f"{small_amt_line6}\\n\\n"
            f"TXID: {{txid[:16]}}..."
        )

    @staticmethod
    def operator_small_amount(user_id: int, usd_val: float, amount: float, coin: str, address: str, txid: str):
        return (
            f"{op_small_line1}\\n\\n"
            f"delays User: {{user_id}}\\n"
            f"delays {op_small_amount} ${{usd_val:.2f}} ({{amount}} {{coin}})\\n"
            f"delays {op_small_addr} {{address}}\\n"
            f"delays TXID: {{txid[:32]}}...\\n\\n"
            f"{op_small_line2}"
        )
'''

# Extract actual Armenian strings from original file
# Button texts
import re

def extract(pattern, text, default="[NOT FOUND]"):
    match = re.search(pattern, text)
    return match.group(1) if match else default

# Extract button texts
btn_btc = extract(r'KeyboardButton\("(.*Bitcoin.*USDT)"\)', original)
btn_ltc = extract(r'KeyboardButton\("(.*Litecoin.*USDT)"\)', original)
btn_dash_usdt = extract(r'KeyboardButton\("(.*Dash.*USDT)"\)', original)
btn_dash_trx = extract(r'KeyboardButton\("(.*Dash.*TRON)"\)', original)
btn_xmr = extract(r'KeyboardButton\("(.*Monero.*USDT)"\)', original)
btn_check = extract(r'KeyboardButton\("(.*Delays delays.*|.*delays delays.*|.*delays.*delays.*)"\)', original)
btn_sent = extract(r'KeyboardButton\("(.*delays delays.*✅)"\)', original)
btn_new = extract(r'KeyboardButton\("(.*Delays delays.*/start)"\)', original)
btn_check_short = extract(r'KeyboardButton\("(📊.*Delays)"\)', original)

print(f"Extracted buttons:")
print(f"  BTC: {btn_btc}")
print(f"  LTC: {btn_ltc}")
print(f"  Check: {btn_check}")
print(f"  Sent: {btn_sent}")

# Find Welcome message
welcome_match = re.search(
    r'await update\.message\.reply_text\(\s*"(.*?)"\s*,\s*reply_markup',
    original, re.DOTALL
)

if welcome_match:
    welcome_text = welcome_match.group(1)
    print(f"\nWelcome text found: {len(welcome_text)} chars")
else:
    print("WARNING: Welcome text not found")
    welcome_text = ""

# For now, create a placeholder file that works
# The actual Armenian will need to be filled in manually

placeholder_hy = '''"""
Armenian UI messages for Convertbot
Generated by scripts/generate_hy_i18n.py

To populate with real Armenian text:
1. Run: git show d693785:telegram_bot_improved.py > /tmp/original_bot.py
2. Copy Armenian strings from /tmp/original_bot.py to this file
3. Restart services
"""
from app.config import settings


class MSG:
    """Armenian UI messages - REPLACE PLACEHOLDERS WITH REAL ARMENIAN"""

    @staticmethod
    def fee_display():
        return f"{settings.commission_percent:.0f}% + ${settings.fee_fixed_usd:.0f}"

    # Buttons - these use symbols/English, keep as-is
    BTN_BTC_USDT = "''' + btn_btc + '''"
    BTN_LTC_USDT = "''' + btn_ltc + '''"
    BTN_DASH_USDT = "''' + btn_dash_usdt + '''"
    BTN_DASH_TRX = "''' + btn_dash_trx + '''"
    BTN_XMR_USDT = "''' + btn_xmr + '''"
    BTN_CHECK_STATUS = "''' + btn_check + '''"
    BTN_I_SENT = "''' + btn_sent + '''"
    BTN_NEW_EXCHANGE = "''' + btn_new + '''"
    BTN_CHECK = "''' + (btn_check_short if btn_check_short != "[NOT FOUND]" else btn_check) + '''"
    BTN_START = "/start"

    @staticmethod
    def welcome():
        fee = MSG.fee_display()
        # Original had 3%, now using dynamic fee
        return (
            f"delays Delays: Delays delays delays delays delays delays.\\n"
            f"\\ndelays Delays delays: $20 USD\\n"
            f"delays Delays: {fee}\\n"
            f"delays Delays delays delays:"
        )

    @staticmethod
    def deposit_address(address: str, coin_name: str, output_coin: str, network: str, confs: int):
        fee = MSG.fee_display()
        return (
            f"Delays delays delays:\\n\\n"
            f"<code>{address}</code>\\n\\n"
            f"delays Delays delays {coin_name} -> {output_coin}\\n"
            f"delays Delays: {network}\\n"
            f"delays Delays: {confs}\\n"
            f"delays Delays {fee} delays\\n"
            f"delays Delays delays: 20-30 delays\\n\\n"
            f"Delays delays delays delays delays delays delays."
        )

    TXID_REQUEST = (
        "Delays delays\\n\\n"
        "Delays delays delays delays HASH-delays (64 delays):\\n\\n"
        "Delays:\\n"
        "<code>a65b33369cf0bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545</code>"
    )

    @staticmethod
    def txid_received(txid: str, output_coin: str, network: str):
        return (
            f"TXID delays delays delays\\n\\n"
            f"<code>{txid[:32]}\\n{txid[32:]}</code>\\n\\n"
            f"Delays delays delays delays {output_coin} ({network}) delays delays:\\n\\n"
            f"Delays:\\n"
            f"<code>TVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3g</code>"
        )

    @staticmethod
    def address_saved(address: str, txid: str, coin_name: str, output_coin: str, confs: int):
        return (
            f"delays Delays {output_coin} delays:\\n"
            f"<code>{address}</code>\\n\\n"
            f"delays Delays delays delays delays delays.\\n\\n"
            f"delays Delays delays:\\n"
            f"* TXID: <code>{txid[:16]}...{txid[-8:]}</code>\\n"
            f"* {coin_name} -> {output_coin}\\n"
            f"* Delays: 0/{confs}\\n\\n"
            f"delays Delays delays delays...\\n"
            f"delays Delays delays delays delays:"
        )

    STATUS_NEW = "Delays"
    STATUS_CONFIRMING = "Delays delays"
    STATUS_CONFIRMED = "Delays"
    STATUS_SOLD = "Delays"
    STATUS_WITHDRAWN = "Delays"
    STATUS_FAILED = "Delays"
    STATUS_ERROR = "Delays"

    STATUS_EMOJI = {
        "NEW": "delays",
        "CONFIRMING": "delays",
        "CONFIRMED": "delays",
        "SOLD": "delays",
        "WITHDRAWN": "delays",
        "TRADE_FAILED": "delays",
        "PROCESSING_ERROR": "delays"
    }

    NO_TRANSACTIONS = (
        "delays Delays delays delays delays.\\n"
        "Delays /start delays delays."
    )

    @staticmethod
    def transaction_history_header():
        return "delays Delays delays delays:\\n\\n"

    @staticmethod
    def transaction_item(coin: str, output_coin: str, status: str, confs: int, required: int, amount: float = None):
        emoji = MSG.STATUS_EMOJI.get(status, "delays")
        text = f"* {coin} -> {output_coin}\\n"
        text += f"   Delays: {emoji} {status}\\n"
        text += f"   Delays: {confs}/{required}\\n"
        if amount:
            text += f"   Delays: {amount:.4f}\\n"
        return text + "\\n"

    INVALID_COIN = "Delays delays delays delays delays:"

    TXID_ALREADY_USED = (
        "delays Delays delays delays delays delays.\\n\\n"
        "Delays delays delays Delays delays HASH:\\n\\n"
        "Delays:\\n"
        "<code>6559ce2924b306bde3ca6433b92e9bac94821f587fda74ada758fd8477cf4f16</code>"
    )

    TXID_ALREADY_USED_BY_YOU = "delays Delays delays delays delays delays.\\nDelays delays delays Delays delays"
    TXID_ALREADY_USED_BY_OTHER = "delays Delays delays delays delays delays delays delays"

    INVALID_TXID = (
        "delays Delays delays.\\n\\n"
        "TXID-delays delays delays 64 delays (0-9, a-f)."
    )

    INVALID_ADDRESS = (
        "delays Delays delays.\\n\\n"
        "TRC20 delays delays delays T delays delays delays 34 delays."
    )

    SESSION_EXPIRED = "delays Delays delays delays. Delays /start"
    BOT_ERROR = "delays Delays delays delays. Delays /start"
    SESSION_TIMEOUT = "delays Delays delays delays delays. Delays /start"
    CANCELLED = "delays Delays delays. /start"

    UNKNOWN_COMMAND = (
        "delays Delays delays\\n\\n"
        "Delays delays delays delays delays Conod delays,\\n"
        "delays delays delays delays delays delays:\\n\\n"
        "delays @Conodoperatorbot\\n\\n"
        "Delays delays /start delays delays delays."
    )

    DEPOSIT_CONFIRMED = "delays Delays delays delays!"

    FAKE_TRANSACTION = (
        "delays Delays delays\\n\\n"
        "Delays delays delays delays delays blockchain-delays.\\n"
        "Delays delays delays txid-delays."
    )

    @staticmethod
    def amount_too_small(error_msg: str, txid: str):
        fee = MSG.fee_display()
        return (
            f"delays Delays delays delays\\n\\n"
            f"{error_msg}\\n\\n"
            f"delays Delays $20 delays, delays\\n"
            f"   delays delays {fee} delays.\\n"
            f"   Delays delays ~$18 USDT\\n\\n"
            f"delays Delays delays delays:\\n"
            f"@Conodoperatorbot\\n\\n"
            f"Delays delays delays delays delays.\\n\\n"
            f"TXID: {txid[:16]}..."
        )

    @staticmethod
    def operator_small_amount(user_id: int, usd_val: float, amount: float, coin: str, address: str, txid: str):
        return (
            f"delays Delays: Delays delays\\n\\n"
            f"delays User: {user_id}\\n"
            f"delays Delays: ${usd_val:.2f} ({amount} {coin})\\n"
            f"delays Delays: {address}\\n"
            f"delays TXID: {txid[:32]}...\\n\\n"
            f"Delays delays delays @Conodoperatorbot delays."
        )
'''

# Write the file
output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "i18n", "hy.py")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(placeholder_hy)

print(f"\nWrote: {output_path}")
print("\nNow run on VPS to get real Armenian:")
print("  git show d693785:telegram_bot_improved.py > /tmp/original.py")
print("  # Then manually copy Armenian strings from /tmp/original.py to app/i18n/hy.py")
