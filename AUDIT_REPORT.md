# 🔍 CONVERTBOT COMPREHENSIVE AUDIT REPORT
## Date: 2025-11-23

---

## ✅ SUMMARY
After full code review, I found **2 CRITICAL BUGS** that need fixing before testing.

---

## 🐛 CRITICAL BUGS FOUND

### BUG #1: XMR Withdrawals Ignore output_coin (CRITICAL!)
**Location:** `app/pipeline.py` lines 114-130

**Problem:**
XMR deposits withdraw immediately (line 114-130) but are **hardcoded to withdraw USDT only**. They don't check the `output_coin` field.

**Impact:**
- If user selects "Monero → USDT": Works ✅
- If user selects "Monero → TRON": Gets USDT instead of TRX ❌

**Current Code:**
```python
if deposit.coin == CoinType.XMR:
    # XMR: Already 10+ confs on MEXC, withdraw immediately...
    if settings.dry_run:
        logger.info(f"🧪 DRY RUN: Would withdraw {final_amount:.2f} USDT")
    else:
        success, result = mexc.withdraw_usdt_trc20(deposit.target_address, final_amount)  # ❌ Always USDT!
        if success:
            withdraw_id = result.get('withdraw_id')
            logger.info(f"✅ Withdrawal successful: {withdraw_id}")
            await db.update_deposit_status(deposit.txid, DepositStatus.WITHDRAWN)
            await _notify_success(deposit, final_amount, "USDT", withdraw_id)  # ❌ Always says "USDT"
```

**Fix Required:**
XMR withdrawals should use the same `withdraw_usdt_only()` function that handles TRX logic.

---

### BUG #2: _notify_success Function Hardcoded
**Location:** `app/pipeline.py` lines 149-161

**Problem:**
The `_notify_success()` function is only called by XMR code path and expects a `coin` parameter, but it's not checking deposit.output_coin.

**Impact:**
XMR withdrawals will always notify "You received X USDT" even if they should say TRX.

**Current Code:**
```python
async def _notify_success(deposit: Deposit, amount: float, coin: str, withdraw_id: str):
    """Notify user of successful withdrawal"""
    message = f"✅ Փոխանակումը ավարտված է!\n\n"
    message += f"💰 Ստացել եք: {amount:.2f} {coin}\n"  # Uses parameter, not deposit.output_coin
```

---

## ✅ FIXES ALREADY APPLIED (CORRECT)

### FIX #1: Database Functions Now Use _row_to_deposit ✅
**Files:** `app/db.py`
- `get_pending_deposits()` - Now uses `_row_to_deposit(row)`
- `get_deposit()` - Now uses `_row_to_deposit(row)`
- `get_user_deposits()` - Now uses `_row_to_deposit(row)`
- `_row_to_deposit()` - Properly extracts `output_coin` from database

**Status:** ✅ CORRECT

---

### FIX #2: BTC/LTC/DASH Withdrawals Check output_coin ✅
**File:** `app/pipeline.py` lines 178-271
- `withdraw_usdt_only()` function checks `deposit.output_coin`
- If TRX: Buys TRX with USDT, then withdraws TRX
- If USDT: Withdraws USDT directly
- Proper notifications for both

**Status:** ✅ CORRECT

---

### FIX #3: Telegram Bot Stores output_coin ✅
**File:** `telegram_bot_improved.py` line 218
- Bot correctly inserts `output_coin` into database

**Status:** ✅ CORRECT

---

## ⚠️ OTHER FINDINGS (NOT BUGS, BUT NOTES)

### 1. Supported Swap Pairs
**File:** `telegram_bot_improved.py` lines 59-80

Current supported swaps:
- ₿ Bitcoin → USDT ✅
- Ł Litecoin → USDT ✅
- 💎 Dash → USDT ✅
- 💎 Dash → TRON (TRX) ✅
- 🔒 Monero → USDT ✅

**Missing:**
- Monero → TRON - Bot doesn't offer this option
- Bitcoin → TRON - Bot doesn't offer this option
- Litecoin → TRON - Bot doesn't offer this option

**Note:** These are intentionally not offered, which is fine. Only DASH → TRON is supported.

---

