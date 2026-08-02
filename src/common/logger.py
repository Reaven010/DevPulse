"""
Logging setup for DevPulse.

Provides a centralized singleton logger that handles:
- Log level reading from config.py
- Dual output: Console (stdout) and Rotating File
- Automatic file log rotation
- Standardized log formatting
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
from typing import Optional, Union

try:
    from src.common.config import get_config, ConfigError
except ImportError:
    from common.config import get_config, ConfigError  # type: ignore


LOGGER_NAME = "devpulse"

# Global singleton tracking
_logger_initialized = False
_DEFAULT_LOG_DIR = Path("logs")
_LOG_FILE_NAME = f"{LOGGER_NAME}.log"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
_BACKUP_COUNT = 3             # Keep 3 backups
_DEFAULT_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _resolve_log_level() -> int:
    """Retrieve log level from config or fallback to INFO."""
    try:
        config = get_config()
        level_str = config.get("general", "log_level", "INFO")
    except ConfigError:
        level_str = "INFO"

    if isinstance(level_str, str):
        return getattr(logging, level_str.upper(), logging.INFO)
    if isinstance(level_str, int):
        return level_str

    return logging.INFO


def reset_logger() -> None:
    """Reset global logger initialization state and remove existing handlers."""
    global _logger_initialized
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(logging.NullHandler())
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    _logger_initialized = False


def setup_logger(
    log_dir: Optional[Union[str, Path]] = None,
    log_file: str = _LOG_FILE_NAME,
    max_bytes: int = _MAX_BYTES,
    backup_count: int = _BACKUP_COUNT,
    force: bool = False,
) -> logging.Logger:
    """
    Configure and initialize the main singleton logger.

    Args:
        log_dir: Directory where log files will be saved. Defaults to 'logs/'.
        log_file: Name of the log file. Defaults to f'{LOGGER_NAME}.log'.
        max_bytes: Maximum size of log file before rotation (default 5MB).
        backup_count: Number of rotated log files to retain (default 3).
        force: If True, forces re-initialization of logger handlers.

    Returns:
        The root singleton logger instance.
    """
    global _logger_initialized

    if _logger_initialized and not force:
        return logging.getLogger(LOGGER_NAME)

    if force:
        reset_logger()

    logger = logging.getLogger(LOGGER_NAME)

    # Resolve log level from config
    level = _resolve_log_level()
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(_DEFAULT_FORMAT, datefmt=_DATE_FORMAT)

    # 1. Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. Rotating File Handler
    target_dir = Path(log_dir) if log_dir else _DEFAULT_LOG_DIR
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / log_file
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning("Failed to initialize file logger at %s: %s", target_dir, e)

    _logger_initialized = True
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    If logger has not been initialized yet, it automatically initializes it.

    Args:
        name: Optional child logger suffix (e.g. 'github', 'weather').

    Returns:
        Singleton logger or named child logger (e.g., f'{LOGGER_NAME}.github').
    """
    if not _logger_initialized:
        setup_logger()

    if name:
        if name.startswith(f"{LOGGER_NAME}."):
            return logging.getLogger(name)
        return logging.getLogger(f"{LOGGER_NAME}.{name}")

    return logging.getLogger(LOGGER_NAME)


def set_log_level(level: Union[int, str]) -> None:
    """
    Dynamically update log level across all logger handlers.

    Args:
        level: Integer logging level or level name string ('DEBUG', 'INFO', etc.).
    """
    if isinstance(level, str):
        numeric_level = getattr(logging, level.upper(), logging.INFO)
    else:
        numeric_level = level

    logger = get_logger()
    logger.setLevel(numeric_level)
    for handler in logger.handlers:
        handler.setLevel(numeric_level)
