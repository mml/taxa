"""Retry wrapper with exponential backoff for API calls."""
import time
import logging
from typing import Callable, Any, TypeVar
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RateLimitError(Exception):
    """Raised when API rate limit is hit."""
    pass


def with_retry(
    func: Callable[..., T],
    *args,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    **kwargs
) -> T:
    """
    Retry a function with exponential backoff.

    Handles network errors, timeouts, and rate limiting (429 errors).

    Args:
        func: Function to retry
        *args: Positional arguments to pass to func
        max_attempts: Maximum number of attempts (default 3)
        base_delay: Initial delay in seconds (default 1.0)
        max_delay: Maximum delay in seconds (default 60.0)
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result from successful function call

    Raises:
        Exception: Re-raises the last exception if all attempts fail
    """
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)

        except Exception as e:
            last_exception = e
            error_str = str(e)

            # Check if this is a retryable error
            is_network_error = isinstance(e, (ConnectionError, TimeoutError))
            is_rate_limit = '429' in error_str or 'Too Many Requests' in error_str

            if not (is_network_error or is_rate_limit):
                # Not a retryable error, raise immediately
                raise

            # Last attempt, don't sleep, just raise
            if attempt == max_attempts - 1:
                logger.error(f"Failed after {max_attempts} attempts: {e}")
                raise

            # Calculate delay with exponential backoff
            delay = min(base_delay * (2 ** attempt), max_delay)

            logger.info(
                f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                f"Retrying in {delay}s..."
            )

            time.sleep(delay)

    # Should never reach here, but just in case
    raise last_exception


def retry_on_rate_limit(max_attempts: int = 3):
    """
    Decorator to add retry logic to a function.

    Usage:
        @retry_on_rate_limit(max_attempts=5)
        def my_api_call():
            return api.get(...)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return with_retry(func, *args, max_attempts=max_attempts, **kwargs)
        return wrapper
    return decorator
