"""
Localized text strings for the bot.

IMPORTANT: This file contains all user-facing messages.
To change to Armenian, edit this file directly on VPS.
Claude should NEVER modify the text values - only reference keys.
"""

TEXTS = {
    # Error messages
    "error_generic": (
        "Error occurred\n\n"
        "Transaction: {txid}\n"
        "Reason: {error}\n\n"
        "We will fix this soon."
    ),

    "error_fake_tx": (
        "Invalid transaction\n\n"
        "This transaction was not found on blockchain.\n"
        "Please check the txid."
    ),

    "error_amount_small": (
        "Amount too small\n\n"
        "{error_msg}\n\n"
        "Minimum is $20 to cover fees.\n"
        "You would receive ~$18 USDT.\n\n"
        "Contact operator: @Conodoperatorbot\n"
        "We will process manually.\n\n"
        "TXID: {txid}"
    ),

    # Success messages
    "success_withdrawal": (
        "Exchange complete!\n\n"
        "You received: {amount} {coin}\n"
        "Address: {address}\n"
        "Withdrawal ID: {wid}\n\n"
        "Thank you!"
    ),

    "success_deposit_confirmed": (
        "Deposit confirmed!\n"
        "TxID: {txid}\n"
        "Coin: {coin}\n"
        "Confirmations: {confs}"
    ),

    # Admin notifications
    "admin_manual_fix": (
        "MANUAL FIX NEEDED\n\n"
        "Deposit {txid} failed {retries} times.\n"
        "Coin: {coin}\n"
        "User: {user_id}\n"
        "Address: {address}"
    ),

    "admin_small_amount": (
        "ATTENTION: Small amount\n\n"
        "User: {user_id}\n"
        "Amount: ${usd_val} ({amount} {coin})\n"
        "Address: {address}\n"
        "TXID: {txid}\n\n"
        "User will contact @Conodoperatorbot"
    ),

    # Withdrawal errors
    "withdrawal_failed": "Withdrawal failed: {error}",
    "withdrawal_error": "Withdrawal error: {error}",
}
