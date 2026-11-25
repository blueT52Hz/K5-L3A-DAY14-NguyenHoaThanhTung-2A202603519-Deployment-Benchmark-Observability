from redis import Redis
from redis.exceptions import RedisError

from .config import settings


r = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=2)


def redis_healthy() -> bool:
    try:
        return bool(r.ping())
    except RedisError:
        return False
