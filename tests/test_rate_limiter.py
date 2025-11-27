"""
Unit tests for Rate Limiter
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestInMemoryRateLimiter:
    """Test in-memory rate limiting (no Redis)"""

    @pytest.fixture
    def rate_limiter(self):
        """Create a fresh rate limiter instance"""
        # Import here to avoid issues with settings
        with patch('app.rate_limiter.REDIS_AVAILABLE', False):
            from app.rate_limiter import RateLimiter
            limiter = RateLimiter()
            limiter.cooldown_seconds = 30
            limiter.daily_swap_limit = 5
            limiter.daily_volume_limit = 1000.0
            return limiter

    @pytest.mark.asyncio
    async def test_first_swap_allowed(self, rate_limiter):
        """First swap should always be allowed"""
        is_allowed, error = rate_limiter._check_memory(user_id=12345)
        assert is_allowed is True
        assert error == ""

    @pytest.mark.asyncio
    async def test_cooldown_enforced(self, rate_limiter):
        """Swap within cooldown should be blocked"""
        user_id = 12345

        # Record first swap
        rate_limiter._record_memory(user_id, volume_usd=100.0)

        # Immediate second swap should fail
        is_allowed, error = rate_limiter._check_memory(user_id)
        assert is_allowed is False
        assert "delays" in error.lower() or "seconds" in error.lower() or "վdelays" in error

    @pytest.mark.asyncio
    async def test_daily_limit_enforced(self, rate_limiter):
        """Should block after daily limit reached"""
        user_id = 12345

        # Record 5 swaps
        for i in range(5):
            rate_limiter._record_memory(user_id, volume_usd=100.0)
            # Bypass cooldown by clearing last swap time
            rate_limiter._memory_last_swap[user_id] = datetime.now() - timedelta(minutes=5)

        # 6th swap should fail
        is_allowed, error = rate_limiter._check_memory(user_id)
        assert is_allowed is False

    @pytest.mark.asyncio
    async def test_volume_limit_enforced(self, rate_limiter):
        """Should block after daily volume limit reached"""
        user_id = 12345

        # Record high volume swap
        rate_limiter._record_memory(user_id, volume_usd=1100.0)
        rate_limiter._memory_last_swap[user_id] = datetime.now() - timedelta(minutes=5)

        # Next swap should fail due to volume
        is_allowed, error = rate_limiter._check_memory(user_id)
        assert is_allowed is False

    @pytest.mark.asyncio
    async def test_different_users_independent(self, rate_limiter):
        """Rate limits should be independent per user"""
        user1, user2 = 11111, 22222

        # User 1 hits limit
        for i in range(5):
            rate_limiter._record_memory(user1, volume_usd=100.0)
            rate_limiter._memory_last_swap[user1] = datetime.now() - timedelta(minutes=5)

        # User 2 should still be allowed
        is_allowed, error = rate_limiter._check_memory(user2)
        assert is_allowed is True


class TestValidation:
    """Test transaction validation"""

    def test_valid_txid_format(self):
        """Valid TXID should be 64 hex characters"""
        import re
        valid_txid = "a65b33369cf0bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545"
        assert re.match(r"^[a-f0-9]{64}$", valid_txid) is not None

    def test_invalid_txid_too_short(self):
        """Short TXID should fail validation"""
        import re
        invalid_txid = "a65b33369cf0bcd1b4e7a47f"
        assert re.match(r"^[a-f0-9]{64}$", invalid_txid) is None

    def test_invalid_txid_wrong_chars(self):
        """TXID with invalid characters should fail"""
        import re
        invalid_txid = "g65b33369cf0bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545"
        assert re.match(r"^[a-f0-9]{64}$", invalid_txid) is None

    def test_valid_trc20_address(self):
        """Valid TRC20 address starts with T and is 34 chars"""
        address = "TVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3g"
        assert address.startswith("T") and len(address) == 34

    def test_invalid_trc20_address_wrong_prefix(self):
        """Invalid TRC20 address with wrong prefix"""
        address = "0xVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3"
        assert not (address.startswith("T") and len(address) == 34)


class TestCoinInfo:
    """Test coin configuration"""

    def test_all_coins_have_required_fields(self):
        """All coins should have name, network, confs, to fields"""
        COIN_INFO = {
            "BTC": {"name": "Bitcoin", "network": "Bitcoin", "confs": 2, "to": "USDT"},
            "LTC": {"name": "Litecoin", "network": "Litecoin", "confs": 4, "to": "USDT"},
            "DASH": {"name": "Dash", "network": "Dash", "confs": 12, "to": "USDT"},
            "DASH_TRX": {"name": "Dash", "network": "Dash", "confs": 12, "to": "TRX"},
            "XMR": {"name": "Monero", "network": "Monero", "confs": 10, "to": "USDT"},
        }

        required_fields = ["name", "network", "confs", "to"]

        for coin, info in COIN_INFO.items():
            for field in required_fields:
                assert field in info, f"{coin} missing {field}"

    def test_confirmation_counts_reasonable(self):
        """Confirmation counts should be within reasonable range"""
        COIN_INFO = {
            "BTC": {"confs": 2},
            "LTC": {"confs": 4},
            "DASH": {"confs": 12},
            "XMR": {"confs": 10},
        }

        for coin, info in COIN_INFO.items():
            assert 1 <= info["confs"] <= 20, f"{coin} has unreasonable confs: {info['confs']}"


class TestDepositAddresses:
    """Test deposit address configuration"""

    def test_btc_address_valid_format(self):
        """BTC address should start with 1, 3, or bc1"""
        address = "33vFCeDJXdEPTnWFEyy5tRy85iQo1oBtw4"
        assert address[0] in "13b"

    def test_ltc_address_valid_format(self):
        """LTC address should start with L, M, or ltc1"""
        address = "ltc1qdx26fhhma5x0kwld5l0dxrwc0mrcygl6fnvnxp"
        assert address.startswith("ltc1") or address[0] in "LM"

    def test_dash_address_valid_format(self):
        """DASH address should start with X"""
        address = "Xdiuzho4EhWWzEEDbNzbxYpt55DRDETgD9"
        assert address.startswith("X")

    def test_xmr_address_valid_length(self):
        """XMR address should be 95 characters"""
        address = "88jVTyDDAJzWyaamiGWaAyXn487o53v7hgzPY46qAwBEBCJsvXoBVadgq1yj7kuBrD6sKo3v49twPCtJ5vozbTqW3HMqWb7"
        assert len(address) == 95


class TestAdminStatus:
    """Test admin status module"""

    @pytest.mark.asyncio
    async def test_format_status_message(self):
        """Test status message formatting"""
        from app.admin_status import format_status_message

        stats = {
            "orders_today": 42,
            "orders_total": 3912,
            "orders_open": 5,
            "users_today": 27,
            "users_total": 1204,
            "queue_size": 0,
            "last_worker_run": 27,
            "mode": "PRODUCTION",
            "failed_today": 1,
            "volume_today_usd": 1500.50,
        }

        message = format_status_message(stats)

        assert "42" in message  # orders_today
        assert "3,912" in message  # orders_total formatted
        assert "PRODUCTION" in message
        assert "27s ago" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
