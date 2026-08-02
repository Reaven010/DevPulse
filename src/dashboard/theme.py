"""
Theme engine and color palettes for DevPulse Dashboard.
"""

from dataclasses import dataclass
from typing import Dict, Optional

try:
    from src.common.config import get_config
except ImportError:
    from common.config import get_config  # type: ignore


@dataclass(frozen=True, slots=True)
class ThemePalette:
    """Color palette and styling specifications for terminal dashboard."""

    name: str
    primary: str
    secondary: str
    accent: str
    border: str
    success: str
    warning: str
    error: str
    muted: str
    panel_title: str
    table_header: str
    highlight: str


# Preset Themes
THEMES: Dict[str, ThemePalette] = {
    "github-dark": ThemePalette(
        name="github-dark",
        primary="bright_white",
        secondary="cyan",
        accent="blue",
        border="cyan",
        success="green",
        warning="yellow",
        error="red",
        muted="dim white",
        panel_title="bold bright_white",
        table_header="bold cyan",
        highlight="bold yellow",
    ),
    "catppuccin": ThemePalette(
        name="catppuccin",
        primary="bright_white",
        secondary="magenta",
        accent="blue",
        border="magenta",
        success="green",
        warning="yellow",
        error="red",
        muted="dim white",
        panel_title="bold magenta",
        table_header="bold magenta",
        highlight="bold yellow",
    ),
    "dracula": ThemePalette(
        name="dracula",
        primary="bright_white",
        secondary="magenta",
        accent="bright_magenta",
        border="bright_magenta",
        success="bright_green",
        warning="bright_yellow",
        error="bright_red",
        muted="dim white",
        panel_title="bold bright_magenta",
        table_header="bold bright_magenta",
        highlight="bold bright_yellow",
    ),
    "nord": ThemePalette(
        name="nord",
        primary="bright_white",
        secondary="cyan",
        accent="blue",
        border="blue",
        success="green",
        warning="yellow",
        error="red",
        muted="dim white",
        panel_title="bold blue",
        table_header="bold cyan",
        highlight="bold yellow",
    ),
    "tokyonight": ThemePalette(
        name="tokyonight",
        primary="bright_white",
        secondary="blue",
        accent="magenta",
        border="blue",
        success="green",
        warning="yellow",
        error="red",
        muted="dim white",
        panel_title="bold magenta",
        table_header="bold blue",
        highlight="bold yellow",
    ),
}


def get_active_theme(theme_name: Optional[str] = None) -> ThemePalette:
    """Retrieve ThemePalette by name or from application config."""
    if not theme_name:
        try:
            config = get_config()
            theme_name = config.get("general", "theme", "github-dark")
        except Exception:
            theme_name = "github-dark"

    return THEMES.get(theme_name, THEMES["github-dark"])
