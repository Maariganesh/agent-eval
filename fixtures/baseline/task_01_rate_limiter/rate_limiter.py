import time

class SlidingWindowRateLimiter:
    def __init__(self, window_seconds, max_requests):
        # Naive implementation without argument validation
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.requests = {}

    def is_allowed(self, key):
        now = time.time()
        if key not in self.requests:
            self.requests[key] = []
        
        # filter timestamps
        cutoff = now - self.window_seconds
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]
        
        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(now)
            return True
        return False

    def get_remaining(self, key):
        now = time.time()
        if key not in self.requests:
            return self.max_requests
        cutoff = now - self.window_seconds
        valid = [t for t in self.requests[key] if t > cutoff]
        return max(0, self.max_requests - len(valid))
