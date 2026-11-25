import hashlib
from uuid import uuid4

from fastapi import HTTPException

from .config import settings
from .redis_client import r


# Use the Redis clock so all workers share the same 60-second window.
admit_request = r.register_script("""
local clock = redis.call('TIME')
local now = tonumber(clock[1]) * 1000 + math.floor(tonumber(clock[2]) / 1000)
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - 60000)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    if not oldest[2] then return 60 end
    return math.ceil((oldest[2] + 60000 - now) / 1000)
end
redis.call('ZADD', KEYS[1], now, ARGV[2])
redis.call('EXPIRE', KEYS[1], 60)
return 0
""")


def check_rate_limit(key: str) -> None:
    digest = hashlib.sha256(key.encode()).hexdigest()
    retry_after = admit_request(keys=[f"cp5:rate:{digest}"],
                                args=[settings.rate_limit_per_minute, uuid4().hex])
    if retry_after:
        raise HTTPException(429, "Rate limit exceeded", headers={"Retry-After": str(retry_after)})
