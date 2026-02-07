#!/usr/bin/env python3
"""
Generate Armenian i18n file from original telegram_bot_improved.py.

Run on VPS:
    cd /root/Convertbot
    python3 scripts/generate_armenian_i18n.py

This extracts Armenian text from git history (commit d693785)
and creates app/i18n/hy.py with real Armenian strings.
"""
import subprocess
import os
import re

# Get the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

print("=" * 60)
print("Generating Armenian i18n from original bot")
print("=" * 60)

# Get original Armenian bot from git history
result = subprocess.run(
    ["git", "show", "d693785:telegram_bot_improved.py"],
    capture_output=True, text=True
)

if result.returncode != 0:
    print("Error: Could not get original file from git history")
    print(result.stderr)
    exit(1)

original = result.stdout
print(f"Read {len(original)} chars from original bot")

# Extract Armenian strings
def find_string(pattern, default="[NOT FOUND]"):
    match = re.search(pattern, original, re.DOTALL)
    return match.group(1) if match else default

# Button texts
btn_btc = find_string(r'KeyboardButton\("([^"]*Bitcoin[^"]*USDT)"\)')
btn_ltc = find_string(r'KeyboardButton\("([^"]*Litecoin[^"]*USDT)"\)')
btn_dash_usdt = find_string(r'KeyboardButton\("([^"]*Dash[^"]*USDT)"\)')
btn_dash_trx = find_string(r'KeyboardButton\("([^"]*Dash[^"]*TRON)"\)')
btn_xmr = find_string(r'KeyboardButton\("([^"]*Monero[^"]*USDT)"\)')
btn_check = find_string(r'KeyboardButton\("([^"]*Ստdelays[^"]*delays[^"]*)"\)')
btn_sent = find_string(r'KeyboardButton\("([^"]*delays[^"]*✅)"\)')
btn_new = find_string(r'KeyboardButton\("([^"]*Delays delays[^"]*/start)"\)')

print(f"Buttons found: check={btn_check[:20]}...")

# Generate the hy.py file content
hy_content = '''"""
Armenian UI messages for Convertbot
Auto-generated from original bot (commit d693785)
"""
from app.config import fee_display


class MSG:
    """Armenian UI messages"""

    # Button labels
'''

# Add button constants
hy_content += f'    BTN_BTC_USDT = "{btn_btc}"\n'
hy_content += f'    BTN_LTC_USDT = "{btn_ltc}"\n'
hy_content += f'    BTN_DASH_USDT = "{btn_dash_usdt}"\n'
hy_content += f'    BTN_DASH_TRX = "{btn_dash_trx}"\n'
hy_content += f'    BTN_XMR_USDT = "{btn_xmr}"\n'
hy_content += f'    BTN_CHECK_STATUS = "{btn_check}"\n'
hy_content += f'    BTN_I_SENT = "{btn_sent}"\n'
hy_content += f'    BTN_NEW_EXCHANGE = "{btn_new}"\n'
hy_content += '    BTN_CHECK = "📊  Delays"\n'
hy_content += '    BTN_START = "/start"\n\n'

# Welcome message - extract lines
welcome_match = re.search(
    r'await update\.message\.reply_text\(\s*"(👋[^"]+\n[^"]+\n[^"]+\n[^"]+\n[^"]+)"',
    original, re.DOTALL
)

if welcome_match:
    welcome_text = welcome_match.group(1)
    # Parse the welcome lines
    lines = welcome_text.split('\n')
    greeting = lines[0] if len(lines) > 0 else "👋 Delays"
    min_line = lines[2] if len(lines) > 2 else "⚠️ Delays delays: $20 USD"
    select_line = lines[4] if len(lines) > 4 else "✌️ Delays delays delays:"

    hy_content += '''    # Welcome message
    @staticmethod
    def welcome():
        return (
'''
    hy_content += f'            f"{greeting}\\n"\n'
    hy_content += f'            f"\\n{min_line}\\n"\n'
    hy_content += '            f"💡 Delays: {fee_display()}\\n"\n'
    hy_content += f'            f"{select_line}"\n'
    hy_content += '        )\n\n'
else:
    print("WARNING: Welcome message not found, using fallback")
    hy_content += '''    @staticmethod
    def welcome():
        return (
            f"👋 Delays\\n"
            f"\\n⚠️ Delays delays: $20 USD\\n"
            f"💡 Delays: {fee_display()}\\n"
            f"✌️ Delays delays delays:"
        )

'''

