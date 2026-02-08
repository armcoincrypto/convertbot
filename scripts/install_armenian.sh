#!/bin/bash
#
# Install Armenian i18n by extracting strings from git history
# Run on VPS: bash scripts/install_armenian.sh
#
set -e
cd "$(dirname "$0")/.."

echo "=============================================="
echo "Extracting Armenian i18n from git history"
echo "=============================================="

# Extract original file
git show d693785:telegram_bot_improved.py > /tmp/orig.py
echo "Extracted original ($(wc -c < /tmp/orig.py) bytes)"

# Generate hy.py using Python - SAFE extraction of string literals only
python3 << 'PYSCRIPT'
import re

with open('/tmp/orig.py', 'r', encoding='utf-8') as f:
    src = f.read()
    lines = src.split('\n')

# Extract KeyboardButton texts
btns = {}
for line in lines:
    m = re.search(r'KeyboardButton\("([^"]+)"\)', line)
    if m:
        t = m.group(1)
        if 'Bitcoin' in t: btns['btc'] = t
        elif 'Litecoin' in t: btns['ltc'] = t
        elif 'Dash' in t and 'TRON' in t: btns['dash_trx'] = t
        elif 'Dash' in t: btns['dash_usdt'] = t
        elif 'Monero' in t: btns['xmr'] = t
        elif any('\u0530' <= c <= '\u058F' for c in t):
            if '\u054d\u057f\u0578\u0582\u0563' in t: btns['check'] = t
            elif '\u0565\u0574' in t: btns['sent'] = t

def extract_string_block(lines, start_pattern, end_patterns=['reply_markup', 'parse_mode']):
    """Extract ONLY string literals from a reply_text block."""
    result = []
    in_block = False

    for i, line in enumerate(lines):
        if start_pattern in line:
            in_block = True
            continue

        if in_block:
            # Stop if we hit non-string content
            stripped = line.strip()
            if any(ep in stripped for ep in end_patterns):
                break
            if stripped.startswith(')'):
                break
            if 'return ' in stripped:
                break
            if stripped.startswith('async ') or stripped.startswith('def '):
                break

            # Extract only quoted string content
            # Match: "..." or f"..."
            m = re.match(r'\s*(?:f)?"([^"]*)"', line)
            if m:
                result.append(m.group(1))
            else:
                # No more strings, stop
                if stripped and not stripped.startswith('#'):
                    break

    return ''.join(result) if result else None

# Extract welcome message from start() function
welcome = extract_string_block(lines, 'async def start')
if not welcome:
    # Try finding the first reply_text with Armenian greeting
    for i, line in enumerate(lines):
        if 'reply_text(' in line and i < 100:  # Only in first 100 lines
            welcome = extract_string_block(lines[i:], 'reply_text(')
            if welcome and '\u0532\u0561\u0580\u0587' in welcome:  # Delays
                break
            welcome = None

# Extract invalid coin message
invalid_coin = None
for i, line in enumerate(lines):
    m = re.search(r'reply_text\("([^"]+\u0568\u0576\u057f\u0580\u0565\u056c[^"]+)"\)', line)
    if m:
        invalid_coin = m.group(1)
        break

# Extract TXID request (Delays = Received)
txid_req = None
for i, line in enumerate(lines):
    m = re.search(r'"(\u054d\u057f\u0561\u0581\u057e\u0565\u0581[^"]+)"', line)
    if m:
        txid_req = m.group(1)
        break

print("Buttons:", list(btns.keys()))
print("Welcome:", "FOUND" if welcome else "NOT FOUND")
if welcome:
    # Show first 60 chars, ensure no code leaked
    preview = welcome[:60].replace('\n', '\\n')
    print(f"  Preview: {preview}...")

# Build output file - CLEAN strings only
out = '''# -*- coding: utf-8 -*-
"""Armenian UI messages for Convertbot - extracted from commit d693785"""
from app.config import fee_display


class MSG:
    """Armenian UI messages"""

'''

