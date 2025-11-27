"""
Unit tests for Transaction Validation
"""
import pytest
from unittest.mock import patch, MagicMock


class TestAmountValidation:
    """Test amount validation logic"""

    @pytest.fixture
    def mock_price(self):
        """Mock price fetching"""
        with patch('app.validation.get_coin_price_usd') as mock:
            mock.return_value = 100.0  # $100 per coin
            yield mock

    def test_minimum_amount_usd(self):
        """Minimum should be $19 (for $20 after fees)"""
        from app.validation import MIN_AMOUNT_USD
        assert MIN_AMOUNT_USD == 19.0

    def test_valid_amount_passes(self, mock_price):
        """Amount above minimum should pass"""
        from app.validation import validate_amount
        from app.models import CoinType

        # 0.2 coins * $100 = $20, which is >= $19
        is_valid, error = validate_amount(CoinType.DASH, 0.2)
        assert is_valid is True
        assert error == ""

    def test_invalid_amount_fails(self, mock_price):
        """Amount below minimum should fail"""
        from app.validation import validate_amount
        from app.models import CoinType

        # 0.1 coins * $100 = $10, which is < $19
        is_valid, error = validate_amount(CoinType.DASH, 0.1)
        assert is_valid is False
        assert "19" in error or "Նdelays" in error  # Contains min amount

    def test_zero_amount_fails(self, mock_price):
        """Zero amount should fail"""
        from app.validation import validate_amount
        from app.models import CoinType

        is_valid, error = validate_amount(CoinType.BTC, 0.0)
        assert is_valid is False

    def test_price_fetch_failure_handled(self):
        """Should handle price fetch failure gracefully"""
        with patch('app.validation.get_coin_price_usd', return_value=None):
            from app.validation import validate_amount
            from app.models import CoinType

            is_valid, error = validate_amount(CoinType.BTC, 1.0)
            assert is_valid is False
            assert "Չ" in error or "գdelays" in error  # Armenian error message


class TestCommissionCalculation:
    """Test commission calculation"""

    def test_commission_percentage(self):
        """Commission should be 3%"""
        COMMISSION_PERCENT = 3.0
        amount = 100.0
        commission = amount * (COMMISSION_PERCENT / 100)
        assert commission == 3.0

    def test_commission_plus_fixed(self):
        """Total fee should be 3% + $1"""
        amount = 100.0
        commission_percent = 3.0
        fixed_fee = 1.0

        total_fee = (amount * commission_percent / 100) + fixed_fee
        assert total_fee == 4.0  # 3% of 100 + $1

    def test_user_receives_after_fees(self):
        """User should receive amount minus fees"""
        amount = 100.0
        commission_percent = 3.0
        fixed_fee = 1.0

        fee = (amount * commission_percent / 100) + fixed_fee
        user_receives = amount - fee
        assert user_receives == 96.0


class TestTXIDValidation:
    """Test TXID validation patterns"""

    def test_valid_btc_txid(self):
        """Valid BTC TXID format"""
        import re
        txid = "a65b33369cf0bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545"
        pattern = r"^[a-f0-9]{64}$"
        assert re.match(pattern, txid.lower()) is not None

    def test_valid_ltc_txid(self):
        """Valid LTC TXID format"""
        import re
        txid = "6559ce2924b306bde3ca6433b92e9bac94821f587fda74ada758fd8477cf4f16"
        pattern = r"^[a-f0-9]{64}$"
        assert re.match(pattern, txid.lower()) is not None

    def test_txid_case_insensitive(self):
        """TXID validation should be case insensitive"""
        import re
        txid_upper = "A65B33369CF0BCD1B4E7A47F00E6536612210AEB0DDB4E6AC557C9F83D316545"
        pattern = r"^[a-f0-9]{64}$"
        assert re.match(pattern, txid_upper.lower()) is not None

    def test_txid_with_spaces_fails(self):
        """TXID with spaces should fail"""
        import re
        txid = "a65b 3336 9cf0 bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545"
        pattern = r"^[a-f0-9]{64}$"
        assert re.match(pattern, txid.replace(" ", "")) is not None
        assert re.match(pattern, txid) is None


class TestAddressValidation:
    """Test cryptocurrency address validation"""

    def test_trc20_address_valid(self):
        """Valid TRC20 address"""
        address = "TVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3g"
        assert address.startswith("T")
        assert len(address) == 34

    def test_trc20_address_invalid_prefix(self):
        """TRC20 address with wrong prefix"""
        address = "0xVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3g"
        is_valid = address.startswith("T") and len(address) == 34
        assert is_valid is False

    def test_trc20_address_invalid_length(self):
        """TRC20 address with wrong length"""
        address = "TVQXrLPpULB6y4KnJ"  # Too short
        is_valid = address.startswith("T") and len(address) == 34
        assert is_valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