### 2. Commission Calculation
**File:** `app/pipeline.py` line 94

Commission: 3% + $1 network fee

```python
commission = usdt_amount * (settings.commission_percent / 100)  # 3%
network_fee = 1.0  # Fixed $1
```

**Status:** Working as designed ✅

---

### 3. Early Sell System (Price Protection)
**File:** `app/worker.py` line 140-145

BTC/LTC sell at 2 confirmations, DASH sells at full confirmations, but withdrawal waits for full confirmations.

**Status:** Working as designed ✅

---

## 🔧 REQUIRED FIXES

### Fix XMR Withdrawal Path

**File:** `app/pipeline.py`

**Replace lines 114-130 with:**
```python
if deposit.coin == CoinType.XMR:
    # XMR: Already 10+ confs on MEXC, withdraw immediately...
    await db.update_deposit_status(deposit.txid, DepositStatus.SOLD)
    logger.info(f"✅ Marked as SOLD - ready for immediate withdrawal")

    # Use the same withdrawal function as BTC/LTC/DASH
    # This will check output_coin and withdraw USDT or TRX accordingly
    success = await withdraw_usdt_only(deposit)
    if success:
        await db.update_deposit_status(deposit.txid, DepositStatus.WITHDRAWN)
        logger.info(f"✅ XMR withdrawal complete!")
    else:
        logger.error(f"❌ XMR withdrawal failed")
        await db.update_deposit_status(deposit.txid, DepositStatus.WITHDRAWAL_FAILED)
```

**Explanation:**
- Mark XMR as SOLD (stores USDT amounts in database)
- Call `withdraw_usdt_only()` which has TRX logic
- Properly updates status based on result

---

## 📋 TESTING CHECKLIST

After applying fixes, test these scenarios:

### Test 1: DASH → USDT
- [  ] Send DASH, select USDT withdrawal
- [  ] Verify receives USDT (not TRX)
- [  ] Check message says "USDT"

### Test 2: DASH → TRON (TRX)
- [  ] Send DASH, select TRON withdrawal
- [  ] Verify receives TRX (not USDT)
- [  ] Check message says "TRX"
- [  ] Verify logs show "💱 Converting USDT → TRX"

### Test 3: XMR → USDT
- [  ] Send XMR, select USDT withdrawal
- [  ] Verify receives USDT immediately (after MEXC confirms)
- [  ] Check message says "USDT"

### Test 4: XMR → TRON (if bot adds this option)
- [  ] Would need to add to bot first
- [  ] Then test XMR → TRX flow

---

## 🎯 PRIORITY

**CRITICAL (Must Fix):**
1. ✅ Database functions use _row_to_deposit (DONE)
2. ❌ XMR withdrawal path needs fixing (TODO)

**OPTIONAL:**
- Add XMR → TRON, BTC → TRON, LTC → TRON swap options to bot

---

## 📊 CODE QUALITY ASSESSMENT

| Component | Status | Notes |
|-----------|--------|-------|
| Database Layer | ✅ GOOD | All functions use _row_to_deposit |
| Pipeline (BTC/LTC/DASH) | ✅ GOOD | Proper output_coin handling |
| Pipeline (XMR) | ❌ BROKEN | Hardcoded to USDT |
| Worker Logic | ✅ GOOD | Calls withdraw_usdt_only correctly |
| MEXC Client | ✅ GOOD | Has both USDT and TRX withdrawal methods |
| Telegram Bot | ✅ GOOD | Stores output_coin correctly |
| Error Handling | ✅ GOOD | Try/except blocks everywhere |
| Logging | ✅ EXCELLENT | Very detailed logging |

---

## 🚀 DEPLOYMENT PLAN

1. Apply XMR withdrawal fix
2. Clear Python cache (venv + project)
3. Restart services
4. Test DASH → TRON (should work now)
5. Test XMR → USDT (will work with fix)
6. Optionally add XMR → TRON to bot

---

## ✅ CONCLUSION

**Main Issue:** Only XMR withdrawals bypass the TRX logic.

**Fix:** Make XMR use the same `withdraw_usdt_only()` function.

**After Fix:** All coins (BTC, LTC, DASH, XMR) will properly check `output_coin` and withdraw USDT or TRX as requested.