# Buttons
out += f'    BTN_BTC_USDT = "{btns.get("btc", "Bitcoin -> USDT")}"\n'
out += f'    BTN_LTC_USDT = "{btns.get("ltc", "Litecoin -> USDT")}"\n'
out += f'    BTN_DASH_USDT = "{btns.get("dash_usdt", "Dash -> USDT")}"\n'
out += f'    BTN_DASH_TRX = "{btns.get("dash_trx", "Dash -> TRON")}"\n'
out += f'    BTN_XMR_USDT = "{btns.get("xmr", "Monero -> USDT")}"\n'
out += f'    BTN_CHECK_STATUS = "{btns.get("check", "Check")}"\n'
out += f'    BTN_I_SENT = "{btns.get("sent", "I sent")}"\n'
out += '    BTN_NEW_EXCHANGE = "/start"\n'
out += '    BTN_CHECK = "Check"\n'
out += '    BTN_START = "/start"\n\n'

# Welcome - use extracted or fallback
if welcome:
    # Replace fee placeholder and escape properly
    w = welcome.replace('3% + $1', '{fee_display()}')
    # Escape backslashes and quotes for Python string
    w = w.replace('\\', '\\\\').replace('"', '\\"')
    # Convert actual newlines to \n
    w = w.replace('\n', '\\n')
    out += f'''    @staticmethod
    def welcome():
        return f"{w}"

'''
else:
    out += '''    @staticmethod
    def welcome():
        return f"Welcome!\\nMinimum: $20 USD\\nFee: {fee_display()}\\nSelect:"

'''

# Rest of the template with safe defaults
out += '''    @staticmethod
    def deposit_address(address: str, coin_name: str, output_coin: str, network: str, confs: int):
        return (
            f"Address:\\n\\n"
            f"<code>{address}</code>\\n\\n"
            f"{coin_name} -> {output_coin}\\n"
            f"Network: {network}\\n"
            f"Confirmations: {confs}\\n"
            f"Fee: {fee_display()}\\n"
            f"Time: 20-30 min"
        )

'''

# TXID request
if txid_req:
    t = txid_req.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    out += f'    TXID_REQUEST = "{t}"\n\n'
else:
    out += '    TXID_REQUEST = "Send HASH (64 chars)"\n\n'

out += '''    @staticmethod
    def txid_received(txid: str, output_coin: str, network: str):
        return (
            f"TXID OK!\\n\\n"
            f"<code>{txid[:32]}\\n{txid[32:]}</code>\\n\\n"
            f"Send {output_coin} ({network}) address"
        )

    @staticmethod
    def address_saved(address: str, txid: str, coin_name: str, output_coin: str, confs: int):
        return (
            f"Saved {output_coin}:\\n"
            f"<code>{address}</code>\\n\\n"
            f"TXID: <code>{txid[:16]}...</code>\\n"
            f"{coin_name} -> {output_coin}\\n"
            f"Confs: 0/{confs}\\n\\n"
            f"Please wait..."
        )

    STATUS_NEW = "New"
    STATUS_CONFIRMING = "Confirming"
    STATUS_CONFIRMED = "Confirmed"
    STATUS_SOLD = "Sold"
    STATUS_WITHDRAWN = "Done"
    STATUS_FAILED = "Failed"
    STATUS_ERROR = "Error"

    STATUS_EMOJI = {
        "NEW": "new", "CONFIRMING": "wait", "CONFIRMED": "ok",
        "SOLD": "sold", "WITHDRAWN": "done",
        "TRADE_FAILED": "fail", "PROCESSING_ERROR": "err"
    }

    NO_TRANSACTIONS = "No transactions. /start"

    @staticmethod
    def transaction_history_header():
        return "Transactions:\\n\\n"

    @staticmethod
    def transaction_item(coin: str, output_coin: str, status: str, confs: int, required: int, amount: float = None):
        emoji = MSG.STATUS_EMOJI.get(status, "?")
        text = f"* {coin} -> {output_coin}\\n   Status: {emoji}\\n   Confs: {confs}/{required}\\n"
        if amount: text += f"   Amount: {amount:.4f}\\n"
        return text + "\\n"

'''

