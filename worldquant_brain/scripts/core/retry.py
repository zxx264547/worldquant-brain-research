"""异步重试装饰器"""

import asyncio
import functools
import logging
import random
from typing import TypeVar, Callable

logger = logging.getLogger(__name__)
T = TypeVar('T')


def async_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, max_delay: float = 60.0):
    """异步重试装饰器（带指数退避和jitter）

    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟（秒）
        backoff: 延迟倍增因子
        max_delay: 最大延迟（秒）
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        # 指数退避 + 随机jitter
                        sleep_time = min(current_delay * backoff + random.uniform(0, 0.5), max_delay)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {sleep_time:.1f}s..."
                        )
                        await asyncio.sleep(sleep_time)
                        current_delay = sleep_time
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )

            raise last_exception
        return wrapper
    return decorator


def sync_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """同步重试装饰器"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )

            raise last_exception
        return wrapper
    return decorator