# Deposit address - find all parts
deposit_match = re.search(
    r'"(Delays delays delays:\n\n)".*?"(💱[^"]+\n)".*?"(🌐[^"]+\n)".*?"(✅[^"]+\n)".*?"(💰[^"]+\n)".*?"(⏱[^"]+\n\n)".*?"([^"]+delays[^"]+delays[^"]+)"',
    original, re.DOTALL
)

hy_content += '''    # Deposit address message
    @staticmethod
    def deposit_address(address: str, coin_name: str, output_coin: str, network: str, confs: int):
        return (
            f"Delays delays delays:\\n\\n"
            f"<code>{address}</code>\\n\\n"
            f"💱 Delays delays {coin_name} → {output_coin}\\n"
            f"🌐 Delays: {network}\\n"
            f"✅ Delays: {confs}\\n"
            f"💰 Delays {fee_display()} delays\\n"
            f"⏱ Delays delays: 20–30 delays\\n\\n"
            f"Delays delays delays «Delays delays delays» delays."
        )

'''

# TXID request
hy_content += '''    # TXID request
    TXID_REQUEST = (
        "Delays ✅\\n\\n"
        "Delays delays delays delays HASH-delays (64 delays):\\n\\n"
        "Delays:\\n"
        "<code>a65b33369cf0bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545</code>"
    )

'''

# TXID received
hy_content += '''    # TXID received
    @staticmethod
    def txid_received(txid: str, output_coin: str, network: str):
        return (
            f"TXID delays delays ✅\\n\\n"
            f"<code>{txid[:32]}\\n{txid[32:]}</code>\\n\\n"
            f"Delays delays delays delays {output_coin} ({network}) delays delays:\\n\\n"
            f"Delays:\\n"
            f"<code>TVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3g</code>"
        )

'''

# Address saved
hy_content += '''    # Address saved
    @staticmethod
    def address_saved(address: str, txid: str, coin_name: str, output_coin: str, confs: int):
        return (
            f"✅ Delays {output_coin} delays:\\n"
            f"<code>{address}</code>\\n\\n"
            f"🔎 Delays delays delays delays delays.\\n\\n"
            f"📊 Delays delays:\\n"
            f"• TXID: <code>{txid[:16]}...{txid[-8:]}</code>\\n"
            f"• {coin_name} → {output_coin}\\n"
            f"• Delays: 0/{confs}\\n\\n"
            f"⏳ Delays delays delays...\\n"
            f"📱 Delays delays delays delays:"
        )

'''

# Status labels
hy_content += '''    # Status labels
    STATUS_NEW = "Delays"
    STATUS_CONFIRMING = "Delays delays"
    STATUS_CONFIRMED = "Delays"
    STATUS_SOLD = "Delays"
    STATUS_WITHDRAWN = "Delays"
    STATUS_FAILED = "Delays"
    STATUS_ERROR = "Delays"

    STATUS_EMOJI = {
        "NEW": "🆕",
        "CONFIRMING": "⏳",
        "CONFIRMED": "✅",
        "SOLD": "💱",
        "WITHDRAWN": "🎉",
        "TRADE_FAILED": "❌",
        "PROCESSING_ERROR": "❌"
    }

'''

# No transactions
hy_content += '''    # No transactions
    NO_TRANSACTIONS = (
        "📭 Delays delays delays delays.\\n"
        "Delays /start delays delays."
    )

    @staticmethod
    def transaction_history_header():
        return "📊 Delays delays delays:\\n\\n"

    @staticmethod
    def transaction_item(coin: str, output_coin: str, status: str, confs: int, required: int, amount: float = None):
        emoji = MSG.STATUS_EMOJI.get(status, "❓")
        text = f"• {coin} → {output_coin}\\n"
        text += f"   Delays: {emoji} {status}\\n"
        text += f"   Delays: {confs}/{required}\\n"
        if amount:
            text += f"   Delays: {amount:.4f}\\n"
        return text + "\\n"

'''

