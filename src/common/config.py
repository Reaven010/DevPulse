"""Configuration parser and loader."""

from pathlib import Path
from typing import Any, Dict, Optional, Union

import os
import tomli
import copy


class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass


class Config:
    """
    Manages application configuration.

    Features:
    - TOML config file support with automatic detection
    - Environment variable overrides
    - Validation and type enforcement
    - Default values for all settings
    """
    
    # --- Default values ---
    DEFAULT_CONFIG = {
        "general": {
            "theme": "github-dark",
            "cache": "./cache",
            "log_level": "INFO",
            "username": "",
            "debug": False,
        },
        "refresh": {
            "github": 600,
            "leetcode": 900,
            "weather": 900,
            "media": 2,
            "git": 5,
            "system": 1,
        },
        "github": {
            "enabled": True,
            "username": "",
            "access_token": "",
        },
        "leetcode": {
            "enabled": True,
            "username": "",
        },
        "weather": {
            "enabled": False,
            "api_key": "",
            "city": "",
            "units": "metric",
        },
        "music": {
            "enabled": True,
            "player": "auto",
        },
        "system": {
            "cpu": True,
            "memory": True,
            "disk": True,
            "network": True,
            "temperature": True,
            "battery": True,
        },
    }
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Optional path to config file. If None, searches automatically.
        """
        self.config_path: Optional[Path] = None
        self._data: Dict[str, Dict[str, Any]] = {}
        
        # Auto-detect config file if not specified
        if config_path is None:
            self.config_path = Path("config/config.toml").resolve()
        else:
            self.config_path = Path(config_path).resolve()
        
        # Load configuration
        self._load()
    
    
    def _load(self):
        """Load configuration from file and environment variables."""
        # Start with defaults

        self._data = copy.deepcopy(self.DEFAULT_CONFIG)
        
        # Load from TOML file if it exists
        if self.config_path and self.config_path.exists():
            try:
                with self.config_path.open("rb") as f:
                    file_config = tomli.load(f)
                self._merge_dict(self._data, file_config)
            except tomli.TOMLDecodeError as e:
                raise ConfigError(f"Invalid TOML syntax in {self.config_path}: {e}") from e
            except OSError as e:
                raise ConfigError(f"Unable to read configuration file: {e}") from e
        
        # Override with environment variables
        self._override_with_env()
        
        # Validate configuration
        self._validate()
    
    def _merge_dict(self, base: dict, overlay: dict) -> None:
        """Recursively merge overlay dictionary into base dictionary."""
        for key, value in overlay.items():
            if key in base:
                if isinstance(base[key], dict) and isinstance(value, dict):
                    self._merge_dict(base[key], value)
                else:
                    base[key] = value
            else:
                base[key] = value
    
    def _override_with_env(self):
        """Override configuration with environment variables."""
        # General
        if "DEV_THEME" in os.environ:
            self._data["general"]["theme"] = os.environ["DEV_THEME"]
        if "DEV_LOG_LEVEL" in os.environ:
            self._data["general"]["log_level"] = os.environ["DEV_LOG_LEVEL"]
        
        # Refresh intervals
        for key in ["github", "leetcode", "weather", "media", "git", "system"]:
            env_var = f"DEV_REFRESH_{key.upper()}"
            if env_var in os.environ:
                try:
                    self._data["refresh"][key] = int(os.environ[env_var])
                except ValueError:
                    pass
        
        # GitHub
        if "DEV_GITHUB_USERNAME" in os.environ:
            self._data["github"]["username"] = os.environ["DEV_GITHUB_USERNAME"]
        if "DEV_GITHUB_TOKEN" in os.environ:
            self._data["github"]["access_token"] = os.environ["DEV_GITHUB_TOKEN"]
        
        # LeetCode
        if "DEV_LEETCODE_USERNAME" in os.environ:
            self._data["leetcode"]["username"] = os.environ["DEV_LEETCODE_USERNAME"]
        
        # Weather
        if "DEV_WEATHER_API_KEY" in os.environ:
            self._data["weather"]["api_key"] = os.environ["DEV_WEATHER_API_KEY"]
        if "DEV_WEATHER_CITY" in os.environ:
            self._data["weather"]["city"] = os.environ["DEV_WEATHER_CITY"]
        if "DEV_WEATHER_UNITS" in os.environ:
            self._data["weather"]["units"] = os.environ["DEV_WEATHER_UNITS"]
        
        # Music
        if "DEV_MUSIC_PLAYER" in os.environ:
            self._data["music"]["player"] = os.environ["DEV_MUSIC_PLAYER"]
    
    def _validate(self):
        """Validate configuration values."""
        # Check refresh intervals
        for key, value in self._data["refresh"].items():
            if not isinstance(value, int) or value < 0:
                raise ConfigError(f"Refresh interval '{key}' must be a non-negative integer.")
        
        # Check optional fields
        if self._data["github"]["access_token"] and len(self._data["github"]["access_token"]) < 40:
            raise ConfigError("GitHub access token seems invalid (too short).")
        
        if self._data["weather"]["api_key"] and len(self._data["weather"]["api_key"]) < 10:
            raise ConfigError("Weather API key seems invalid (too short).")
        
        # Check log level
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self._data["general"]["log_level"].upper() not in log_levels:
            raise ConfigError(f"Invalid log level. Must be one of: {', '.join(log_levels)}")
        
        # Check units
        if self._data["weather"]["units"] not in ["metric", "imperial"]:
            raise ConfigError("Weather units must be 'metric' or 'imperial'.")
    
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a specific configuration value."""
        return self._data.get(section, {}).get(key, default)
    
# Singleton instance
_config: Optional[Config] = None


def get_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """
    Get or create the global configuration instance.
    
    Args:
        config_path: Optional path to config file.
    
    Returns:
        The global Config instance.
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def reload_config() -> None:
    """Reload the configuration from disk."""
    global _config
    if _config:
        _config._load()


def clear_config() -> None:
    """Clear the global configuration instance."""
    global _config
    _config = None


