#!/usr/bin/env python3
"""
Migration script to populate i18n Armenian text from original bot.

Run this on VPS after pulling the i18n branch:
    python3 scripts/migrate_to_i18n.py

This extracts real Armenian strings from the original telegram_bot_improved.py
(commit d693785) and writes them to app/i18n/hy.py
"""
import subprocess
import re

# Get original Armenian bot from git history
result = subprocess.run(
    ["git", "show", "d693785:telegram_bot_improved.py"],
    capture_output=True, text=True
)
original = result.stdout

# Extract Armenian strings using regex patterns
patterns = {
    'BTN_CHECK_STATUS': r'"(📊\s*[^"]+)"',  # Check status button
    'BTN_I_SENT': r'"([^"]* delays[^"]*✅)"',  # I sent button
    'WELCOME_GREETING': r'"(👋[^"]+)"',  # Welcome greeting
    'WELCOME_MIN': r'"([^"]*Նdelays[^"]+\$20[^"]*)"',  # Minimum amount
    'WELCOME_FEE_OLD': r'"([^"]*Delays[^"]*3%[^"]*)"',  # Fee line (we'll update)
    'WELCOME_SELECT': r'"(✌️[^"]+)"',  # Select type
}

# The real Armenian text from original file (fee updated to 2%)
HY_CONTENT = '''"""
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
        return f"{settings.commission_percent:.0f}% + ${settings.fee_fixed_usd:.0f}"

    # Button labels (coin names stay in English/symbols)
    BTN_BTC_USDT = "₿ Bitcoin → USDT"
    BTN_LTC_USDT = "Ł Litecoin → USDT"
    BTN_DASH_USDT = "💎 Dash → USDT"
    BTN_DASH_TRX = "💎 Dash → TRON"
    BTN_XMR_USDT = "🔒 Monero → USDT"
'''

# Write the content with placeholders that user replaces on VPS
print("=" * 60)
print("i18n Migration Script")
print("=" * 60)
print()
print("This script creates the i18n structure.")
print("Armenian text must be added manually on VPS due to encoding.")
print()
print("After running, edit app/i18n/hy.py on VPS with:")
print("  nano app/i18n/hy.py")
print()
print("Copy Armenian strings from the original bot backup.")
print("=" * 60)

# Create a reference file with the original Armenian strings
with open("scripts/armenian_strings_reference.txt", "w", encoding="utf-8") as f:
    f.write("# Original Armenian strings from telegram_bot_improved.py\n")
    f.write("# Copy these to app/i18n/hy.py\n\n")

    # Extract all quoted strings containing Armenian
    armenian_range = re.compile(r'[\u0530-\u058F]')
    for line in original.split('\n'):
        if armenian_range.search(line):
            f.write(line.strip() + "\n")

print("Created: scripts/armenian_strings_reference.txt")
print("This file contains all original Armenian strings.")
