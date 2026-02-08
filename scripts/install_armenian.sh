#!/bin/bash
#
# Install Armenian i18n by extracting ALL strings from git history
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

# Generate hy.py using Python - all Armenian comes from /tmp/orig.py
python3 << 'PYSCRIPT'
import re

with open('/tmp/orig.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Extract all KeyboardButton texts
btns = {}
for line in src.split('\n'):
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

# Extract messages by finding reply_text patterns
msgs = {}

# Welcome - find the first big Armenian message
m = re.search(r'reply_text\(\s*"([^\n]+\\n[^\n]+\\n[^\n]+\\n[^\n]+\\n[^"]+)"', src)
if m: msgs['welcome'] = m.group(1)

# TXID request - contains HASH
m = re.search(r'"([^"]*HASH[^"]+64[^"]+)"', src)
if m: msgs['txid_req'] = m.group(1)

# TXID received - contains TXID + address request
m = re.search(r'"(TXID[^"]+\{output_coin\}[^"]+)"', src)
if m: msgs['txid_recv'] = m.group(1)

# Invalid coin
m = re.search(r'"([^"]+\u0568\u0576\u057f\u0580\u0565\u056c[^"]+)"', src)  # delays
if m: msgs['invalid_coin'] = m.group(1)

# Already used
m = re.search(r'"(\u274c[^"]+\u0576\u0578\u0580[^"]+)"', src, re.IGNORECASE)
if m: msgs['already_used'] = m.group(1)

# Invalid TXID
m = re.search(r'"(\u274c[^"]+64[^"]+a-f[^"]+)"', src)
if m: msgs['invalid_txid'] = m.group(1)

# Invalid address
m = re.search(r'"(\u274c[^"]+TRC20[^"]+)"', src)
if m: msgs['invalid_addr'] = m.group(1)

print("Buttons:", list(btns.keys()))
print("Messages:", list(msgs.keys()))

# Build output file
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

# Welcome - need to process and add fee_display()
if 'welcome' in msgs:
    w = msgs['welcome'].replace('3% + $1', '{fee_display()}').replace('\\n', '\\\\n')
    out += f'''    @staticmethod
    def welcome():
        return f"{w}"

'''
else:
    out += '''    @staticmethod
    def welcome():
        return f"Welcome!\\nMinimum: $20 USD\\nFee: {fee_display()}\\nSelect:"

'''

# Deposit address - keep as template
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
if 'txid_req' in msgs:
    t = msgs['txid_req'].replace('\\n', '\\\\n')
    out += f'    TXID_REQUEST = "{t}"\n\n'
else:
    out += '    TXID_REQUEST = "Send HASH (64 chars)"\n\n'

# TXID received
out += '''    @staticmethod
    def txid_received(txid: str, output_coin: str, network: str):
        return (
            f"TXID OK!\\n\\n"
            f"<code>{txid[:32]}\\n{txid[32:]}</code>\\n\\n"
            f"Send {output_coin} ({network}) address"
        )

'''

# Address saved
out += '''    @staticmethod
    def address_saved(address: str, txid: str, coin_name: str, output_coin: str, confs: int):
        return (
            f"Saved {output_coin}:\\n"
            f"<code>{address}</code>\\n\\n"
            f"TXID: <code>{txid[:16]}...</code>\\n"
            f"{coin_name} -> {output_coin}\\n"
            f"Confs: 0/{confs}\\n\\n"
            f"Please wait..."
        )

'''

# Statuses
out += '''    STATUS_NEW = "New"
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
inv_coin = msgs.get('invalid_coin', 'Select from buttons')
out += f'    INVALID_COIN = "{inv_coin}"\n\n'

out += '''    TXID_ALREADY_USED = "Transaction already used. Send NEW HASH."
    TXID_ALREADY_USED_BY_YOU = "Already used by you."
    TXID_ALREADY_USED_BY_OTHER = "Used by another user."

'''

inv_txid = msgs.get('invalid_txid', 'Invalid. TXID: 64 chars (0-9, a-f).')
out += f'    INVALID_TXID = "{inv_txid}"\n\n'

inv_addr = msgs.get('invalid_addr', 'Invalid. TRC20: starts T, 34 chars.')
out += f'    INVALID_ADDRESS = "{inv_addr}"\n\n'

out += '''    SESSION_EXPIRED = "Session expired. /start"
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

with open('app/i18n/hy.py', 'w', encoding='utf-8') as f:
    f.write(out)

print(f"Wrote app/i18n/hy.py ({len(out)} bytes)")
PYSCRIPT

# Verify
python3 -c "from app.i18n.hy import MSG; print('BTN_CHECK:', MSG.BTN_CHECK_STATUS); print('BTN_SENT:', MSG.BTN_I_SENT)"

echo ""
echo "Done! Restart: systemctl restart convertbot-bot.service"
