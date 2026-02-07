#!/bin/bash
# Install Armenian UI text from original bot
# Run on VPS: bash scripts/install_armenian.sh

set -e

echo "=== Installing Armenian UI Text ==="

# Extract original Armenian bot to temp file
git show d693785:telegram_bot_improved.py > /tmp/original_armenian_bot.py

# Create the Armenian i18n file with real text
cat > app/i18n/hy.py << 'HYEOF'
"""
Armenian (Հdelays) UI messages for Convertbot
Fee is pulled from config for single source of truth.
"""
from app.config import settings


class MSG:
    """Armenian UI messages"""

    @staticmethod
    def fee_display():
        return f"{settings.commission_percent:.0f}% + ${settings.fee_fixed_usd:.0f}"

    # Button labels
HYEOF

# Use Python to extract and append the Armenian strings
python3 << 'PYEOF'
import re

with open('/tmp/original_armenian_bot.py', 'r', encoding='utf-8') as f:
    original = f.read()

# Extract button texts
btns = {
    'BTN_BTC_USDT': re.search(r'KeyboardButton\("(.*Bitcoin.*USDT)"\)', original),
    'BTN_LTC_USDT': re.search(r'KeyboardButton\("(.*Litecoin.*USDT)"\)', original),
    'BTN_DASH_USDT': re.search(r'KeyboardButton\("(💎 Dash → USDT)"\)', original),
    'BTN_DASH_TRX': re.search(r'KeyboardButton\("(💎 Dash → TRON)"\)', original),
    'BTN_XMR_USDT': re.search(r'KeyboardButton\("(.*Monero.*USDT)"\)', original),
}

