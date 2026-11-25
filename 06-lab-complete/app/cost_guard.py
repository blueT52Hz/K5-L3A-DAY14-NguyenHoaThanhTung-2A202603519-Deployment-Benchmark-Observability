from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from utils.mock_llm import MOCK_RESPONSES

from .config import settings
from .redis_client import r


# Integer nano-USD per estimated token ($0.00015/$0.00060 per 1000 tokens).
INPUT_PRICE = 150
OUTPUT_PRICE = 600
MAX_OUTPUT_TOKENS = max(2 * len(reply.split()) for replies in MOCK_RESPONSES.values() for reply in replies)

reserve = r.register_script("""
local spent = tonumber(redis.call('GET', KEYS[1]) or 0)
if spent + tonumber(ARGV[1]) > tonumber(ARGV[2]) then return 0 end
redis.call('INCRBY', KEYS[1], ARGV[1])
redis.call('EXPIREAT', KEYS[1], ARGV[3])
return 1
""")
refund = r.register_script("""
if redis.call('EXISTS', KEYS[1]) == 1 then
    redis.call('DECRBY', KEYS[1], ARGV[1])
end
""")


def check_budget(input_tokens: int) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    key = f"cp5:budget:{now.date()}"
    amount = input_tokens * INPUT_PRICE + MAX_OUTPUT_TOKENS * OUTPUT_PRICE
    limit = int(settings.daily_budget_usd * 1_000_000_000)
    if not reserve(keys=[key], args=[amount, limit, int(midnight.timestamp())]):
        raise HTTPException(402, "Daily budget exhausted")
    return key, amount


def record_cost(reservation: tuple[str, int], input_tokens: int, output_tokens: int) -> float:
    key, reserved = reservation
    cost = input_tokens * INPUT_PRICE + output_tokens * OUTPUT_PRICE
    refund(keys=[key], args=[reserved - cost])
    return cost / 1_000_000_000
