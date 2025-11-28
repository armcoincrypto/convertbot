"""MEXC Exchange Client - WORKING VERSION"""
import time
import hmac
import hashlib
import requests
import logging
from urllib.parse import quote
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

# Default timeout for API calls (seconds)
API_TIMEOUT = 10


class MEXCClient:
    """MEXC Exchange API Client"""

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.mexc.com"
        self.timeout = API_TIMEOUT


    def _quantize_amount(self, coin: str, amount: float) -> float:
        """Round DOWN to valid step size for MEXC"""
        # MEXC step sizes (from exchange info)
        step_sizes = {
            'BTC': 0.00001,
            'LTC': 0.01,
            'DASH': 0.01,
            'XMR': 0.01,
            'USDT': 0.01,
            'USDC': 0.01
        }
        step = step_sizes.get(coin, 0.01)
        # Round DOWN to nearest step
        return float(int(amount / step) * step)

    def _sign(self, params_string: str) -> str:
        """Generate signature for authenticated requests"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            params_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def test_connection(self) -> bool:
        """Test MEXC API connection"""
        try:
            response = requests.get(f"{self.base_url}/api/v3/ping", timeout=self.timeout)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_account_balance(self) -> Dict:
        """Get account balances"""
        try:
            timestamp = str(int(time.time() * 1000))
            params = f"recvWindow=5000&timestamp={timestamp}"
            signature = self._sign(params)

            url = f"{self.base_url}/api/v3/account?{params}&signature={signature}"
            headers = {"X-MEXC-APIKEY": self.api_key}

            response = requests.get(url, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                balances = {}
                for balance in data.get('balances', []):
                    asset = balance['asset']
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    if free > 0 or locked > 0:
                        balances[asset] = {'free': free, 'locked': locked}
                return balances
            else:
                logger.error(f"Failed to get balance: {response.status_code} {response.text}")
                return {}
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return {}


    def get_deposit_history(self, coin: str = None, limit: int = 100) -> list:
        """Get deposit history from MEXC"""
        try:
            timestamp = str(int(time.time() * 1000))
            params_dict = {
                "recvWindow": "5000",
                "timestamp": timestamp
            }
            if coin:
                params_dict["coin"] = coin
            if limit:
                params_dict["limit"] = str(limit)
            
            params = "&".join([f"{k}={v}" for k, v in params_dict.items()])
            signature = self._sign(params)
            
            url = f"{self.base_url}/api/v3/capital/deposit/hisrec?{params}&signature={signature}"
            headers = {"X-MEXC-APIKEY": self.api_key}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                deposits = response.json()
                # Filter deposits: 1=pending, 5=completed, 6=credited, 9=under review
                return [d for d in deposits if d.get("status") in [1, 5, 6, 9]]
            else:
                logger.error(f"Deposit history error: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Get deposit history failed: {e}")
            return []

    def get_ticker_price(self, symbol: str) -> Optional[float]:
        """Get current ticker price"""
        try:
            url = f"{self.base_url}/api/v3/ticker/price?symbol={symbol}"
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return float(response.json()['price'])
            return None
        except:
            return None

    def check_coin_balance(self, coin: str, required_amount: float) -> Tuple[bool, float]:
        """Check if we have enough balance of a coin to sell.
        Returns (has_enough, available_balance)"""
        coin_str = coin.value if hasattr(coin, 'value') else str(coin)
        balances = self.get_account_balance()
        available = balances.get(coin_str, {}).get('free', 0)
        return available >= required_amount, available

    def verify_deposit_on_mexc(self, coin: str, txid: str) -> Tuple[bool, Optional[float]]:
        """Check if a specific deposit has been credited on MEXC.
        Returns (is_credited, amount)"""
        coin_str = coin.value if hasattr(coin, 'value') else str(coin)
        try:
            deposits = self.get_deposit_history(coin=coin_str, limit=100)
            for d in deposits:
                mexc_txid = d.get('txId', '')
                # MEXC adds output index suffix like ":0" or ":1" for UTXO coins
                # Match if our txid is contained in MEXC txid or vice versa
                if txid in mexc_txid or mexc_txid.startswith(txid):
                    status = d.get('status')
                    amount = float(d.get('amount', 0))
                    # Status 5 = completed/credited, 6 = credited
                    if status in [5, 6]:
                        return True, amount
                    elif status == 9:
                        logger.warning(f"   ⚠️ Deposit UNDER REVIEW (status=9) - MEXC risk control")
                        logger.warning(f"   💡 Check MEXC app/website for verification requirements")
                        return False, amount
                    elif status == 1:
                        logger.info(f"   ⏳ Deposit pending confirmation (status=1)")
                        return False, amount
                    else:
                        logger.info(f"   ⏳ Deposit found but status={status} (not credited yet)")
                        return False, amount
            return False, None
        except Exception as e:
            logger.error(f"❌ Error checking deposit: {e}")
            return False, None

    def _check_response_error(self, data: Dict) -> Tuple[bool, Optional[str]]:
        """Check if MEXC response contains an error code.
        Returns (is_error, error_message)"""
        # MEXC returns error codes in JSON even with HTTP 200
        error_code = data.get('code')
        if error_code and error_code != 0:
            error_msg = data.get('msg', 'Unknown error')
            return True, f"MEXC Error {error_code}: {error_msg}"
        return False, None

    def sell_crypto_to_usdt(self, coin: str, amount: float) -> Tuple[bool, Dict]:
        """Sell crypto for USDT (with BTC special handling)"""
        coin_str = coin.value if hasattr(coin, 'value') else str(coin)

        # CRITICAL: Check if we have enough balance BEFORE attempting to sell
        has_balance, available = self.check_coin_balance(coin_str, amount)
        if not has_balance:
            error = f"Insufficient {coin_str} balance: have {available}, need {amount}"
            logger.error(f"❌ {error}")
            return False, {'error': error, 'error_code': 'INSUFFICIENT_BALANCE', 'available': available}

        logger.info(f"✅ Balance check passed: {available} {coin_str} available (need {amount})")

        # Special handling for BTC (not allowed on MEXC API)
        if coin_str == 'BTC':
            logger.info(f"🔄 BTC not allowed on API, converting BTC → USDC → USDT")

            # Step 1: Sell BTC for USDC
            success1, result1 = self._trade_pair('BTCUSDC', amount, 'SELL')
            if not success1:
                return False, result1

            usdc_amount = result1.get('received', 0)
            logger.info(f"   ✅ Step 1: {amount} BTC → {usdc_amount:.2f} USDC")

            # Step 2: Sell USDC for USDT
            time.sleep(1)
            success2, result2 = self._trade_pair('USDCUSDT', usdc_amount, 'SELL')
            if not success2:
                return False, result2

            usdt_amount = result2.get('received', 0)
            logger.info(f"   ✅ Step 2: {usdc_amount:.2f} USDC → {usdt_amount:.2f} USDT")

            return True, {
                'order_id': f"{result1.get('order_id')}+{result2.get('order_id')}",
                'usdt_received': usdt_amount,
                'avg_price': usdt_amount / amount if amount > 0 else 0,
                'two_step': True
            }

        symbol = f"{coin_str}USDT"

        try:
            precision = {'BTC': 6, 'LTC': 4, 'DASH': 2, 'XMR': 3, 'TRX': 2}
            decimals = precision.get(coin_str, 6)

            # Quantize amount first, then apply 99% (only once!)
            amount = self._quantize_amount(coin_str, amount * 0.99)

            balances_before = self.get_account_balance()
            usdt_before = balances_before.get('USDT', {}).get('free', 0)

            timestamp = str(int(time.time() * 1000))
            params = f"quantity={amount}&recvWindow=5000&side=SELL&symbol={symbol}&timestamp={timestamp}&type=MARKET"
            signature = self._sign(params)

            url = f"{self.base_url}/api/v3/order?{params}&signature={signature}"
            headers = {"X-MEXC-APIKEY": self.api_key}

            logger.info(f"📤 Placing SELL order: {amount} {coin_str} → {symbol}")
            response = requests.post(url, headers=headers)

            if response.status_code == 200:
                data = response.json()

                # CRITICAL: Check for error codes in JSON response
                is_error, error_msg = self._check_response_error(data)
                if is_error:
                    logger.error(f"❌ Trade failed: {error_msg}")
                    return False, {'error': error_msg}

                order_id = data.get('orderId', 'N/A')

                time.sleep(2)

                balances_after = self.get_account_balance()
                usdt_after = balances_after.get('USDT', {}).get('free', 0)
                usdt_received = usdt_after - usdt_before

                logger.info(f"✅ Sold {amount} {coin_str} → {usdt_received:.2f} USDT")

                return True, {
                    'order_id': order_id,
                    'usdt_received': usdt_received,
                    'avg_price': usdt_received / amount if amount > 0 else 0
                }
            else:
                error = f"{response.status_code}: {response.text}"
                logger.error(f"❌ Trade failed: {error}")
                return False, {'error': error}

        except Exception as e:
            error = str(e)
            logger.error(f"❌ Exception: {error}")
            return False, {'error': error}

    def withdraw_usdt_trc20(self, address: str, amount: float) -> Tuple[bool, Dict]:
        """Withdraw USDT to TRC20 address"""
        try:
            amount = round(amount, 2)
            
            timestamp = str(int(time.time() * 1000))
            network = quote("Tron(TRC20)")
            params = f"address={address}&amount={amount}&coin=USDT&network={network}&recvWindow=5000&timestamp={timestamp}"
            signature = self._sign(params)
            
            url = f"{self.base_url}/api/v3/capital/withdraw/apply?{params}&signature={signature}"
            headers = {"X-MEXC-APIKEY": self.api_key}
            
            logger.info(f"📤 Withdrawing {amount} USDT to {address[:10]}...")
            response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                withdraw_id = data.get('id', 'N/A')
                
                logger.info(f"✅ Withdrawal submitted: ID={withdraw_id}")
                
                return True, {
                    'withdraw_id': withdraw_id,
                    'status': 'submitted',
                    'amount': amount,
                    'fee': 1.0
                }
            else:
                error = f"{response.status_code}: {response.text}"
                logger.error(f"❌ Withdrawal failed: {error}")
                return False, {'error': error}
                
        except Exception as e:
            error = str(e)
            logger.error(f"❌ Exception: {error}")
            return False, {'error': error}

    def buy_crypto_with_usdt(self, coin: str, usdt_amount: float) -> Tuple[bool, Dict]:
        """Buy crypto with USDT (market order)"""
        coin_str = coin if isinstance(coin, str) else coin.value if hasattr(coin, 'value') else str(coin)
        symbol = f"{coin_str}USDT"
        
        try:
            price = self.get_ticker_price(symbol)
            if not price:
                return False, {'error': 'Could not get price'}
            
            precision = {'TRX': 2, 'BTC': 6, 'LTC': 4, 'DASH': 2}
            decimals = precision.get(coin_str, 2)
            amount = round(usdt_amount / price, decimals)
            
            timestamp = str(int(time.time() * 1000))
            params = f"quantity={amount}&recvWindow=5000&side=BUY&symbol={symbol}&timestamp={timestamp}&type=MARKET"
            signature = self._sign(params)
            
            url = f"{self.base_url}/api/v3/order?{params}&signature={signature}"
            headers = {"X-MEXC-APIKEY": self.api_key}
            
            logger.info(f"📤 Placing BUY order: {amount} {coin_str} → {symbol}")
            response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Bought {amount} {coin_str}")
                return True, {'order_id': data.get('orderId'), 'amount': amount}
            else:
                error = f"{response.status_code}: {response.text}"
                logger.error(f"❌ Buy failed: {error}")
                return False, {'error': error}
                
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            return False, {'error': str(e)}

    def withdraw_trx(self, address: str, amount: float) -> Tuple[bool, Dict]:
        """Withdraw TRX to TRC20 address"""
        try:
            amount = round(amount, 2)
            
            timestamp = str(int(time.time() * 1000))
            network = quote("Tron(TRC20)")
            params = f"address={address}&amount={amount}&coin=TRX&network={network}&recvWindow=5000&timestamp={timestamp}"
            signature = self._sign(params)
            
            url = f"{self.base_url}/api/v3/capital/withdraw/apply?{params}&signature={signature}"
            headers = {"X-MEXC-APIKEY": self.api_key}
            
            logger.info(f"📤 Withdrawing {amount} TRX to {address[:10]}...")
            response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                withdraw_id = data.get('id', 'N/A')
                logger.info(f"✅ TRX withdrawal: ID={withdraw_id}")
                return True, {'withdraw_id': withdraw_id}
            else:
                error = f"{response.status_code}: {response.text}"
                logger.error(f"❌ Withdrawal failed: {error}")
                return False, {'error': error}
                
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            return False, {'error': str(e)}

    def _trade_pair(self, symbol: str, amount: float, side: str) -> Tuple[bool, Dict]:
        """Generic trading pair method"""
        try:
            # Use proper precision for each pair (from MEXC API rules)
            precision = {
                'BTCUSDC': 6,  # MEXC baseSizePrecision: 0.000001
                'USDCUSDT': 2  # MEXC quotePrecision: 2
            }
            decimals = precision.get(symbol, 6)
            amount = round(amount, decimals)

            balances_before = self.get_account_balance()

            timestamp = str(int(time.time() * 1000))
            params = f"quantity={amount}&recvWindow=5000&side={side}&symbol={symbol}&timestamp={timestamp}&type=MARKET"
            signature = self._sign(params)

            url = f"{self.base_url}/api/v3/order?{params}&signature={signature}"
            headers = {"X-MEXC-APIKEY": self.api_key}

            response = requests.post(url, headers=headers)

            if response.status_code == 200:
                data = response.json()

                # CRITICAL: Check for error codes in JSON response
                is_error, error_msg = self._check_response_error(data)
                if is_error:
                    logger.error(f"❌ Trade pair failed: {error_msg}")
                    return False, {'error': error_msg}

                order_id = data.get('orderId', 'N/A')

                time.sleep(2)

                balances_after = self.get_account_balance()

                # Figure out what we received
                received = 0
                if side == 'SELL':
                    # Selling first coin, receiving second
                    # Properly parse the quote asset from known pairs
                    if "USDT" in symbol:
                        quote = "USDT"
                    elif "USDC" in symbol:
                        quote = "USDC"
                    else:
                        quote = "USDT"  # fallback

                    before_balance = balances_before.get(quote, {}).get("free", 0)
                    after_balance = balances_after.get(quote, {}).get("free", 0)
                    received = after_balance - before_balance

                    logger.info(f"   💰 Balance change: {quote} {before_balance:.8f} → {after_balance:.8f} (received: {received:.8f})")

                return True, {
                    'order_id': order_id,
                    'received': received
                }
            else:
                error = f"{response.status_code}: {response.text}"
                return False, {'error': error}

        except Exception as e:
            return False, {'error': str(e)}
