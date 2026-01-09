"""True random number pool using Random.org API.

This module provides a pool of true random numbers generated from atmospheric noise
via Random.org's API. Numbers are fetched in batches and cached locally for fast access.
Falls back to pseudo-random generation if the API is unavailable.
"""

import asyncio
import random

import httpx

from app.config import settings
from app.observability.logger import get_logger

logger = get_logger(__name__)


class TrueRandomPool:
    """Pool of true random numbers from Random.org.

    Fetches random numbers in batches and maintains a local cache for fast access.
    Automatically refills when the pool drops below the minimum threshold.
    Gracefully falls back to Python's pseudo-random generator if API is unavailable.
    """

    def __init__(self):
        """Initialize the random pool."""
        self.pool: list[int] = []
        self.is_refilling: bool = False
        self.refill_lock = asyncio.Lock()
        self.enabled = settings.use_true_randomness
        self.api_available = True  # Assume available until proven otherwise

        logger.info(
            f"TrueRandomPool initialized (enabled={self.enabled}, "
            f"pool_size={settings.random_pool_size}, "
            f"min_threshold={settings.random_pool_min_threshold})"
        )

    async def get_random_int(self, min_val: int, max_val: int) -> int:
        """Get a random integer in the specified range.

        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)

        Returns:
            Random integer between min_val and max_val
        """
        # If true randomness is disabled, use pseudo-random immediately
        if not self.enabled:
            return random.randint(min_val, max_val)

        # Check if pool needs refilling
        if len(self.pool) < settings.random_pool_min_threshold:
            await self._refill_pool()

        # Try to use a number from the pool
        if self.pool:
            raw_number = self.pool.pop()
            # Scale the random number to the desired range
            # Using modulo is simple but slightly biases toward lower values
            # For dice rolls (small ranges), this bias is negligible
            return (raw_number % (max_val - min_val + 1)) + min_val
        else:
            # Fallback to pseudo-random if pool is empty
            logger.debug("Random pool empty, using pseudo-random fallback")
            return random.randint(min_val, max_val)

    async def _refill_pool(self):
        """Refill the random pool from Random.org API.

        Fetches a batch of random numbers from Random.org. Uses a lock to prevent
        multiple simultaneous refill operations. Fails gracefully if API is unavailable.
        """
        # Prevent multiple simultaneous refills
        if self.is_refilling:
            return

        async with self.refill_lock:
            # Double-check after acquiring lock
            if self.is_refilling:
                return

            self.is_refilling = True

            try:
                # Construct Random.org API URL
                # Fetching numbers in range 1 to 1,000,000 for good distribution
                url = (
                    f"{settings.random_org_url}"
                    f"?num={settings.random_pool_size}"
                    f"&min=1"
                    f"&max=1000000"
                    f"&col=1"
                    f"&base=10"
                    f"&format=plain"
                    f"&rnd=new"
                )

                logger.debug(f"Fetching {settings.random_pool_size} random numbers from Random.org")

                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=settings.random_pool_timeout)

                    if response.status_code == 200:
                        # Parse the response (plain text with one number per line)
                        numbers = [
                            int(line.strip())
                            for line in response.text.strip().split("\n")
                            if line.strip()
                        ]

                        # Add to pool
                        self.pool.extend(numbers)
                        self.api_available = True

                        logger.info(
                            f"Refilled random pool with {len(numbers)} numbers "
                            f"(total pool size: {len(self.pool)})"
                        )

                    elif response.status_code == 503:
                        # Service unavailable - quota exhausted or server overloaded
                        logger.warning(
                            "Random.org API returned 503 (Service Unavailable). "
                            "Quota may be exhausted. Using pseudo-random fallback."
                        )
                        self.api_available = False

                    else:
                        logger.warning(
                            f"Random.org API returned unexpected status {response.status_code}. "
                            "Using pseudo-random fallback."
                        )
                        self.api_available = False

            except httpx.TimeoutException:
                logger.warning(
                    f"Random.org API request timed out after {settings.random_pool_timeout}s. "
                    "Using pseudo-random fallback."
                )
                self.api_available = False

            except Exception as e:
                logger.error(
                    f"Failed to fetch random numbers from Random.org: {e}. "
                    "Using pseudo-random fallback."
                )
                self.api_available = False

            finally:
                self.is_refilling = False

    async def get_pool_status(self) -> dict:
        """Get current status of the random pool.

        Returns:
            Dictionary with pool status information
        """
        return {
            "enabled": self.enabled,
            "api_available": self.api_available,
            "pool_size": len(self.pool),
            "min_threshold": settings.random_pool_min_threshold,
            "is_refilling": self.is_refilling,
            "source": "random.org" if self.enabled and self.api_available else "pseudo-random",
        }


# Global instance
random_pool = TrueRandomPool()
