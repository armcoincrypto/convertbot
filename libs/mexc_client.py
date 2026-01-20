"""MEXC Exchange Client - WORKING VERSION"""
import time
import hmac
import hashlib
import requests
from urllib.parse import quote
from typing import Dict, Tuple, Optional


class MEXCClient:
    """MEXC Exchange API Client"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.mexc.com"


    def _quantize_amount(self, coin: str, amount: float) -> str:
        """Round DOWN to valid step size for MEXC and return as string with correct decimals"""
        # MEXC step sizes and decimal places (from exchange info)
        # Format: (step_size, decimal_places)
        coin_precision = {
            'BTC': (0.00001, 5),
            'LTC': (0.01, 2),
            'DASH': (0.01, 2),
            'XMR': (0.001, 3),
            'USDT': (0.01, 2),
            'USDC': (0.01, 2),
            'TRX': (0.01, 2)
        }
        step, decimals = coin_precision.get(coin, (0.01, 2))
        # Round DOWN to nearest step
        quantized = float(int(amount / step) * step)
        # Return as string with exact decimal places (no scientific notation)
        return f"{quantized:.{decimals}f}"

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
            response = requests.get(f"{self.base_url}/api/v3/ping", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    def get_account_balance(self) -> Dict:
        """Get account balances"""
        try:
            timestamp = str(int(time.time() * 1000))
            params = f"recvWindow=5000&timestamp={timestamp}"
            signature = self._sign(params)
            
            url = f"{self.base_url}/api/v3/account?{params}&signature={signature}"
            headers = {"X-MEXC-APIKEY": self.api_key}
            
            response = requests.get(url, headers=headers)
            
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
                print(f"Failed to get balance: {response.status_code} {response.text}")
                return {}
        except Exception as e:
            print(f"Error getting balance: {e}")
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
                # Filter successful deposits only
                return [d for d in deposits if d.get("status") in [1, 5, 6]]  # 5=completed, 1=pending, 6=credited
            else:
                print(f"Deposit history error: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"Get deposit history failed: {e}")
            return []

    def get_ticker_price(self, symbol: str) -> Optional[float]:
        """Get current ticker price"""
        try:
            url = f"{self.base_url}/api/v3/ticker/price?symbol={symbol}"
            response = requests.get(url)
            if response.status_code == 200:
                return float(response.json()['price'])
            return None
        except:
            return None

    def sell_crypto_to_usdt(self, coin: str, amount: float) -> Tuple[bool, Dict]:
        """Sell crypto for USDT (with BTC special handling)"""
        coin_str = coin.value if hasattr(coin, 'value') else str(coin)
        
        # Special handling for BTC (not allowed on MEXC API)
        if coin_str == 'BTC':
            print(f"🔄 BTC not allowed on API, converting BTC → USDC → USDT")
            
            # Step 1: Sell BTC for USDC
            success1, result1 = self._trade_pair('BTCUSDC', amount, 'SELL')
            if not success1:
                return False, result1
            
            usdc_amount = result1.get('received', 0)
            print(f"   ✅ Step 1: {amount} BTC → {usdc_amount:.2f} USDC")
            
            # Step 2: Sell USDC for USDT
            time.sleep(1)
            success2, result2 = self._trade_pair('USDCUSDT', usdc_amount, 'SELL')
            if not success2:
                return False, result2
            
            usdt_amount = result2.get('received', 0)
            print(f"   ✅ Step 2: {usdc_amount:.2f} USDC → {usdt_amount:.2f} USDT")
            
            return True, {
                'order_id': f"{result1.get('order_id')}+{result2.get('order_id')}",
                'usdt_received': usdt_amount,
                'avg_price': usdt_amount / amount if amount > 0 else 0,
                'two_step': True
            }
        
        symbol = f"{coin_str}USDT"

        try:
            # Quantize amount FIRST (returns string with correct decimals)
            qty_str = self._quantize_amount(coin_str, amount)
            qty_float = float(qty_str)

            if qty_float <= 0:
                return False, {'error': f'Amount too small after quantization: {amount} -> {qty_str}'}

            balances_before = self.get_account_balance()
            usdt_before = balances_before.get('USDT', {}).get('free', 0)

            timestamp = str(int(time.time() * 1000))
            # Use quantized string in params to ensure correct format
            params = f"quantity={qty_str}&recvWindow=5000&side=SELL&symbol={symbol}&timestamp={timestamp}&type=MARKET"
            signature = self._sign(params)

            url = f"{self.base_url}/api/v3/order?{params}&signature={signature}"
            headers = {"X-MEXC-APIKEY": self.api_key}

            print(f"📤 Placing SELL order: {qty_str} {coin_str} → {symbol}")
            response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                order_id = data.get('orderId', 'N/A')

                time.sleep(2)

                balances_after = self.get_account_balance()
                usdt_after = balances_after.get('USDT', {}).get('free', 0)
                usdt_received = usdt_after - usdt_before

                print(f"✅ Sold {qty_str} {coin_str} → {usdt_received:.2f} USDT")

                return True, {
                    'order_id': order_id,
                    'usdt_received': usdt_received,
                    'avg_price': usdt_received / qty_float if qty_float > 0 else 0
                }
            else:
                error = f"{response.status_code}: {response.text}"
                print(f"❌ Trade failed: {error}")
                return False, {'error': error}

        except Exception as e:
            error = str(e)
            print(f"❌ Exception: {error}")
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
            
            print(f"📤 Withdrawing {amount} USDT to {address[:10]}...")
            response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                withdraw_id = data.get('id', 'N/A')
                
                print(f"✅ Withdrawal submitted: ID={withdraw_id}")
                
                return True, {
                    'withdraw_id': withdraw_id,
                    'status': 'submitted',
                    'amount': amount,
                    'fee': 1.0
                }
            else:
                error = f"{response.status_code}: {response.text}"
                print(f"❌ Withdrawal failed: {error}")
                return False, {'error': error}
                
        except Exception as e:
            error = str(e)
            print(f"❌ Exception: {error}")
            return False, {'error': error}

    def buy_crypto_with_usdt(self, coin: str, usdt_amount: float) -> Tuple[bool, Dict]:
        """Buy crypto with USDT (market order)"""
        coin_str = coin if isinstance(coin, str) else coin.value if hasattr(coin, 'value') else str(coin)
        symbol = f"{coin_str}USDT"

        try:
            price = self.get_ticker_price(symbol)
            if not price:
                return False, {'error': 'Could not get price'}

            # Calculate amount and quantize properly
            raw_amount = usdt_amount / price
            qty_str = self._quantize_amount(coin_str, raw_amount)
            qty_float = float(qty_str)

            if qty_float <= 0:
                return False, {'error': f'Amount too small: {raw_amount} -> {qty_str}'}

            timestamp = str(int(time.time() * 1000))
            params = f"quantity={qty_str}&recvWindow=5000&side=BUY&symbol={symbol}&timestamp={timestamp}&type=MARKET"
            signature = self._sign(params)

            url = f"{self.base_url}/api/v3/order?{params}&signature={signature}"
            headers = {"X-MEXC-APIKEY": self.api_key}

            print(f"📤 Placing BUY order: {qty_str} {coin_str} → {symbol}")
            response = requests.post(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Bought {qty_str} {coin_str}")
                return True, {'order_id': data.get('orderId'), 'amount': qty_float}
            else:
                error = f"{response.status_code}: {response.text}"
                print(f"❌ Buy failed: {error}")
                return False, {'error': error}

        except Exception as e:
            print(f"❌ Exception: {e}")
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
            
            print(f"📤 Withdrawing {amount} TRX to {address[:10]}...")
            response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                withdraw_id = data.get('id', 'N/A')
                print(f"✅ TRX withdrawal: ID={withdraw_id}")
                return True, {'withdraw_id': withdraw_id}
            else:
                error = f"{response.status_code}: {response.text}"
                print(f"❌ Withdrawal failed: {error}")
                return False, {'error': error}
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False, {'error': str(e)}

    def _trade_pair(self, symbol: str, amount: float, side: str) -> Tuple[bool, Dict]:
        """Generic trading pair method"""
        try:
            # Use proper precision for each pair (from MEXC API rules)
            # Maps symbol to (step_size, decimals)
            pair_precision = {
                'BTCUSDC': (0.00001, 5),
                'USDCUSDT': (0.01, 2)
            }
            step, decimals = pair_precision.get(symbol, (0.01, 2))
            # Round DOWN to step size
            quantized = float(int(amount / step) * step)
            qty_str = f"{quantized:.{decimals}f}"

            if quantized <= 0:
                return False, {'error': f'Amount too small: {amount} -> {qty_str}'}

            balances_before = self.get_account_balance()

            timestamp = str(int(time.time() * 1000))
            params = f"quantity={qty_str}&recvWindow=5000&side={side}&symbol={symbol}&timestamp={timestamp}&type=MARKET"
            signature = self._sign(params)
            
            url = f"{self.base_url}/api/v3/order?{params}&signature={signature}"
            headers = {"X-MEXC-APIKEY": self.api_key}
            
            response = requests.post(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
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
                    
                    print(f"   💰 Balance change: {quote} {before_balance:.8f} → {after_balance:.8f} (received: {received:.8f})")
                
                return True, {
                    'order_id': order_id,
                    'received': received
                }
            else:
                error = f"{response.status_code}: {response.text}"
                return False, {'error': error}
                
        except Exception as e:
            return False, {'error': str(e)}
