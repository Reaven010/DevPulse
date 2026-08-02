"""
Codeforces widget component for DevPulse Dashboard.
"""

from typing import Optional
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

try:
    from src.dashboard.icons import get_icon, get_language_color, get_language_dot
    from src.dashboard.theme import ThemePalette, get_active_theme
    from src.services.codeforces import CodeforcesUserData
except ImportError:
    from dashboard.icons import get_icon, get_language_color, get_language_dot  # type: ignore
    from dashboard.theme import ThemePalette, get_active_theme  # type: ignore
    from services.codeforces import CodeforcesUserData  # type: ignore


class CodeforcesWidget:
    """Renders the Codeforces metrics widget with symmetrical layout."""

    def __init__(self, theme: Optional[ThemePalette] = None):
        self.theme = theme or get_active_theme()

    def render(self, cf: Optional[CodeforcesUserData]) -> Panel:
        icon_cf = get_icon("codeforces")
        icon_user = get_icon("user")
        icon_star = get_icon("star")
        icon_check = get_icon("check")

        if not cf:
            return Panel(
                Text("Codeforces metrics disabled or unavailable.", style=f"italic {self.theme.error}"),
                title=f"[bold cyan]{icon_cf} Codeforces[/bold cyan]",
                border_style=self.theme.muted,
            )

        content_table = Table.grid(expand=True)
        content_table.add_column()

        # Profile Overview Header
        name_display = f"{icon_user} {cf.name} (@{cf.handle})" if cf.name else f"{icon_user} @{cf.handle}"
        header_grid = Table.grid(expand=True)
        header_grid.add_column(justify="left")
        header_grid.add_column(justify="right")
        header_grid.add_row(
            Text(name_display, style=f"bold {self.theme.primary}"),
            Text(f"Rank: {cf.rank}", style=f"bold {self.theme.secondary}"),
        )
        header_grid.add_row(
            Text(f"{icon_star} Rating: {cf.rating} (Max: {cf.max_rating})", style=f"bold {self.theme.warning}"),
            Text(f"Contribution: {cf.contribution:+d}", style=self.theme.secondary),
        )
        content_table.add_row(header_grid)
        content_table.add_row(Text(""))

        # Solved Summary & Progress
        stats_table = Table.grid(expand=True)
        stats_table.add_column(justify="left")
        stats_table.add_column(justify="right")
        stats_table.add_row(
            Text(f"Total Solved: {cf.solved_count}", style=f"bold {self.theme.success}"),
            Text(f"Max Rank: {cf.max_rank}", style=f"bold {self.theme.warning}"),
        )
        content_table.add_row(stats_table)
        content_table.add_row(Text(""))

        # Recent Submissions Table
        sub_table = Table(
            show_header=True,
            header_style=f"bold {self.theme.secondary}",
            expand=True,
            box=None,
            padding=(0, 1),
        )
        sub_table.add_column("Recent Accepted Problem", style=self.theme.primary)
        sub_table.add_column("Rating", justify="right", style=self.theme.warning)
        sub_table.add_column("Language")
        sub_table.add_column("Verdict", justify="right", style=f"bold {self.theme.success}")

        for sub in cf.recent_submissions[:3]:
            lang_style = get_language_color(sub.language)
            dot = get_language_dot(sub.language)
            rating_str = f"★ {sub.problem_rating}" if sub.problem_rating else "-"

            sub_table.add_row(
                sub.title,
                rating_str,
                Text(f"{dot} {sub.language}", style=lang_style),
                f"{icon_check} {sub.verdict}",
            )

        content_table.add_row(sub_table)

        return Panel(
            content_table,
            title=f"[bold bright_white]{icon_cf} Codeforces[/bold bright_white] [dim](https://codeforces.com/profile/{cf.handle})[/dim]",
            border_style=self.theme.secondary,
            padding=(1, 2),
        )
