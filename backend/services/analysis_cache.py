"""
Simple caching service for analysis results.
Uses in-memory dictionary cache with TTL support.
"""

import time
from typing import Any, Optional
from threading import Lock


class AnalysisCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, default_ttl: int = 3600):
        """
        Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 1 hour)
        """
        self.cache = {}
        self.lock = Lock()
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if exists and not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if time.time() < expiry:
                    return value
                else:
                    # Expired, remove it
                    del self.cache[key]
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not provided)
        """
        if ttl is None:
            ttl = self.default_ttl

        expiry = time.time() + ttl

        with self.lock:
            self.cache[key] = (value, expiry)

    def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cached values."""
        with self.lock:
            self.cache.clear()

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, (_, expiry) in self.cache.items()
                if expiry < current_time
            ]

            for key in expired_keys:
                del self.cache[key]

            return len(expired_keys)

    def size(self) -> int:
        """Get current number of cached entries."""
        with self.lock:
            return len(self.cache)


# Global cache instance
_analysis_cache = AnalysisCache(default_ttl=3600)  # 1 hour default


def get_analysis_cache() -> AnalysisCache:
    """Get the global analysis cache instance."""
    return _analysis_cache
