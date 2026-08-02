"""Unit tests for logger module."""

import logging
from pathlib import Path
import tempfile
import pytest

from src.common.logger import get_logger, setup_logger, set_log_level, reset_logger


@pytest.fixture(autouse=True)
def cleanup_logger():
    """Reset logger handlers before and after each test."""
    reset_logger()
    yield
    reset_logger()


def test_singleton_logger():
    logger1 = get_logger()
    logger2 = get_logger()
    assert logger1 is logger2
    assert logger1.name == "devpulse"


def test_child_logger():
    child_logger = get_logger("github")
    assert child_logger.name == "devpulse.github"
    assert child_logger.parent.name == "devpulse"


def test_file_logging_and_rotation():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        log_file_name = "test.log"
        
        # Test custom setup with force=True
        logger = setup_logger(log_dir=test_dir, log_file=log_file_name, max_bytes=100, backup_count=2, force=True)
        logger.info("Hello world test log message")
        
        log_file_path = test_dir / log_file_name
        assert log_file_path.exists()
        
        content = log_file_path.read_text(encoding="utf-8")
        assert "Hello world test log message" in content

        # Close file handlers so Windows file lock is released before cleanup
        reset_logger()


def test_set_log_level():
    logger = get_logger()
    set_log_level("DEBUG")
    assert logger.level == logging.DEBUG
    set_log_level("WARNING")
    assert logger.level == logging.WARNING
