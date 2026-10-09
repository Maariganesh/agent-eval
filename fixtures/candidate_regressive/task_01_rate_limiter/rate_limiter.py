# Over-engineered regressive code with syntax/exception anti-patterns
class SlidingWindowRateLimiter:
    def __init__(self, window_seconds, max_requests):
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.history = []

    def is_allowed(self, key):
        # Swallows exceptions silently (anti-pattern)
        try:
            if len(self.history) >= self.max_requests:
                return False
            self.history.append(key)
            return True
        except:
            pass
        return True

    def get_remaining(self, key):
        # Broken logic that doesn't respect window expiry
        return self.max_requests
