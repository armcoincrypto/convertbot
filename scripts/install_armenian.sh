#!/bin/bash
#
# Install proper Armenian i18n file from git history
# Run on VPS: bash scripts/install_armenian.sh
#

set -e

cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "=============================================="
echo "Installing Armenian i18n from git history"
echo "=============================================="

# Extract original Armenian bot
echo "Extracting original Armenian bot from commit d693785..."
git show d693785:telegram_bot_improved.py > /tmp/armenian_original.py

# Check if extraction worked
if [ ! -s /tmp/armenian_original.py ]; then
    echo "Error: Could not extract original file from git history"
    exit 1
fi

echo "Creating Armenian i18n file..."

# Use Python to parse and generate the file
python3 - << 'PYTHON_SCRIPT'
import re
import sys

# Read original file
with open('/tmp/armenian_original.py', 'r', encoding='utf-8') as f:
    original = f.read()

print(f"Read {len(original)} chars from original")

# Extract KeyboardButton texts
buttons = {}
for line in original.split('\n'):
    if 'KeyboardButton' in line:
        m = re.search(r'KeyboardButton\("([^"]+)"\)', line)
        if m:
            text = m.group(1)
            # Check for Armenian characters (Unicode range 0530-058F)
            has_armenian = any('\u0530' <= c <= '\u058F' for c in text)
            
            if 'Bitcoin' in text:
                buttons['btc'] = text
            elif 'Litecoin' in text:
                buttons['ltc'] = text
            elif 'Dash' in text and 'TRON' in text:
                buttons['dash_trx'] = text
            elif 'Dash' in text:
                buttons['dash_usdt'] = text
            elif 'Monero' in text:
                buttons['xmr'] = text
            elif has_armenian:
                if '\u054d\u057f\u0578\u0582\u0563' in text:  # Armenian for "check"
                    buttons['check'] = text
                elif '✅' in text:
                    buttons['sent'] = text

print("Buttons found:")
for k, v in buttons.items():
    print(f"  {k}: {v}")

# Write hy.py
output = '''"""
Armenian UI messages for Convertbot
Auto-generated from original bot (commit d693785)
"""
from app.config import fee_display


class MSG:
    """Armenian UI messages"""

    # Button labels
'''

output += f'    BTN_BTC_USDT = "{buttons.get("btc", "Bitcoin -> USDT")}"\n'
output += f'    BTN_LTC_USDT = "{buttons.get("ltc", "Litecoin -> USDT")}"\n'
output += f'    BTN_DASH_USDT = "{buttons.get("dash_usdt", "Dash -> USDT")}"\n'
output += f'    BTN_DASH_TRX = "{buttons.get("dash_trx", "Dash -> TRON")}"\n'
output += f'    BTN_XMR_USDT = "{buttons.get("xmr", "Monero -> USDT")}"\n'
output += f'    BTN_CHECK_STATUS = "{buttons.get("check", "Check Status")}"\n'
output += f'    BTN_I_SENT = "{buttons.get("sent", "I sent")}"\n'

