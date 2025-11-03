# lipapp/services/ratelimit.py
import os, time, hashlib
from dataclasses import dataclass
from typing import Optional
import redis as redis_py

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
_r = None
def r():
    global _r
    if _r is None:
        _r = redis_py.from_url(REDIS_URL, decode_responses=True)
    return _r

def fingerprint(request) -> str:
    # کلید یکتا برای کاربر ناشناس
    if not request.session.session_key:
        request.session.save()
    raw = f"{request.session.session_key}|{request.META.get('REMOTE_ADDR')}|{request.META.get('HTTP_USER_AGENT')}"
    return hashlib.sha256(raw.encode()).hexdigest()

@dataclass
class Limit:
    limit: int     # حداکثر درخواست در پنجره
    window: int    # ثانیه

def allow(key: str, limit: Limit) -> tuple[bool, int, int]:
    """
    الگوریتم Fixed Window ساده:
    - key: مثلا "q:create:<room_slug>:<fp>" یا "q:vote:<question_id>:<fp>"
    - برمی‌گرداند: (allowed, remaining, reset_seconds)
    """
    now = int(time.time())
    bucket = now // limit.window
    redis_key = f"rl:{key}:{bucket}"
    pipe = r().pipeline()
    pipe.incr(redis_key)
    pipe.expire(redis_key, limit.window + 2)
    count, _ = pipe.execute()
    remaining = max(0, limit.limit - int(count))
    reset = ((bucket + 1) * limit.window) - now
    return (count <= limit.limit, remaining, reset)

def set_rate_headers(response, remaining: int, reset: int, limit: Limit):
    response["X-RateLimit-Limit"] = str(limit.limit)
    response["X-RateLimit-Remaining"] = str(remaining)
    response["X-RateLimit-Reset"] = str(reset)
    return response