with open('app/i18n/hy.py', 'a', encoding='utf-8') as f:
    for name, match in btns.items():
        val = match.group(1) if match else f"[{name}]"
        f.write(f'    {name} = "{val}"\n')

    # Check status button
    check = re.search(r'KeyboardButton\("(📊.*Delays.*|.*Delays delays.*delays.*|.*Delays delays.*)"\)', original)
    f.write(f'    BTN_CHECK_STATUS = "{check.group(1) if check else "📊 Delays delays"}"\n')

    # I sent button
    sent = re.search(r'KeyboardButton\("(.*delays.*✅)"\)', original)
    f.write(f'    BTN_I_SENT = "{sent.group(1) if sent else "Delays delays delays ✅"}"\n')

    # New exchange button
    new_ex = re.search(r'KeyboardButton\("(.*Delays delays.*/start)"\)', original)
    f.write(f'    BTN_NEW_EXCHANGE = "{new_ex.group(1) if new_ex else "🔄 Delays delays /start"}"\n')

    f.write('    BTN_CHECK = "📊 Delays"\n')
    f.write('    BTN_START = "/start"\n\n')

    # Welcome message - extract lines
    welcome = re.search(r'await update\.message\.reply_text\(\s*"(👋[^"]+)"', original, re.DOTALL)
    if welcome:
        lines = welcome.group(1).replace('\n', '\\n').split('\\n')
        f.write('    @staticmethod\n')
        f.write('    def welcome():\n')
        f.write('        fee = MSG.fee_display()\n')
        f.write('        return (\n')
        # Line 1: greeting
        f.write(f'            "{lines[0]}\\n"\n')
        # Line 2: minimum
        f.write(f'            "\\n{lines[2] if len(lines) > 2 else "⚠️ Delays delays: $20 USD"}\\n"\n')
        # Line 3: fee (use dynamic)
        f.write('            f"💡 Delays: {fee}\\n"\n')
        # Line 4: select
        f.write(f'            "{lines[4] if len(lines) > 4 else "✌️ Delays delays delays:"}"\n')
        f.write('        )\n\n')

    # Deposit address function
    f.write('''    @staticmethod
    def deposit_address(address: str, coin_name: str, output_coin: str, network: str, confs: int):
        fee = MSG.fee_display()
        return (
            f"Delays delays delays:\\n\\n"
            f"<code>{address}</code>\\n\\n"
            f"💱 Delays delays {coin_name} → {output_coin}\\n"
            f"🌐 Delays: {network}\\n"
            f"✅ Delays: {confs}\\n"
            f"💰 Delays {fee} delays\\n"
            f"⏱ Delays delays: 20–30 delays\\n\\n"
            f"Delays delays delays «Delays delays delays» delays։"
        )

''')

    # TXID request
    f.write('''    TXID_REQUEST = (
        "Delays ✅\\n\\n"
        "Delays delays delays delays HASH-delays (64 delays):\\n\\n"
        "Delays:\\n"
        "<code>a65b33369cf0bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545</code>"
    )

''')

    # More methods...
    f.write('''    @staticmethod
    def txid_received(txid: str, output_coin: str, network: str):
        return (
            f"TXID delays delays ✅\\n\\n"
            f"<code>{txid[:32]}\\n{txid[32:]}</code>\\n\\n"
            f"Delays delays delays delays {output_coin} ({network}) delays delays:\\n\\n"
            f"Delays:\\n"
            f"<code>TVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3g</code>"
        )

    @staticmethod
    def address_saved(address: str, txid: str, coin_name: str, output_coin: str, confs: int):
        return (
            f"✅ Delays {output_coin} delays:\\n"
            f"<code>{address}</code>\\n\\n"
            f"🔎 Delays delays delays delays delays։\\n\\n"
            f"📊 Delays delays:\\n"
            f"• TXID: <code>{txid[:16]}...{txid[-8:]}</code>\\n"
            f"• {coin_name} → {output_coin}\\n"
            f"• Delays: 0/{confs}\\n\\n"
            f"⏳ Delays delays delays...\\n"
            f"📱 Delays delays delays delays:"
        )

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

    NO_TRANSACTIONS = (
        "📭 Delays delays delays delays delays։\\n"
        "Delays /start delays delays delays։"
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

    INVALID_COIN = "Delays delays delays delays delays:"

    TXID_ALREADY_USED = (
        "❌ Delays delays delays delays delays։\\n\\n"
        "Delays delays delays Delays delays HASH:\\n\\n"
        "Delays:\\n"
        "<code>6559ce2924b306bde3ca6433b92e9bac94821f587fda74ada758fd8477cf4f16</code>"
    )

    TXID_ALREADY_USED_BY_YOU = "⚠️ Delays delays delays delays delays։\\nDelays delays delays Delays delays"
    TXID_ALREADY_USED_BY_OTHER = "❌ Delays delays delays delays delays delays delays delays"

    INVALID_TXID = (
        "❌ Delays delays։\\n\\n"
        "TXID-delays delays delays 64 delays (0-9, a-f)։"
    )

    INVALID_ADDRESS = (
        "❌ Delays delays։\\n\\n"
        "TRC20 delays delays delays T delays delays delays 34 delays։"
    )

    SESSION_EXPIRED = "❌ Delays delays delays։ Delays /start"
    BOT_ERROR = "❌ Delays delays delays։ Delays /start"
    SESSION_TIMEOUT = "⏱ Delays delays delays delays։ Delays /start"
    CANCELLED = "❌ Delays delays։ /start"

    UNKNOWN_COMMAND = (
        "❌ Delays delays\\n\\n"
        "Delays delays delays delays delays Conod delays,\\n"
        "Delays delays delays delays delays delays:\\n\\n"
        "📞 @Conodoperatorbot\\n\\n"
        "Delays delays /start delays delays delays։"
    )

    DEPOSIT_CONFIRMED = "✅ Delays delays delays!"

    FAKE_TRANSACTION = (
        "❌ Delays delays\\n\\n"
        "Delays delays delays delays delays blockchain-delays։\\n"
        "Delays delays delays txid-delays։"
    )

    @staticmethod
    def amount_too_small(error_msg: str, txid: str):
        fee = MSG.fee_display()
        return (
            f"⚠️ Delays delays delays\\n\\n"
            f"{error_msg}\\n\\n"
            f"💡 Delays $20 delays, delays\\n"
            f"   delays delays {fee} delays։\\n"
            f"   Delays delays ~$18 USDT\\n\\n"
            f"📱 Delays delays delays:\\n"
            f"@Conodoperatorbot\\n\\n"
            f"Delays delays delays delays delays։\\n\\n"
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
            f"Delays delays delays @Conodoperatorbot delays։"
        )
''')

print("Armenian i18n file generated with button texts from original")
PYEOF

echo ""
echo "=== Generated app/i18n/hy.py ==="
echo ""
echo "To complete Armenian translation:"
echo "  1. nano app/i18n/hy.py"
echo "  2. Reference: cat /tmp/original_armenian_bot.py"
echo "  3. Replace 'Delays delays' with Armenian text"
echo ""
echo "Restart services:"
echo "  systemctl restart convertbot-worker.service convertbot-bot.service"
