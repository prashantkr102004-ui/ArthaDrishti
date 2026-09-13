from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import uuid4

from fastapi import Request, Response, status
from starlette.responses import JSONResponse


@dataclass(frozen=True)
class RateLimitRule:
    methods: frozenset[str]
    path_prefix: str
    max_requests: int
    window_seconds: int


class InMemoryRateLimiter:
    def __init__(self, rules: list[RateLimitRule] | None = None) -> None:
        self.rules = rules or []
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def reset(self) -> None:
        self._buckets.clear()

    def check(self, request: Request) -> tuple[bool, int | None]:
        rule = self._match_rule(request)
        if rule is None:
            return True, None

        now = time.monotonic()
        key = self._bucket_key(request, rule)
        bucket = self._buckets[key]
        cutoff = now - rule.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= rule.max_requests:
            retry_after = max(1, int(rule.window_seconds - (now - bucket[0])))
            return False, retry_after

        bucket.append(now)
        return True, None

    def _match_rule(self, request: Request) -> RateLimitRule | None:
        method = request.method.upper()
        path = request.url.path
        for rule in self.rules:
            if method in rule.methods and path.startswith(rule.path_prefix):
                return rule
        return None

    def _bucket_key(self, request: Request, rule: RateLimitRule) -> str:
        client_host = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_host = forwarded_for.split(",", maxsplit=1)[0].strip() or client_host
        return f"{client_host}:{request.method.upper()}:{rule.path_prefix}"


api_rate_limiter = InMemoryRateLimiter(
    rules=[
        RateLimitRule(frozenset({"POST"}), "/api/v1/auth/login", 120, 60),
        RateLimitRule(frozenset({"POST"}), "/api/v1/auth/register", 120, 60),
        RateLimitRule(frozenset({"POST"}), "/api/v1/assistant/query", 120, 60),
        RateLimitRule(frozenset({"POST"}), "/api/v1/document-search", 120, 60),
        RateLimitRule(frozenset({"POST"}), "/api/v1/documents", 120, 60),
    ]
)


async def security_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("x-request-id") or str(uuid4())
    request.state.request_id = request_id

    allowed, retry_after = api_rate_limiter.check(request)
    if not allowed:
        response = JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Too many requests. Please try again shortly."},
        )
        if retry_after is not None:
            response.headers["Retry-After"] = str(retry_after)
    else:
        response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response
