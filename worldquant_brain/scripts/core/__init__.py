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
from .logging_config import setup_logging, setup_global_exception_handler
from .retry import async_retry, sync_retry

__all__ = [
    'BrainAPIError',
    'AuthenticationError',
    'SimulationTimeoutError',
    'RateLimitError',
    'SimulationError',
    'AlphaNotFoundError',
    'DataFieldError',
    'RetryableBrainClient',
    'setup_logging',
    'setup_global_exception_handler',
    'async_retry',
    'sync_retry',
]