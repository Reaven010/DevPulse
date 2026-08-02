"""
Header widget component for DevPulse Dashboard.
"""

from typing import Optional
from rich.panel import Panel
from rich.text import Text

try:
    from src.dashboard.icons import get_icon
    from src.dashboard.models import DashboardData
    from src.dashboard.theme import ThemePalette, get_active_theme
except ImportError:
    from dashboard.icons import get_icon  # type: ignore
    from dashboard.models import DashboardData  # type: ignore
    from dashboard.theme import ThemePalette, get_active_theme  # type: ignore


class HeaderWidget:
    """Renders the top banner header widget."""

    def __init__(self, theme: Optional[ThemePalette] = None):
        self.theme = theme or get_active_theme()

    def render(self, data: DashboardData) -> Panel:
        bolt = get_icon("bolt")
        title_text = Text(f"{bolt}   DEVPULSE   {bolt}", style=f"bold {self.theme.secondary}")
        subtitle_text = Text(
            f"Refreshed: {data.formatted_time} ({data.relative_time})  •  Theme: {self.theme.name}  •  Status: ONLINE",
            style=self.theme.muted,
        )

        content = Text.assemble(title_text, "\n", subtitle_text, justify="center")
        return Panel(
            content,
            style=f"bold {self.theme.secondary}",
            border_style=self.theme.border,
            padding=(0, 2),
        )
