#!/usr/bin/env python3
"""共享日志工具 - 带轮转的日志记录器"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys


def get_logger(name: str, log_file: str, max_mb: int = 10, backup_count: int = 3,
               also_console: bool = True) -> logging.Logger:
    """获取带轮转的logger

    Args:
        name: logger名称
        log_file: 日志文件路径
        max_mb: 单个日志文件最大MB
        backup_count: 保留的备份数量
        also_console: 是否同时输出到控制台
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(file_handler)

    if also_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(
            '%(message)s'
        ))
        logger.addHandler(console_handler)

    return logger
