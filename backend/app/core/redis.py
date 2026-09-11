from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings

async def create_redis_pool():
    return await create_pool(
        RedisSettings(
            host=settings.redis_host,
            port=settings.redis_port,
        )
    )