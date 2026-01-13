import redis.asyncio as redis
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self, url: str):
        self.client = redis.from_url(url, encoding="utf-8", decode_responses=True)

    async def connect(self):
        """Establishes and tests the Redis connection on application startup."""
        logger.info("Initializing Redis connection...")
        try:
            await self.client.ping()
            logger.info("Redis connection successful.")
        except (redis.exceptions.ConnectionError, OSError) as e:
            logger.critical(f"Redis connection failed: {e}", exc_info=True)
            raise

    async def disconnect(self):
        """Closes the Redis connection on application shutdown."""
        logger.info("Closing Redis connection.")
        await self.client.close()


# --- Create a single, reusable Redis client instance ---
redis_client_instance = RedisClient(settings.REDIS_URL)

# Expose the raw client for use in the application
redis_client = redis_client_instance.client
