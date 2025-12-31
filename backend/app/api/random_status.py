"""Random pool status API endpoint."""
from fastapi import APIRouter

from app.services.random_pool import random_pool

router = APIRouter(prefix="/api/random", tags=["random"])


@router.get("/status")
async def get_random_pool_status():
    """Get the current status of the true random pool.
    
    Returns:
        Dictionary with pool status information including:
        - enabled: Whether true randomness is enabled
        - api_available: Whether Random.org API is accessible
        - pool_size: Current number of cached random numbers
        - min_threshold: Minimum pool size before refill
        - is_refilling: Whether pool is currently being refilled
        - source: Random number source (random.org or pseudo-random)
    """
    return await random_pool.get_pool_status()
