"""MEXC Deposit Address Management - Fixed Response Handling."""
import time
import hmac
import hashlib
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode
import aiohttp
from app.logger import setup_logger

logger = setup_logger(__name__)

class MexcDepositManager:
    def __init__(self, mexc_client):
        self.mexc = mexc_client
        self._network_cache = {}
        self._cache_timestamp = 0
    
    def _sign(self, params: Dict[str, Any]) -> str:
        query_string = urlencode(sorted(params.items()))
        return hmac.new(
            self.mexc.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def get_network_config(self) -> List[Dict[str, Any]]:
        now = time.time()
        if self._network_cache and (now - self._cache_timestamp) < 600:
            return self._network_cache
        
        timestamp = int(time.time() * 1000)
        params = {"recvWindow": 60000, "timestamp": timestamp}
        signature = self._sign(params)
        query_string = f"recvWindow=60000&timestamp={timestamp}&signature={signature}"
        headers = {"X-MEXC-APIKEY": self.mexc.api_key}
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.mexc.BASE_URL}/api/v3/capital/config/getall?{query_string}"
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    self._network_cache = result
                    self._cache_timestamp = now
                    return result
                return []
    
    async def get_deposit_address(self, coin: str, network: Optional[str] = None) -> Dict[str, Any]:
        config = await self.get_network_config()
        
        if not config:
            return {"error": "Failed to get network config"}
        
        coin_config = None
        for c in config:
            if c.get("coin", "").upper() == coin.upper():
                coin_config = c
                break
        
        if not coin_config:
            return {"error": f"Coin {coin} not found"}
        
        networks = coin_config.get("networkList", [])
        if not networks:
            return {"error": "No networks available"}
        
        net_config = networks[0]
        if network:
            for n in networks:
                net_name = n.get("network", "").upper()
                if network.upper() in net_name or net_name == network.upper():
                    net_config = n
                    break
        
        network_name = net_config.get("network")
        
        if not net_config.get("depositEnable"):
            return {"error": f"Deposits disabled for {coin} on {network_name}"}
        
        timestamp = int(time.time() * 1000)
        params = {
            "coin": coin.upper(),
            "network": network_name,
            "recvWindow": 60000,
            "timestamp": timestamp
        }
        signature = self._sign(params)
        params["signature"] = signature
        query_string = urlencode(params)
        headers = {"X-MEXC-APIKEY": self.mexc.api_key}
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.mexc.BASE_URL}/api/v3/capital/deposit/address?{query_string}"
            async with session.get(url, headers=headers) as resp:
                result = await resp.json()
                
                # Handle both dict and list responses
                if isinstance(result, list):
                    if len(result) > 0:
                        result = result[0]
                    else:
                        return {"error": "No address returned"}
                
                if isinstance(result, dict):
                    if result.get("address"):
                        return {
                            "coin": coin.upper(),
                            "network": network_name,
                            "address": result.get("address"),
                            "memo": result.get("tag") or result.get("memo"),
                            "minConfirmations": net_config.get("minConfirm", 2),
                        }
                    elif result.get("code"):
                        return {"error": f"Error {result.get('code')}: {result.get('msg')}"}
                
                return {"error": f"Unexpected response: {result}"}
