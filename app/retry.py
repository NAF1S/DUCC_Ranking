from functools import wraps
import asyncio
import logging
from typing import TypeVar, Callable, Any

T = TypeVar('T')

def async_retry(
    retries: int = 3,
    delay: float = 1,
    backoff: float = 2,
    exceptions: tuple = (Exception,),
    logger: logging.Logger = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying asynchronous functions with exponential backoff.
    
    Args:
        retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff: Multiplier for the delay between retries
        exceptions: Tuple of exceptions to catch
        logger: Logger instance for logging retries
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            current_delay = delay

            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == retries:
                        break
                        
                    if logger:
                        logger.warning(
                            f"Attempt {attempt + 1}/{retries} failed: {str(e)}. "
                            f"Retrying in {current_delay} seconds..."
                        )
                        
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            if logger:
                logger.error(f"All {retries} retries failed. Last error: {str(last_exception)}")
            raise last_exception

        return wrapper
    return decorator
