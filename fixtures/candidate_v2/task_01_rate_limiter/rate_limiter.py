"""
Sliding Window Rate Limiter implementation with thread safety and defensive validation.
"""
from __future__ import annotations

import collections
import threading
import time
from typing import Deque, Dict


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding window log rate limiter.
    """

    def __init__(self, window_seconds: float, max_requests: int) -> None:
        """
        Initializes the rate limiter with a sliding window duration and request limit.
        """
        if window_seconds <= 0:
            raise ValueError(f"window_seconds must be positive, got {window_seconds}")
        if max_requests <= 0:
            raise ValueError(f"max_requests must be positive, got {max_requests}")

        self.window_seconds: float = float(window_seconds)
        self.max_requests: int = int(max_requests)
        self._requests: Dict[str, Deque[float]] = collections.defaultdict(collections.deque)
        self._lock: threading.Lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        """
        Determines whether a request for the given key is permitted under current rate limits.
        """
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            timestamps = self._requests[key]
            # Prune expired timestamps
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) < self.max_requests:
                timestamps.append(now)
                return True
            return False

    def get_remaining(self, key: str) -> int:
        """
        Returns the remaining request quota for the key within the active sliding window.
        """
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            return max(0, self.max_requests - len(timestamps))
