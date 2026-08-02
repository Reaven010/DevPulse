"""Unit tests for cache manager module."""

import json
from pathlib import Path
import tempfile
import threading
import time

import pytest

from src.common.cache import CacheManager, clear_global_cache_instance, get_cache


@pytest.fixture(autouse=True)
def reset_global_cache():
    clear_global_cache_instance()
    yield
    clear_global_cache_instance()


def test_auto_directory_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        target_dir = Path(tmpdir) / "nested" / "cache_dir"
        assert not target_dir.exists()

        cache = CacheManager(cache_dir=target_dir)
        assert target_dir.exists()


def test_set_and_get():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheManager(cache_dir=tmpdir)
        test_data = {"user": "Reaven010", "scores": [10, 20, 30]}

        assert cache.set("test_key", test_data) is True
        result = cache.get("test_key")
        assert result == test_data


def test_exists_and_list_keys():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheManager(cache_dir=tmpdir)

        assert cache.exists("github") is False
        assert cache.list_keys() == []

        cache.set("github", {"stars": 42})
        cache.set("weather", {"temp": 22})
        cache.set("leetcode", {"solved": 150})

        assert cache.exists("github") is True
        assert cache.exists("nonexistent") is False

        assert cache.list_keys() == ["github", "leetcode", "weather"]


def test_validation_and_corrupt_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheManager(cache_dir=tmpdir)
        corrupt_file = Path(tmpdir) / "corrupt.json"

        # 1. Invalid JSON syntax
        corrupt_file.write_text("{invalid_json: ", encoding="utf-8")
        assert cache.get("corrupt") is None
        assert cache.exists("corrupt") is False
        assert cache.is_expired("corrupt", ttl_seconds=60) is True

        # 2. Invalid timestamp type (string instead of int/float)
        invalid_ts_file = Path(tmpdir) / "invalid_ts.json"
        invalid_ts_file.write_text(
            json.dumps({"timestamp": "not_a_number", "data": 123}), encoding="utf-8"
        )
        assert cache.get("invalid_ts") is None
        assert cache.exists("invalid_ts") is False


def test_ttl_expiration():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheManager(cache_dir=tmpdir)
        test_data = {"status": "ok"}

        cache.set("quick_ttl", test_data)

        # Non-expired read
        assert cache.get("quick_ttl", ttl_seconds=10) == test_data
        assert cache.is_expired("quick_ttl", ttl_seconds=10) is False
        assert cache.exists("quick_ttl", ttl_seconds=10) is True

        # Expired check with ttl_seconds=0
        time.sleep(0.01)
        assert cache.get("quick_ttl", ttl_seconds=0) is None
        assert cache.is_expired("quick_ttl", ttl_seconds=0) is True
        assert cache.exists("quick_ttl", ttl_seconds=0) is False


def test_delete_and_clear():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheManager(cache_dir=tmpdir)
        cache.set("file1", {"a": 1})
        cache.set("file2", {"b": 2})

        assert cache.delete("file1") is True
        assert cache.get("file1") is None
        assert cache.exists("file1") is False

        cleared_count = cache.clear()
        assert cleared_count == 1
        assert cache.get("file2") is None


def test_thread_safety():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheManager(cache_dir=tmpdir)
        errors = []

        def worker(worker_id: int):
            try:
                for i in range(20):
                    cache.set(f"thread_{worker_id}", {"step": i})
                    val = cache.get(f"thread_{worker_id}")
                    assert val is not None
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
