# 🛡️ Spam Protection - How Your Bot Handles Abuse

## Your Current Spam Protection (Already Built-In)

### 1. **Rate Limiting** ⏱️
**What happens:** User tries to start multiple swaps quickly

**Protection:**
```
User tries /start → Selects coin
Rate limit: Must wait 30 seconds between swap requests
If spam: "⏱ Սպասեք XX վայրկյան" message
```

**Example:**
- 9:00:00 - User starts swap #1 ✅ Allowed
- 9:00:15 - User starts swap #2 ❌ Blocked (wait 15 seconds)
- 9:00:35 - User starts swap #2 ✅ Allowed (30s passed)

**Code:** `telegram_bot_improved.py` line 102-110

---

### 2. **Daily Quotas** 📊
**What happens:** User tries to make too many swaps in one day

**Protection:**
```
Daily limits per user:
- Maximum 10 swaps per day
- Maximum $10,000 USD volume per day
```

**Example:**
- User makes 10 swaps today ✅ All allowed
- User tries swap #11 ❌ Blocked until tomorrow
- Shows: "❌ Օրական սահմանաչափը գերազանցված է"

**Code:** `telegram_bot_improved.py` line 113-124

---

### 3. **Unpaid Deposits - Auto Cleanup** 🧹
**What happens:** User opens order but never pays

**Protection:**
```
Deposit lifecycle:
1. User submits TXID → Status: NEW
2. If not paid within 24 hours → Auto-deleted
3. Database cleaned up, no storage wasted
```

**Cleanup function:** `app/worker.py` line 36-51
```python
async def cleanup_old_deposits():
    """Delete unconfirmed deposits older than 24 hours"""
    # Removes NEW/CONFIRMING deposits > 24 hours old
    # Prevents database bloat from unpaid orders
```

**What this means:**
- User spam creates fake orders ❌ Deleted after 24 hours automatically
- No manual intervention needed ✅
- Database stays clean ✅

---

### 4. **Duplicate TXID Protection** 🔒
**What happens:** User tries to reuse the same transaction

**Protection:**
```
Every TXID can only be used ONCE
- Checked in database (PRIMARY KEY constraint)
- Checked in logic (2 security checks)
- Clear error message to user
```

**Example:**
- User submits TXID abc123 → Processed ✅
- Same user tries abc123 again → "⚠️ ՍԽԱԼ - Կրկնվող գործարք"
- Different user tries abc123 → "🚫 ՍԽԱԼ - Արգելված գործարք"

**Code:** `telegram_bot_improved.py` line 227-257

---

### 5. **Blacklist System** 🚫
**What happens:** Known scammer tries to use bot

**Admin tools:**
```bash
/blacklist_add abc123...def456 Scammer
/blacklist_remove abc123...def456
```

**Protection:**
- Fraudulent TXIDs permanently blocked
- Checked before processing any deposit
- Admin can manage blacklist

**Code:** `telegram_bot_improved.py` line 66-76, 384-448

---

### 6. **Input Validation** ✅
**What happens:** User sends malformed data

**Protection:**
```
TXID validation:
- Must be exactly 64 characters
- Must be hexadecimal (0-9, a-f)
- Normalized (strips whitespace, newlines)

TRC20 address validation:
- Must start with 'T'
- Must be exactly 34 characters
```

**Example:**
- User sends "abc" → ❌ "Սխալ ձևաչափ"
- User sends 64-char hex ✅ Accepted
- User sends TRC20 starting with '1' → ❌ "Սխալ հասցե"

**Code:** `telegram_bot_improved.py` line 226, 278-286

---

## Spam Scenarios & How Bot Handles Them

### Scenario 1: Bot Spammer (Opens 100 Orders)
**Attack:**
```
Spammer: /start /start /start /start ... (100 times)
```

**Protection:**
1. Rate limit: Only 1 request per 30 seconds ✅
2. After 10 swaps: Daily quota exceeded ✅
3. All unpaid orders: Deleted after 24 hours ✅

**Result:** Spammer wastes own time, bot unaffected

---

### Scenario 2: Fake Transaction Spammer
**Attack:**
```
User submits 100 fake TXIDs that don't exist
```

**Protection:**
1. Rate limit: Only 1 per 30 seconds (takes 50 minutes for 100) ✅
2. Daily quota: Maximum 10 per day ✅
3. Fake TXIDs: Stay in NEW status, never confirm ✅
4. Auto cleanup: Deleted after 24 hours ✅

**Result:** Maximum 10 fake orders per day, auto-cleaned

---

### Scenario 3: Never Pays
**Attack:**
```
User submits real TXID but never sends crypto
```

**Protection:**
1. Deposit stays in NEW status (0 confirmations) ✅
2. Worker never processes it (needs confirmations) ✅
3. After 24 hours: Auto-deleted from database ✅

**Result:** No impact on bot, order auto-removed

---

### Scenario 4: Reuse Attack
**Attack:**
```
User tries to use same TXID multiple times
```

**Protection:**
1. First use: Processed normally ✅
2. Second use: "⚠️ ՍԽԱԼ - Կրկնվող գործարք" ❌
3. Database constraint: Prevents insertion ✅

**Result:** Only first use accepted, others blocked

---

### Scenario 5: API Flood Attack
**Attack:**
```
Bot spammer sends 1000 messages per second
```

**Protection:**
1. Telegram rate limits: Telegram blocks the bot attacker ✅
2. Your rate limiting: Even if messages arrive, only processed every 30s ✅
3. ConversationHandler: User must complete flow step-by-step ✅

**Result:** Bot processes at controlled rate

---

## Database Impact of Spam

### With Protection (Current):
```
Day 1: User creates 10 fake orders (daily limit)
Day 2: Orders auto-deleted (24h cleanup)
Database: 0 spam records remaining
```

### Without Protection (Theoretical):
```
Day 1: User creates 1000 fake orders
Day 2: User creates 1000 more
Database: 2000 spam records accumulating forever
```

**Your system:** ✅ Auto-cleans, no manual intervention needed

---

## Admin Monitoring

Check spam activity with `/debug`:
```
📊 Deposit Stats:
• Pending: 5
• Failed (auto-retry): 2

📈 Today's Activity:
• Swaps completed: 8
• Volume: $1,234.56

🔒 Security:
• Blacklisted TXIDs: 3
• Rate limit: 30s
• Daily limit: 10 swaps, $10,000
```

---

## Configuration (Adjust as Needed)

`telegram_bot_improved.py`:
```python
# Line 23: Time between swap requests
RATE_LIMIT_COOLDOWN = 30  # seconds

# Line 27-28: Daily limits
DAILY_SWAP_LIMIT = 10      # swaps per day
DAILY_VOLUME_LIMIT = 10000  # USD per day
```

`app/worker.py`:
```python
# Line 41: Cleanup old deposits
cutoff = datetime.now() - timedelta(hours=24)
# Deletes unconfirmed deposits > 24 hours old
```

---

## Summary: Multi-Layer Protection 🛡️

Your bot has **6 layers** of spam protection:

1. ⏱️ **Rate Limiting** - 30s cooldown
2. 📊 **Daily Quotas** - 10 swaps, $10K per day
3. 🧹 **Auto Cleanup** - Unpaid orders deleted after 24h
4. 🔒 **Duplicate Protection** - Each TXID used once
5. 🚫 **Blacklist** - Block known scammers
6. ✅ **Input Validation** - Reject malformed data

**Result:** Spam attempts are automatically blocked, limited, or cleaned up with zero manual intervention required.
