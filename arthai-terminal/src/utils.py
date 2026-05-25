import logging
import time
from src.config import settings

def setup_logging():
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler()]
    )


class RateLimiter:
    """Implements exponential backoff with jitter for API rate limiting."""
    
    def __init__(self, initial_delay: float = 0.1, max_delay: float = 30, max_retries: int = 5):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.retry_count = 0
    
    def wait(self):
        """Wait before next attempt using exponential backoff with jitter."""
        if self.retry_count >= self.max_retries:
            raise RuntimeError(f"Max retries ({self.max_retries}) exceeded")
        
        delay = min(self.initial_delay * (2 ** self.retry_count), self.max_delay)
        # Add jitter: ±10% of delay
        import random
        jitter = delay * (0.9 + 0.2 * random.random())
        
        logging.getLogger(__name__).debug(f"Rate limit: sleeping {jitter:.2f}s (retry {self.retry_count + 1}/{self.max_retries})")
        time.sleep(jitter)
        self.retry_count += 1
    
    def reset(self):
        """Reset retry counter on success."""
        self.retry_count = 0
    
    def should_retry(self, status_code: int) -> bool:
        """Check if response indicates rate limiting or transient error."""
        return status_code in (429, 503, 504, 408)  # Too Many Requests, Service Unavailable, Gateway Timeout, Request Timeout