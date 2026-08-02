"""
GeeksforGeeks widget component for DevPulse Dashboard.
"""

from typing import Optional
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

try:
    from src.dashboard.icons import get_icon
    from src.dashboard.theme import ThemePalette, get_active_theme
    from src.services.geeksforgeeks import GeeksforGeeksUserData
except ImportError:
    from dashboard.icons import get_icon  # type: ignore
    from dashboard.theme import ThemePalette, get_active_theme  # type: ignore
    from services.geeksforgeeks import GeeksforGeeksUserData  # type: ignore


def _make_progress_bar(count: int, max_count: int = 200, width: int = 16) -> str:
    """Generate a visual block progress bar string."""
    if max_count <= 0:
        filled = 0
    else:
        filled = min(width, int((count / max_count) * width))
    empty = width - filled
    return "█" * filled + "░" * empty


class GeeksforGeeksWidget:
    """Renders the GeeksforGeeks metrics widget with symmetrical layout."""

    def __init__(self, theme: Optional[ThemePalette] = None):
        self.theme = theme or get_active_theme()

    def render(self, gfg: Optional[GeeksforGeeksUserData]) -> Panel:
        icon_gfg = get_icon("geeksforgeeks")
        icon_user = get_icon("user")
        icon_trophy = get_icon("trophy")

        if not gfg:
            return Panel(
                Text("GeeksforGeeks metrics disabled or unavailable.", style=f"italic {self.theme.error}"),
                title=f"[bold green]{icon_gfg} GeeksforGeeks[/bold green]",
                border_style=self.theme.muted,
            )

        content_table = Table.grid(expand=True)
        content_table.add_column()

        # Profile Overview Header
        name_display = f"{icon_user} {gfg.name} (@{gfg.username})" if gfg.name else f"{icon_user} @{gfg.username}"
        header_grid = Table.grid(expand=True)
        header_grid.add_column(justify="left")
        header_grid.add_column(justify="right")
        header_grid.add_row(
            Text(name_display, style=f"bold {self.theme.primary}"),
            Text(f"{icon_trophy} Score: {gfg.overall_coding_score}", style=f"bold {self.theme.success}"),
        )
        header_grid.add_row(
            Text(f"Institute: {gfg.institute_name}", style=self.theme.secondary),
            Text(f"Institute Rank: #{gfg.institute_rank}", style=f"bold {self.theme.warning}"),
        )
        content_table.add_row(header_grid)
        content_table.add_row(Text(""))

        # Solved Breakdown Grid
        solved_table = Table(
            show_header=True,
            header_style=f"bold {self.theme.success}",
            expand=True,
            box=None,
            padding=(0, 1),
        )
        solved_table.add_column("Difficulty")
        solved_table.add_column("Progress Bar")
        solved_table.add_column("Count", justify="right", style="bold")

        max_target = max(gfg.total_problems_solved, 200)

        solved_table.add_row(
            "School / Basic",
            Text(_make_progress_bar(gfg.school_solved, max_target // 2, width=16), style=self.theme.secondary),
            f"[{self.theme.secondary}]{gfg.school_solved}[/{self.theme.secondary}]",
        )
        solved_table.add_row(
            "Easy",
            Text(_make_progress_bar(gfg.easy_solved, max_target // 2, width=16), style=self.theme.success),
            f"[{self.theme.success}]{gfg.easy_solved}[/{self.theme.success}]",
        )
        solved_table.add_row(
            "Medium",
            Text(_make_progress_bar(gfg.medium_solved, max_target // 2, width=16), style=self.theme.warning),
            f"[{self.theme.warning}]{gfg.medium_solved}[/{self.theme.warning}]",
        )
        solved_table.add_row(
            "Hard",
            Text(_make_progress_bar(gfg.hard_solved, max_target // 4, width=16), style=self.theme.error),
            f"[{self.theme.error}]{gfg.hard_solved}[/{self.theme.error}]",
        )

        content_table.add_row(solved_table)

        return Panel(
            content_table,
            title=f"[bold bright_white]{icon_gfg} GeeksforGeeks[/bold bright_white] [dim](https://auth.geeksforgeeks.org/user/{gfg.username})[/dim]",
            border_style=self.theme.success,
            padding=(1, 2),
        )
