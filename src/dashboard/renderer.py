"""
Main renderer for DevPulse Dashboard using Rich.

Responsibilities:
- Receives DashboardData model and outputs formatted terminal renderables
- Side-by-side grid panels, header banner, and footer metrics widget
- Pure rendering pipeline: NO API calls, NO caching logic
"""

from typing import Optional
from rich.columns import Columns
from rich.console import Console

try:
    from src.dashboard.models import DashboardData
    from src.dashboard.theme import ThemePalette, get_active_theme
    from src.dashboard.widgets import FooterWidget, GitHubWidget, HeaderWidget, LeetCodeWidget
except ImportError:
    from dashboard.models import DashboardData  # type: ignore
    from dashboard.theme import ThemePalette, get_active_theme  # type: ignore
    from dashboard.widgets import FooterWidget, GitHubWidget, HeaderWidget, LeetCodeWidget  # type: ignore


class DashboardRenderer:
    """Orchestrates layout rendering for DashboardData."""

    def __init__(self, console: Optional[Console] = None, theme_name: Optional[str] = None):
        self.console = console or Console()
        self.theme = get_active_theme(theme_name)

        # Instantiate modular widget renderers
        self.header_widget = HeaderWidget(self.theme)
        self.github_widget = GitHubWidget(self.theme)
        self.leetcode_widget = LeetCodeWidget(self.theme)
        self.footer_widget = FooterWidget(self.theme)

    def render_layout(self, data: DashboardData) -> Columns:
        """Construct renderable layout grid for Live or static printing."""
        header_panel = self.header_widget.render(data)
        gh_panel = self.github_widget.render(data.github)
        lc_panel = self.leetcode_widget.render(data.leetcode)
        footer_panel = self.footer_widget.render()

        # Side-by-side cards for GitHub and LeetCode
        cards_columns = Columns([gh_panel, lc_panel], equal=True, expand=True)

        return Columns(
            [header_panel, cards_columns, footer_panel],
            equal=False,
            expand=True,
        )

    def render(self, data: DashboardData) -> None:
        """
        Pure rendering pipeline.

        Args:
            data: DashboardData model containing pre-aggregated metrics.
        """
        header_panel = self.header_widget.render(data)
        gh_panel = self.github_widget.render(data.github)
        lc_panel = self.leetcode_widget.render(data.leetcode)
        footer_panel = self.footer_widget.render()

        cards_columns = Columns([gh_panel, lc_panel], equal=True, expand=True)

        self.console.print()
        self.console.print(header_panel)
        self.console.print(cards_columns)
        self.console.print(footer_panel)
        self.console.print()
