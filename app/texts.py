"""
Localized text strings for the bot.

ARCHITECTURE:
- This file contains ASCII-only placeholder text
- To add Armenian: edit this file directly on VPS
- Claude will NEVER modify text values - only reference keys

KEYS:
- error_generic: Generic error notification to user
- error_fake_tx: Transaction not found on blockchain
- error_amount_small: Deposit amount below minimum
- success_withdrawal: Successful withdrawal notification
- success_deposit_confirmed: Deposit confirmed notification
- admin_manual_fix: Admin alert for manual intervention
- admin_small_amount: Admin alert for small deposit
"""

TEXTS = {
    # User error messages
    "error_generic": (
        "[ERROR]\n\n"
        "Transaction: {txid}\n"
        "Reason: {error}\n\n"
        "We are working on this issue."
    ),

    "error_fake_tx": (
        "[INVALID TRANSACTION]\n\n"
        "This transaction was not found on blockchain.\n"
        "Please verify your TXID."
    ),

    "error_amount_small": (
        "[AMOUNT TOO SMALL]\n\n"
        "{error_msg}\n\n"
        "Minimum: $20 USD\n"
        "Fee: 3% + $1\n\n"
        "Contact support: @Conodoperatorbot\n"
        "We will process manually.\n\n"
        "TXID: {txid}"
    ),

    # Success messages
    "success_withdrawal": (
        "[SUCCESS]\n\n"
        "Received: {amount} {coin}\n"
        "Address: {address}\n"
        "Withdrawal ID: {wid}\n\n"
        "Thank you!"
    ),

    "success_deposit_confirmed": (
        "[DEPOSIT CONFIRMED]\n"
        "TxID: {txid}\n"
        "Coin: {coin}\n"
        "Confirmations: {confs}"
    ),

    # Admin notifications
    "admin_manual_fix": (
        "[MANUAL FIX NEEDED]\n\n"
        "Deposit {txid} failed {retries} times.\n"
        "Coin: {coin}\n"
        "User: {user_id}\n"
        "Address: {address}"
    ),

    "admin_small_amount": (
        "[SMALL AMOUNT ALERT]\n\n"
        "User: {user_id}\n"
        "Amount: ${usd_val} ({amount} {coin})\n"
        "Address: {address}\n"
        "TXID: {txid}\n\n"
        "User will contact @Conodoperatorbot"
    ),
}