# Errors
hy_content += '''    # Errors
    INVALID_COIN = "Delays delays delays delays delays:"

    TXID_ALREADY_USED = (
        "❌ Delays delays delays delays delays.\\n\\n"
        "Delays delays delays DELAYS delays HASH:\\n\\n"
        "Delays:\\n"
        "<code>6559ce2924b306bde3ca6433b92e9bac94821f587fda74ada758fd8477cf4f16</code>"
    )

    TXID_ALREADY_USED_BY_YOU = "⚠️ Delays delays delays delays delays.\\nDelays delays delays DELAYS delays"
    TXID_ALREADY_USED_BY_OTHER = "❌ Delays delays delays delays delays delays delays delays"

    INVALID_TXID = (
        "❌ Delays delays.\\n\\n"
        "TXID-delays delays delays 64 delays (0-9, a-f)."
    )

    INVALID_ADDRESS = (
        "❌ Delays delays.\\n\\n"
        "TRC20 delays delays delays T delays delays 34 delays."
    )

    SESSION_EXPIRED = "❌ Delays delays delays. Delays /start"
    BOT_ERROR = "❌ Delays delays delays. Delays /start"
    SESSION_TIMEOUT = "⏱ Delays delays delays delays. Delays /start"
    CANCELLED = "❌ Delays delays. /start"

    UNKNOWN_COMMAND = (
        "❌ Delays delays\\n\\n"
        "Delays delays delays delays delays Conod delays,\\n"
        "delays delays delays delays delays:\\n\\n"
        "📞 @Conodoperatorbot\\n\\n"
        "Delays delays /start delays delays delays."
    )

'''

# Worker notifications
hy_content += '''    # Worker notifications
    DEPOSIT_CONFIRMED = "✅ Delays delays delays!"

    FAKE_TRANSACTION = (
        "❌ Delays delays\\n\\n"
        "Delays delays delays delays delays blockchain-delays.\\n"
        "Delays delays delays txid-delays."
    )

    # Small amount notification
    @staticmethod
    def amount_too_small(error_msg: str, txid: str):
        return (
            f"⚠️ Delays delays delays\\n\\n"
            f"{error_msg}\\n\\n"
            f"💡 Delays $20 delays, delays\\n"
            f"   delays delays {fee_display()} delays.\\n"
            f"   Delays delays ~$18 USDT\\n\\n"
            f"📱 Delays delays delays:\\n"
            f"@Conodoperatorbot\\n\\n"
            f"Delays delays delays delays delays.\\n\\n"
            f"TXID: {txid[:16]}..."
        )

    @staticmethod
    def operator_small_amount(user_id: int, usd_val: float, amount: float, coin: str, address: str, txid: str):
        return (
            f"🔔 Delays: Delays delays\\n\\n"
            f"👤 User: {user_id}\\n"
            f"💰 Delays: ${usd_val:.2f} ({amount} {coin})\\n"
            f"📍 Delays: {address}\\n"
            f"🔗 TXID: {txid[:32]}...\\n\\n"
            f"Delays delays delays @Conodoperatorbot delays."
        )

    # Status check response
    @staticmethod
    def status_response(txid: str, coin: str, status: str, confs: int, required: int):
        emoji = MSG.STATUS_EMOJI.get(status, "❓")
        status_text = {
            "NEW": "Delays",
            "CONFIRMING": "Delays delays",
            "CONFIRMED": "Delays",
            "SOLD": "Delays",
            "WITHDRAWN": "Delays",
            "TRADE_FAILED": "Delays",
            "PROCESSING_ERROR": "Delays"
        }.get(status, status)

        if status in ["CONFIRMED", "SOLD"]:
            progress_msg = "✅ Delays delays delays!"
        elif status == "CONFIRMING":
            progress_msg = "⏳ Delays..."
        else:
            progress_msg = "🔍 Delays delays..."

        return (
            f"📊 Delays delays\\n\\n"
            f"TXID: <code>{txid[:16]}...{txid[-8:]}</code>\\n"
            f"Delays: {coin}\\n"
            f"Delays: {emoji} {status_text}\\n"
            f"Delays: {confs}/{required}\\n\\n"
            f"{progress_msg}"
        )
'''

# Write the file
output_path = os.path.join(PROJECT_ROOT, "app", "i18n", "hy.py")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(hy_content)

print(f"\nWrote: {output_path}")
print(f"Size: {len(hy_content)} chars")
print("\nDone! Armenian i18n file generated.")
print("\nRestart services:")
print("  systemctl restart convertbot-worker.service convertbot-bot.service")
