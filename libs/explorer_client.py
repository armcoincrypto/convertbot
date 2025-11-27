"""Blockchain Explorer Client - WITH FAKE TX DETECTION"""
import asyncio
import aiohttp
from typing import Optional
from app.logger import setup_logger
from app.models import CoinType

logger = setup_logger(__name__)


class ExplorerClient:
    """Multi-provider blockchain explorer with fake transaction detection"""
    
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=10)
    
    async def _try_providers(self, providers: list, *args) -> Optional[int]:
        """Try multiple providers. Returns -1 for non-existent tx."""
        for name, func in providers:
            try:
                result = await func(*args)
                if result is not None and result >= 0:
                    logger.info(f"  ✅ {name} returned: {result}")
                    return result
                elif result == -1:
                    logger.warning(f"  ❌ {name}: Transaction not found")
                    return -1
            except Exception as e:
                logger.debug(f"  ⚠️  {name} failed: {e}")
                continue
        return -1  # All providers failed = transaction doesn't exist
    
    async def get_confirmations(self, coin: CoinType, txid: str) -> Optional[int]:
        """
        Get transaction confirmations.
        Returns:
          - N (>= 0): Transaction exists with N confirmations
          - -1: Transaction does NOT exist (fake/invalid txid)
          - None: API error (retry later)
        """
        logger.info(f"🔍 Looking up {coin.value} transaction: {txid[:16]}...")
        
        if coin == CoinType.BTC:
            return await self._get_btc_confirmations(txid)


        elif coin == CoinType.LTC:
            return await self._get_ltc_confirmations(txid)
        elif coin == CoinType.DASH:
            return await self._get_dash_confirmations(txid)
        return None
    
    async def _get_btc_confirmations(self, txid: str) -> Optional[int]:
        providers = [
            ("Blockstream", self._blockstream_btc),
            ("BlockCypher", self._blockcypher_btc),
        ]
        return await self._try_providers(providers, txid)
    
    async def _get_ltc_confirmations(self, txid: str) -> Optional[int]:
        """Get LTC confirmations using Blockchair + SoChain"""
        # Try Blockchair first
        try:
            url = f"https://api.blockchair.com/litecoin/dashboards/transaction/{txid}"
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Handle case where 'data' might be a list or None
                        data_section = data.get('data', {})
                        if not isinstance(data_section, dict):
                            logger.warning(f"   ⚠️ Blockchair returned unexpected format")
                            return None
                        tx_data = data_section.get(txid, {})
                        if tx_data and isinstance(tx_data, dict):
                            block_id = tx_data.get('transaction', {}).get('block_id')
                            if block_id and block_id > 0:
                                current_height = data.get('context', {}).get('state', 0)
                                confs = current_height - block_id + 1
                                logger.info(f"   ✅ Blockchair returned: {confs}")
                                return confs
                            else:
                                logger.info(f"   ⚠️ Unconfirmed (block_id={block_id})")
                                return 0
                    elif response.status == 404:
                        return -1
        except Exception as e:
            logger.warning(f"Blockchair confs failed: {e}")
        
        # Fallback to SoChain
        try:
            url = f"https://sochain.com/api/v2/get_tx/LTC/{txid}"
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 'success':
                            confs = data['data'].get('confirmations', 0)
                            logger.info(f"   ✅ SoChain returned: {confs}")
                            return int(confs)
        except Exception as e:
            logger.warning(f"SoChain confs failed: {e}")
        
        return None

    async def _get_dash_confirmations(self, txid: str) -> Optional[int]:
        providers = [
            ("BlockCypher", self._blockcypher_dash),
            ("CryptoID", self._cryptoid_dash)
        ]
        return await self._try_providers(providers, txid)
    
    async def _blockcypher_btc(self, txid: str) -> Optional[int]:
        url = f"https://api.blockcypher.com/v1/btc/main/txs/{txid}"
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("confirmations", 0)
                elif resp.status == 404:
                    return -1  # Transaction not found
        return None
    
    async def _blockstream_btc(self, txid: str) -> Optional[int]:
        url = f"https://blockstream.info/api/tx/{txid}"
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("status", {}).get("confirmed"):
                        block_height = data["status"]["block_height"]
                        async with session.get("https://blockstream.info/api/blocks/tip/height") as tip_resp:
                            if tip_resp.status == 200:
                                current_height = int(await tip_resp.text())
                                return current_height - block_height + 1
                    return 0  # Unconfirmed but exists
                elif resp.status == 404:
                    return -1  # Transaction not found
        return None
    
    async def _blockcypher_ltc(self, txid: str) -> Optional[int]:
        url = f"https://api.blockcypher.com/v1/ltc/main/txs/{txid}"
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("confirmations", 0)
                elif resp.status == 404:
                    return -1
        return None
    
    async def _blockcypher_dash(self, txid: str) -> Optional[int]:
        url = f"https://api.blockcypher.com/v1/dash/main/txs/{txid}"
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("confirmations", 0)
                elif resp.status == 404:
                    return -1
        return None
    
    async def _cryptoid_dash(self, txid: str) -> Optional[int]:
        url = f"https://chainz.cryptoid.info/dash/api.dws?q=txinfo&t={txid}"
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "confirmations" in data:
                        return data.get("confirmations", 0)
                    else:
                        return -1  # Transaction not found
        return None
    
    async def get_transaction_amount(self, coin: CoinType, txid: str, address: str) -> Optional[float]:
        """Get transaction amount for a specific address"""
        logger.info(f"💰 Getting amount for {coin.value} tx {txid[:16]}...")
        
        if coin == CoinType.BTC:
            return await self._get_btc_amount(txid, address)
        elif coin == CoinType.LTC:
            return await self._get_ltc_amount(txid, address)
        elif coin == CoinType.DASH:
            return await self._get_dash_amount(txid, address)
        return None
    
    async def _get_btc_amount(self, txid: str, address: str) -> Optional[float]:
        # Blockstream
        try:
            url = f"https://blockstream.info/api/tx/{txid}"
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for vout in data.get('vout', []):
                            if vout.get('scriptpubkey_address') == address:
                                return vout['value'] / 100000000
        except:
            pass
        return None
    
    async def _get_ltc_amount(self, txid: str, address: str) -> Optional[float]:
        """Get LTC transaction amount using Blockchair"""
        # Try Blockchair first (best bech32 support)
        try:
            url = f"https://api.blockchair.com/litecoin/dashboards/transaction/{txid}"
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Handle case where 'data' might be a list or None
                        data_section = data.get('data', {})
                        if not isinstance(data_section, dict):
                            logger.warning(f"   ⚠️ Blockchair returned unexpected format for amount")
                            data_section = {}
                        tx_data = data_section.get(txid, {})

                        if tx_data and isinstance(tx_data, dict):
                            outputs = tx_data.get('outputs', [])
                            for output in outputs:
                                if output.get('recipient') == address:
                                    amount = output.get('value', 0) / 100000000
                                    logger.info(f"   ✅ Blockchair returned amount: {amount}")
                                    return amount
            logger.warning("Blockchair: Transaction found but no matching output")
        except Exception as e:
            logger.warning(f"Blockchair failed for LTC: {e}")
        
        # Fallback to SoChain
        try:
            url = f"https://sochain.com/api/v2/get_tx/LTC/{txid}"
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 'success':
                            outputs = data.get('data', {}).get('outputs', [])
                            for output in outputs:
                                if output.get('address') == address:
                                    amount = float(output.get('value', 0))
                                    logger.info(f"   ✅ SoChain returned amount: {amount}")
                                    return amount
            logger.warning("SoChain: Transaction found but no matching output")
        except Exception as e:
            logger.warning(f"SoChain failed for LTC: {e}")
        
        logger.error("All LTC explorers failed")
        return None

    async def _get_dash_amount(self, txid: str, address: str) -> Optional[float]:
        try:
            url = f"https://api.blockcypher.com/v1/dash/main/txs/{txid}"
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for output in data.get('outputs', []):
                            if address in output.get('addresses', []):
                                return output['value'] / 100000000
        except:
            pass
        return None

# Create singleton instance for backward compatibility
explorer_client = ExplorerClient()
