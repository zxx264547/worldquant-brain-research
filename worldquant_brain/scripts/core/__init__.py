"""WorldQuant BRAIN 核心模块

提供统一的API封装、异常处理和重试机制
"""

from .exceptions import (
    BrainAPIError,
    AuthenticationError,
    SimulationTimeoutError,
    RateLimitError,
    SimulationError,
    AlphaNotFoundError,
    DataFieldError,
)

from .api_client import RetryableBrainClient
from .retry import async_retry, sync_retry
from .logging_config import setup_logging

__all__ = [
    'BrainAPIError',
    'AuthenticationError',
    'SimulationTimeoutError',
    'RateLimitError',
    'SimulationError',
    'AlphaNotFoundError',
    'DataFieldError',
    'RetryableBrainClient',
    'async_retry',
    'sync_retry',
    'setup_logging',
]