# Error messages
if invalid_coin:
    inv = invalid_coin.replace('\\', '\\\\').replace('"', '\\"')
    out += f'    INVALID_COIN = "{inv}"\n\n'
else:
    out += '    INVALID_COIN = "Select from buttons"\n\n'

out += '''    TXID_ALREADY_USED = "Transaction already used. Send NEW HASH."
    TXID_ALREADY_USED_BY_YOU = "Already used by you."
    TXID_ALREADY_USED_BY_OTHER = "Used by another user."

    INVALID_TXID = "Invalid. TXID: 64 chars (0-9, a-f)."

    INVALID_ADDRESS = "Invalid. TRC20: starts T, 34 chars."

    SESSION_EXPIRED = "Session expired. /start"
    BOT_ERROR = "Error. /start"
    SESSION_TIMEOUT = "Timeout. /start"
    CANCELLED = "Cancelled. /start"

    UNKNOWN_COMMAND = "Unknown. Contact @Conodoperatorbot or /start"

    DEPOSIT_CONFIRMED = "Deposit confirmed!"

    FAKE_TRANSACTION = "Invalid transaction. Not found on blockchain."

    @staticmethod
    def amount_too_small(error_msg: str, txid: str):
        return f"Amount too small.\\n{error_msg}\\nContact @Conodoperatorbot\\nTXID: {txid[:16]}..."

    @staticmethod
    def operator_small_amount(user_id: int, usd_val: float, amount: float, coin: str, address: str, txid: str):
        return f"SMALL AMOUNT\\nUser: {user_id}\\n${usd_val:.2f} ({amount} {coin})\\n{address}\\n{txid[:32]}..."

    @staticmethod
    def status_response(txid: str, coin: str, status: str, confs: int, required: int):
        emoji = MSG.STATUS_EMOJI.get(status, "?")
        return f"Status: {emoji} {status}\\nTXID: {txid[:16]}...\\n{coin}\\nConfs: {confs}/{required}"
'''

# Write file
with open('app/i18n/hy.py', 'w', encoding='utf-8') as f:
    f.write(out)

print(f"Wrote app/i18n/hy.py ({len(out)} bytes)")

# VALIDATION: Check for code leakage (bot code that shouldn't be there)
bad_patterns = [
    'async def',           # Bot function definitions
    'reply_markup=',       # Bot code
    'ConversationHandler', # Bot code
    'await ',              # Bot async code
    'context.',            # Bot context
    'update.',             # Bot update object
    'CHOOSING_COIN',       # Bot state
    '.reply_text(',        # Bot method calls
]
with open('app/i18n/hy.py', 'r') as f:
    content = f.read()
    for pat in bad_patterns:
        if pat in content:
            print(f"ERROR: Found code fragment '{pat}' in hy.py!")
            exit(1)

print("Validation: OK (no code leakage)")
PYSCRIPT

# Verify Python syntax
echo "Checking Python syntax..."
python3 -m py_compile app/i18n/hy.py || { echo "SYNTAX ERROR in hy.py!"; exit 1; }

# Verify import works
python3 -c "from app.i18n.hy import MSG; print('BTN_CHECK:', MSG.BTN_CHECK_STATUS); print('Welcome preview:', MSG.welcome()[:50])"

# Verify API compatibility with en/ru
echo "Checking API compatibility..."
python3 scripts/check_i18n.py || { echo "API MISMATCH!"; exit 1; }

echo ""
echo "=============================================="
echo "Installation complete!"
echo "=============================================="
echo "Restart: systemctl restart convertbot-bot.service"
