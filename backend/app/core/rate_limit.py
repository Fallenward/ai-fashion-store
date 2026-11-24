import time
from collections import defaultdict

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import AppError


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, request: Request) -> None:
        if not get_settings().rate_limit_enabled:
            return
        host = request.client.host if request.client else "unknown"
        now = time.monotonic()
        recent = [stamp for stamp in self._hits[host] if now - stamp < self.window_seconds]
        if len(recent) >= self.limit:
            raise AppError("Too many requests. Please wait a moment and try again.", 429)
        recent.append(now)
        self._hits[host] = recent
        if len(self._hits) > 5000:
            self._hits.clear()


auth_limiter = RateLimiter(limit=20, window_seconds=60)
ai_limiter = RateLimiter(limit=30, window_seconds=60)