# Rest of the template (messages that need Armenian)
output += '''    BTN_NEW_EXCHANGE = "New /start"
    BTN_CHECK = "Check"
    BTN_START = "/start"

    @staticmethod
    def welcome():
        return (
            f"Welcome!\\n"
            f"\\nMinimum: $20 USD\\n"
            f"Fee: {fee_display()}\\n"
            f"Select type:"
        )

    @staticmethod
    def deposit_address(address: str, coin_name: str, output_coin: str, network: str, confs: int):
        return (
            f"Your address:\\n\\n"
            f"<code>{address}</code>\\n\\n"
            f"Selected: {coin_name} -> {output_coin}\\n"
            f"Network: {network}\\n"
            f"Confirmations: {confs}\\n"
            f"Fee: {fee_display()}\\n"
            f"Time: 20-30 min\\n\\n"
            f"After sending click I sent."
        )

    TXID_REQUEST = (
        "Received!\\n\\n"
        "Send HASH (64 chars):\\n\\n"
        "Example:\\n"
        "<code>a65b33369cf0bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545</code>"
    )

    @staticmethod
    def txid_received(txid: str, output_coin: str, network: str):
        return (
            f"TXID received!\\n\\n"
            f"<code>{txid[:32]}\\n{txid[32:]}</code>\\n\\n"
            f"Send your {output_coin} ({network}) address:\\n\\n"
            f"Example:\\n"
            f"<code>TVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3g</code>"
        )

    @staticmethod
    def address_saved(address: str, txid: str, coin_name: str, output_coin: str, confs: int):
        return (
            f"Saved {output_coin} address:\\n"
            f"<code>{address}</code>\\n\\n"
            f"Checking transfer...\\n\\n"
            f"Details:\\n"
            f"* TXID: <code>{txid[:16]}...{txid[-8:]}</code>\\n"
            f"* {coin_name} -> {output_coin}\\n"
            f"* Confs: 0/{confs}\\n\\n"
            f"Please wait...\\n"
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
        "No transactions.\\n"
        "Click /start to begin."
    )

    @staticmethod
    def transaction_history_header():
        return "Transactions:\\n\\n"

    @staticmethod
    def transaction_item(coin: str, output_coin: str, status: str, confs: int, required: int, amount: float = None):
        emoji = MSG.STATUS_EMOJI.get(status, "?")
        text = f"* {coin} -> {output_coin}\\n"
        text += f"   Status: {emoji} {status}\\n"
        text += f"   Confs: {confs}/{required}\\n"
        if amount:
            text += f"   Amount: {amount:.4f}\\n"
        return text + "\\n"

    INVALID_COIN = "Select from buttons:"

    TXID_ALREADY_USED = (
        "Transaction used.\\n\\n"
        "Send NEW HASH:\\n\\n"
        "Example:\\n"
        "<code>6559ce2924b306bde3ca6433b92e9bac94821f587fda74ada758fd8477cf4f16</code>"
    )

    TXID_ALREADY_USED_BY_YOU = "Already used by you.\\nSend NEW."
    TXID_ALREADY_USED_BY_OTHER = "Used by another user."

    INVALID_TXID = (
        "Invalid format.\\n\\n"
        "TXID: 64 chars (0-9, a-f)."
    )

    INVALID_ADDRESS = (
        "Invalid address.\\n\\n"
        "TRC20: starts T, 34 chars."
    )

    SESSION_EXPIRED = "Session expired. /start"
    BOT_ERROR = "Error. Try /start"
    SESSION_TIMEOUT = "Timeout. /start"
    CANCELLED = "Cancelled. /start"

    UNKNOWN_COMMAND = (
        "Unknown command.\\n\\n"
        "Contact operator:\\n\\n"
        "@Conodoperatorbot\\n\\n"
        "Or /start for new exchange."
    )

    DEPOSIT_CONFIRMED = "Deposit confirmed!"

    FAKE_TRANSACTION = (
        "Invalid transaction.\\n\\n"
        "Not found on blockchain.\\n"
        "Check txid."
    )

    @staticmethod
    def amount_too_small(error_msg: str, txid: str):
        return (
            f"Amount insufficient.\\n\\n"
            f"{error_msg}\\n\\n"
            f"Minimum $20, after {fee_display()} fee\\n"
            f"you get ~$18 USDT\\n\\n"
            f"Contact:\\n"
            f"@Conodoperatorbot\\n\\n"
            f"Manual processing.\\n\\n"
            f"TXID: {txid[:16]}..."
        )

    @staticmethod
    def operator_small_amount(user_id: int, usd_val: float, amount: float, coin: str, address: str, txid: str):
        return (
            f"ATTENTION: Small\\n\\n"
            f"User: {user_id}\\n"
            f"Amount: ${usd_val:.2f} ({amount} {coin})\\n"
            f"Address: {address}\\n"
            f"TXID: {txid[:32]}...\\n\\n"
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
            f"Status\\n\\n"
            f"TXID: <code>{txid[:16]}...{txid[-8:]}</code>\\n"
            f"Coin: {coin}\\n"
            f"Status: {emoji} {status_text}\\n"
            f"Confs: {confs}/{required}\\n\\n"
            f"{progress_msg}"
        )
'''

with open('app/i18n/hy.py', 'w', encoding='utf-8') as f:
    f.write(output)

print(f"\nWrote app/i18n/hy.py ({len(output)} chars)")
PYTHON_SCRIPT

echo ""
echo "=============================================="
echo "Installation complete!"
echo "=============================================="
echo ""
echo "Restart services:"
echo "  systemctl restart convertbot-bot.service convertbot-worker.service"
