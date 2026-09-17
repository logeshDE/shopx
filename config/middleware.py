"""
Custom middleware for the ShopX project.

Provides:
  - SecurityHeadersMiddleware: adds common security-related HTTP response headers.
  - RateLimitMiddleware: simple per-IP request rate limiter, backed by Redis
    when available (falls back to an in-memory counter otherwise).
"""

import time
import os

from django.conf import settings
from django.http import HttpResponse

try:
    import redis as redis_lib
except ImportError:
    redis_lib = None


class SecurityHeadersMiddleware:
    """Adds common security-related HTTP response headers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('X-Frame-Options', 'DENY')
        response.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.setdefault('X-XSS-Protection', '1; mode=block')
        response.setdefault(
            'Permissions-Policy',
            'geolocation=(), microphone=(), camera=()'
        )
        return response


class RateLimitMiddleware:
    """
    Sliding-window request rate limiter, keyed by client IP.

    Uses Redis (via settings.REDIS_URL) when available so limits are shared
    across all app instances; falls back to a local in-memory counter if
    Redis can't be reached (e.g. local development).

    Configure via settings.RATE_LIMIT_MAX (default 120 requests) and
    settings.RATE_LIMIT_WINDOW (default 60 seconds).
    """

    _memory_store = {}

    def __init__(self, get_response):
        self.get_response = get_response
        self.max_requests = getattr(settings, 'RATE_LIMIT_MAX', 120)
        self.window_seconds = getattr(settings, 'RATE_LIMIT_WINDOW', 60)
        self.redis_client = None

        redis_url = getattr(settings, 'REDIS_URL', os.environ.get('REDIS_URL'))
        if redis_lib and redis_url:
            try:
                self.redis_client = redis_lib.from_url(redis_url)
                self.redis_client.ping()
            except Exception:
                self.redis_client = None

    def __call__(self, request):
        client_ip = self._get_client_ip(request)
        key = f'ratelimit:{client_ip}'

        if self.redis_client is not None:
            try:
                count = self.redis_client.incr(key)
                if count == 1:
                    self.redis_client.expire(key, self.window_seconds)
                if count > self.max_requests:
                    return self._too_many_requests()
            except Exception:
                # Fail open if Redis has a transient issue mid-request.
                pass
        else:
            if self._memory_increment(key) > self.max_requests:
                return self._too_many_requests()

        return self.get_response(request)

    def _memory_increment(self, key):
        now = time.time()
        entry = self._memory_store.get(key)
        if entry is None or now - entry['start'] > self.window_seconds:
            self._memory_store[key] = {'start': now, 'count': 1}
            return 1
        entry['count'] += 1
        return entry['count']

    @staticmethod
    def _get_client_ip(request):
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

    @staticmethod
    def _too_many_requests():
        return HttpResponse(
            'Too many requests. Please slow down and try again shortly.',
            status=429,
        )
