"""
Main renderer for DevPulse Dashboard using Rich.

Responsibilities:
- Receives DashboardData model and outputs formatted terminal renderables
- Grid panel columns for GitHub, LeetCode, Codeforces, and GeeksforGeeks
- Pure rendering pipeline: NO API calls, NO caching logic
"""

from typing import Optional
from rich.columns import Columns
from rich.console import Console

try:
    from src.dashboard.models import DashboardData
    from src.dashboard.theme import ThemePalette, get_active_theme
    from src.dashboard.widgets import (
        CodeforcesWidget,
        FooterWidget,
        GeeksforGeeksWidget,
        GitHubWidget,
        HeaderWidget,
        LeetCodeWidget,
    )
except ImportError:
    from dashboard.models import DashboardData  # type: ignore
    from dashboard.theme import ThemePalette, get_active_theme  # type: ignore
    from dashboard.widgets import (  # type: ignore
        CodeforcesWidget,
        FooterWidget,
        GeeksforGeeksWidget,
        GitHubWidget,
        HeaderWidget,
        LeetCodeWidget,
    )


class DashboardRenderer:
    """Orchestrates layout rendering for DashboardData."""

    def __init__(self, console: Optional[Console] = None, theme_name: Optional[str] = None):
        self.console = console or Console()
        self.theme = get_active_theme(theme_name)

        # Instantiate modular widget renderers
        self.header_widget = HeaderWidget(self.theme)
        self.github_widget = GitHubWidget(self.theme)
        self.leetcode_widget = LeetCodeWidget(self.theme)
        self.codeforces_widget = CodeforcesWidget(self.theme)
        self.geeksforgeeks_widget = GeeksforGeeksWidget(self.theme)
        self.footer_widget = FooterWidget(self.theme)

    def render_layout(self, data: DashboardData) -> Columns:
        """Construct renderable layout grid for Live or static printing."""
        header_panel = self.header_widget.render(data)
        gh_panel = self.github_widget.render(data.github)
        lc_panel = self.leetcode_widget.render(data.leetcode)
        cf_panel = self.codeforces_widget.render(data.codeforces)
        gfg_panel = self.geeksforgeeks_widget.render(data.geeksforgeeks)
        footer_panel = self.footer_widget.render()

        row1_columns = Columns([gh_panel, lc_panel], equal=True, expand=True)
        row2_columns = Columns([cf_panel, gfg_panel], equal=True, expand=True)

        return Columns(
            [header_panel, row1_columns, row2_columns, footer_panel],
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
        cf_panel = self.codeforces_widget.render(data.codeforces)
        gfg_panel = self.geeksforgeeks_widget.render(data.geeksforgeeks)
        footer_panel = self.footer_widget.render()

        row1_columns = Columns([gh_panel, lc_panel], equal=True, expand=True)
        row2_columns = Columns([cf_panel, gfg_panel], equal=True, expand=True)

        self.console.print()
        self.console.print(header_panel)
        self.console.print(row1_columns)
        self.console.print(row2_columns)
        self.console.print(footer_panel)
        self.console.print()
