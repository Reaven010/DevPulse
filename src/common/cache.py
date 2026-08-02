"""
Cache manager for DevPulse.

Provides thread-safe, atomic JSON file-based caching with TTL expiry checks,
strict schema validation, and atomic writes via pathlib.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from src.common.config import ConfigError, get_config
    from src.common.logger import get_logger
except ImportError:
    from common.config import ConfigError, get_config  # type: ignore
    from common.logger import get_logger  # type: ignore

logger = get_logger("cache")


class CacheManager:
    """
    Thread-safe JSON file cache manager with atomic writes and TTL validation.
    """

    def __init__(self, cache_dir: Optional[Union[str, Path]] = None):
        """
        Initialize CacheManager.

        Args:
            cache_dir: Path to directory where cache files are stored.
                       If None, resolves from application config or defaults to './cache'.
        """
        self._lock = threading.RLock()

        if cache_dir is not None:
            self.cache_dir = Path(cache_dir).resolve()
        else:
            self.cache_dir = self._resolve_cache_dir()

        self._ensure_dir()

    def _resolve_cache_dir(self) -> Path:
        """Resolve cache directory from configuration."""
        try:
            config = get_config()
            dir_str = config.get("general", "cache", "./cache")
            return Path(dir_str).resolve()
        except ConfigError:
            return Path("./cache").resolve()

    def _ensure_dir(self) -> None:
        """Create cache directory if it does not exist."""
        with self._lock:
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.error("Failed to create cache directory at %s: %s", self.cache_dir, e)

    def _get_file_path(self, key: str) -> Path:
        """Get path for a cache file given a key."""
        filename = key if key.endswith(".json") else f"{key}.json"
        return self.cache_dir / filename

    def _unpack_envelope(self, target_path: Path, envelope: Any) -> Tuple[float, Any]:
        """
        Validate structure and extract timestamp and data payload.

        Raises:
            ValueError: If envelope structure or timestamp type is invalid.
        """
        if isinstance(envelope, dict) and "timestamp" in envelope and "data" in envelope:
            ts = envelope["timestamp"]
            if not isinstance(ts, (int, float)):
                raise ValueError(
                    f"Cache file '{target_path.name}' has invalid timestamp type: {type(ts).__name__}"
                )
            return float(ts), envelope["data"]

        # Legacy or raw JSON format fallback
        try:
            ts = target_path.stat().st_mtime
        except OSError:
            ts = datetime.now(timezone.utc).timestamp()
        return float(ts), envelope

    def set(self, key: str, data: Any) -> bool:
        """
        Write data to cache atomically using Path.replace().

        Args:
            key: Cache key (file identifier).
            data: JSON-serializable data to store.

        Returns:
            True if write succeeded, False otherwise.
        """
        with self._lock:
            self._ensure_dir()
            target_path = self._get_file_path(key)

            envelope = {
                "timestamp": datetime.now(timezone.utc).timestamp(),
                "data": data,
            }

            try:
                # Atomic write via temporary file in the same directory
                temp_file = tempfile.NamedTemporaryFile(
                    mode="w",
                    dir=self.cache_dir,
                    delete=False,
                    encoding="utf-8",
                    suffix=".tmp",
                )
                temp_path = Path(temp_file.name)
                try:
                    json.dump(envelope, temp_file, indent=2, ensure_ascii=False)
                    temp_file.flush()
                    os.fsync(temp_file.fileno())
                    temp_file.close()

                    # Atomic replace using pathlib
                    temp_path.replace(target_path)
                    logger.debug("Successfully cached data for key '%s'", key)
                    return True
                except (OSError, TypeError, ValueError) as write_err:
                    temp_file.close()
                    if temp_path.exists():
                        try:
                            temp_path.unlink()
                        except OSError:
                            pass
                    logger.error("Error writing cache for key '%s': %s", key, write_err)
                    return False
            except OSError as e:
                logger.error("OS Error setting cache for key '%s': %s", key, e)
                return False

    def get(self, key: str, ttl_seconds: Optional[int] = None, default: Any = None) -> Any:
        """
        Read cached data if present, valid, and not expired.

        Args:
            key: Cache key.
            ttl_seconds: Optional Time-To-Live in seconds. If exceeded, returns default.
            default: Fallback value if cache miss, corrupted, or expired.

        Returns:
            Cached data or default value.
        """
        with self._lock:
            target_path = self._get_file_path(key)
            if not target_path.exists():
                logger.debug("Cache miss for key '%s' (file not found)", key)
                return default

            try:
                with target_path.open("r", encoding="utf-8") as f:
                    envelope = json.load(f)

                ts, payload = self._unpack_envelope(target_path, envelope)

                if ttl_seconds is not None:
                    now = datetime.now(timezone.utc).timestamp()
                    if (now - ts) > ttl_seconds:
                        logger.debug(
                            "Cache expired for key '%s' (age: %.1fs > TTL: %ds)",
                            key,
                            now - ts,
                            ttl_seconds,
                        )
                        return default

                logger.debug("Cache hit for key '%s'", key)
                return payload
            except (OSError, json.JSONDecodeError, ValueError) as e:
                logger.warning("Cache reading error for key '%s': %s", key, e)
                return default

    def exists(self, key: str, ttl_seconds: Optional[int] = None) -> bool:
        """
        Check if a valid, non-expired cache entry exists for the given key.

        Args:
            key: Cache key identifier.
            ttl_seconds: Optional TTL limit in seconds.

        Returns:
            True if valid cache exists and is unexpired, False otherwise.
        """
        with self._lock:
            target_path = self._get_file_path(key)
            if not target_path.exists():
                return False

            if ttl_seconds is not None:
                return not self.is_expired(key, ttl_seconds)

            try:
                with target_path.open("r", encoding="utf-8") as f:
                    envelope = json.load(f)
                self._unpack_envelope(target_path, envelope)
                return True
            except (OSError, json.JSONDecodeError, ValueError):
                return False

    def is_expired(self, key: str, ttl_seconds: int) -> bool:
        """
        Check if a cache key is missing, invalid, or expired.

        Args:
            key: Cache key.
            ttl_seconds: Maximum allowed age in seconds.

        Returns:
            True if key is missing/corrupt or older than ttl_seconds, False otherwise.
        """
        with self._lock:
            target_path = self._get_file_path(key)
            if not target_path.exists():
                return True

            try:
                with target_path.open("r", encoding="utf-8") as f:
                    envelope = json.load(f)
                ts, _ = self._unpack_envelope(target_path, envelope)
                now = datetime.now(timezone.utc).timestamp()
                return (now - ts) > ttl_seconds
            except (OSError, json.JSONDecodeError, ValueError):
                return True

    def get_timestamp(self, key: str) -> Optional[float]:
        """
        Get the creation/update timestamp for a cached key.

        Returns:
            Unix timestamp float or None if missing/corrupted.
        """
        with self._lock:
            target_path = self._get_file_path(key)
            if not target_path.exists():
                return None

            try:
                with target_path.open("r", encoding="utf-8") as f:
                    envelope = json.load(f)
                ts, _ = self._unpack_envelope(target_path, envelope)
                return ts
            except (OSError, json.JSONDecodeError, ValueError):
                return None

    def list_keys(self) -> List[str]:
        """
        List all cached key names in the cache directory.

        Returns:
            List of key names without '.json' extension (e.g. ['github', 'weather']).
        """
        with self._lock:
            if not self.cache_dir.exists():
                return []
            keys: List[str] = []
            for path in sorted(self.cache_dir.glob("*.json")):
                keys.append(path.stem)
            return keys

    def delete(self, key: str) -> bool:
        """Delete a cache file if it exists."""
        with self._lock:
            target_path = self._get_file_path(key)
            if target_path.exists():
                try:
                    target_path.unlink()
                    logger.debug("Deleted cache for key '%s'", key)
                    return True
                except OSError as e:
                    logger.error("Failed to delete cache file for key '%s': %s", key, e)
                    return False
            return False

    def clear(self) -> int:
        """
        Clear all JSON cache files in cache directory.

        Returns:
            Number of files removed.
        """
        with self._lock:
            removed_count = 0
            if self.cache_dir.exists():
                for p in self.cache_dir.glob("*.json"):
                    try:
                        p.unlink()
                        removed_count += 1
                    except OSError as e:
                        logger.error("Failed to delete cache file %s: %s", p, e)
            return removed_count


# Global singleton instance
_cache_manager: Optional[CacheManager] = None


def get_cache(cache_dir: Optional[Union[str, Path]] = None) -> CacheManager:
    """
    Get global CacheManager singleton instance.

    Args:
        cache_dir: Optional custom cache directory path.

    Returns:
        Singleton CacheManager instance.
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(cache_dir)
    return _cache_manager


def clear_global_cache_instance() -> None:
    """Clear global singleton reference (useful for testing)."""
    global _cache_manager
    _cache_manager = None
