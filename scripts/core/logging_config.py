"""标准日志配置"""

import logging
import sys
from pathlib import Path


def setup_logging(name: str = None, level: int = logging.INFO) -> logging.Logger:
    """标准日志配置"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger


def setup_global_exception_handler(logger: logging.Logger = None):
    """全局异常处理"""
    if logger is None:
        logger = logging.getLogger(__name__)

    def exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.error(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = exception_handler