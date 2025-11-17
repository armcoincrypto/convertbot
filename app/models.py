from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional

class DepositStatus(str, Enum):
    NEW = "NEW"
    CONFIRMING = "CONFIRMING"
    CONFIRMED = "CONFIRMED"
    SOLD = "SOLD"
    WITHDRAWN = "WITHDRAWN"
    FAILED = "FAILED"
    TRADE_FAILED = "TRADE_FAILED"
    WITHDRAWAL_FAILED = "WITHDRAWAL_FAILED"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    AMOUNT_TOO_SMALL = "AMOUNT_TOO_SMALL"

class CoinType(str, Enum):
    BTC = "BTC"
    LTC = "LTC"
    DASH = "DASH"
    XMR = "XMR"
    USDT = "USDT"
    TRX = "TRX"

@dataclass
class Deposit:
    txid: str
    coin: CoinType
    user_id: int
    status: DepositStatus = DepositStatus.NEW
    confs: int = 0
    required_confs: int = 0
    target_address: Optional[str] = None
    amount: Optional[float] = None
    onchain_amount: Optional[Decimal] = None
    usdt_amount: Optional[float] = None
    final_usdt: Optional[float] = None
    output_coin: Optional[str] = 'USDT'
    deposit_address: Optional[str] = None
    reference_code: Optional[str] = None


@dataclass
class User:
    user_id: int
    usdt_trc20_address: str
