"""
Redis-based Rate Limiter for Convertbot
Supports distributed rate limiting across multiple instances
Falls back to in-memory if Redis is unavailable
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Tuple, Optional
from collections import defaultdict
from app.config import settings
from app.logger import setup_logger

logger = setup_logger(__name__)

# Try to import redis
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. Using in-memory rate limiting.")


class RateLimiter:
    """
    Distributed rate limiter using Redis with in-memory fallback.

    Features:
    - Per-user cooldown between swaps
    - Daily swap limit
    - Daily volume limit
    - Automatic cleanup of old entries
    """

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.use_redis = False

        # In-memory fallback storage
        self._memory_last_swap = {}  # user_id -> timestamp
        self._memory_daily_swaps = defaultdict(list)  # user_id -> list of timestamps
        self._memory_daily_volume = defaultdict(float)  # user_id -> USD volume

        # Configuration
        self.cooldown_seconds = getattr(settings, 'rate_limit_cooldown', 30)
        self.daily_swap_limit = getattr(settings, 'daily_swap_limit', 10)
        self.daily_volume_limit = getattr(settings, 'daily_volume_limit', 10000.0)

    async def connect(self):
        """Connect to Redis if available"""
        if not REDIS_AVAILABLE:
            logger.info("Rate limiter using in-memory storage (Redis not installed)")
            return

        redis_url = getattr(settings, 'redis_url', 'redis://localhost:6379/0')

        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            await self.redis_client.ping()
            self.use_redis = True
            logger.info(f"✅ Rate limiter connected to Redis: {redis_url}")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}. Using in-memory fallback.")
            self.redis_client = None
            self.use_redis = False

    async def check_rate_limit(self, user_id: int) -> Tuple[bool, str]:
        """
        Check if user is within rate limits.

        Returns:
            (is_allowed, error_message)
        """
        if self.use_redis:
            return await self._check_redis(user_id)
        else:
            return self._check_memory(user_id)

    async def record_swap(self, user_id: int, volume_usd: float = 0.0):
        """Record a successful swap for rate limiting"""
        if self.use_redis:
            await self._record_redis(user_id, volume_usd)
        else:
            self._record_memory(user_id, volume_usd)

    # ==================== Redis Implementation ====================

    async def _check_redis(self, user_id: int) -> Tuple[bool, str]:
        """Check rate limit using Redis"""
        now = time.time()
        user_key = f"ratelimit:{user_id}"

        try:
            # Check cooldown
            last_swap = await self.redis_client.hget(user_key, "last_swap")
            if last_swap:
                elapsed = now - float(last_swap)
                if elapsed < self.cooldown_seconds:
                    remaining = int(self.cooldown_seconds - elapsed)
                    return False, f"⏳ Սdelays delays delays {remaining} delays delays delays delays:"

            # Check daily swap count
            daily_count = await self.redis_client.hget(user_key, "daily_count")
            if daily_count and int(daily_count) >= self.daily_swap_limit:
                return False, f"📊 Delays delays {self.daily_swap_limit} delays delays delays delays delays:"

            # Check daily volume
            daily_volume = await self.redis_client.hget(user_key, "daily_volume")
            if daily_volume and float(daily_volume) >= self.daily_volume_limit:
                return False, f"💰 Delays delays ${self.daily_volume_limit:.0f} delays delays delays delays delays:"

            return True, ""

        except Exception as e:
            logger.error(f"Redis rate limit check error: {e}")
            # Fallback to allow on error
            return True, ""

    async def _record_redis(self, user_id: int, volume_usd: float):
        """Record swap in Redis"""
        now = time.time()
        user_key = f"ratelimit:{user_id}"

        try:
            pipe = self.redis_client.pipeline()

            # Update last swap time
            pipe.hset(user_key, "last_swap", str(now))

            # Increment daily count
            pipe.hincrby(user_key, "daily_count", 1)

            # Add volume
            pipe.hincrbyfloat(user_key, "daily_volume", volume_usd)

            # Set expiry for midnight reset (24 hours from now as fallback)
            pipe.expire(user_key, 86400)

            await pipe.execute()
            logger.debug(f"Recorded swap for user {user_id}: volume=${volume_usd:.2f}")

        except Exception as e:
            logger.error(f"Redis record swap error: {e}")

    # ==================== In-Memory Implementation ====================

    def _check_memory(self, user_id: int) -> Tuple[bool, str]:
        """Check rate limit using in-memory storage"""
        now = datetime.now()

        # Check cooldown
        if user_id in self._memory_last_swap:
            elapsed = (now - self._memory_last_swap[user_id]).total_seconds()
            if elapsed < self.cooldown_seconds:
                remaining = int(self.cooldown_seconds - elapsed)
                return False, f"⏳ Սdelays delays delays {remaining} delays delays delays delays:"

        # Clean old daily entries (older than 24h)
        today_start = now - timedelta(hours=24)
        self._memory_daily_swaps[user_id] = [
            ts for ts in self._memory_daily_swaps[user_id]
            if ts > today_start
        ]

        # Check daily swap limit
        if len(self._memory_daily_swaps[user_id]) >= self.daily_swap_limit:
            return False, f"📊 Delays delays {self.daily_swap_limit} delays delays delays delays delays:"

        # Check daily volume (reset if first swap today)
        if not self._memory_daily_swaps[user_id]:
            self._memory_daily_volume[user_id] = 0.0

        if self._memory_daily_volume[user_id] >= self.daily_volume_limit:
            return False, f"💰 Delays delays ${self.daily_volume_limit:.0f} delays delays delays delays delays:"

        return True, ""

    def _record_memory(self, user_id: int, volume_usd: float):
        """Record swap in memory"""
        now = datetime.now()
        self._memory_last_swap[user_id] = now
        self._memory_daily_swaps[user_id].append(now)
        self._memory_daily_volume[user_id] += volume_usd
        logger.debug(f"Recorded swap for user {user_id}: volume=${volume_usd:.2f}")

    # ==================== Admin Methods ====================

    async def get_user_stats(self, user_id: int) -> dict:
        """Get rate limit stats for a user (admin use)"""
        if self.use_redis:
            user_key = f"ratelimit:{user_id}"
            data = await self.redis_client.hgetall(user_key)
            return {
                "last_swap": data.get("last_swap"),
                "daily_count": int(data.get("daily_count", 0)),
                "daily_volume": float(data.get("daily_volume", 0)),
            }
        else:
            return {
                "last_swap": self._memory_last_swap.get(user_id),
                "daily_count": len(self._memory_daily_swaps.get(user_id, [])),
                "daily_volume": self._memory_daily_volume.get(user_id, 0),
            }

    async def reset_user(self, user_id: int):
        """Reset rate limit for a user (admin use)"""
        if self.use_redis:
            await self.redis_client.delete(f"ratelimit:{user_id}")
        else:
            self._memory_last_swap.pop(user_id, None)
            self._memory_daily_swaps.pop(user_id, None)
            self._memory_daily_volume.pop(user_id, None)
        logger.info(f"Reset rate limit for user {user_id}")

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()


# Global instance
rate_limiter = RateLimiter()


# Backwards-compatible functions
async def check_rate_limit(user_id: int) -> Tuple[bool, str]:
    """Check if user is within rate limits"""
    return await rate_limiter.check_rate_limit(user_id)


async def record_swap(user_id: int, volume_usd: float = 0.0):
    """Record a successful swap"""
    await rate_limiter.record_swap(user_id, volume_usd)
