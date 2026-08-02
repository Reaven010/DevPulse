"""
LeetCode widget component for DevPulse Dashboard.
"""

from typing import Optional
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

try:
    from src.dashboard.icons import get_icon, get_language_color, get_language_dot
    from src.dashboard.theme import ThemePalette, get_active_theme
    from src.services.leetcode import LeetCodeUserData
except ImportError:
    from dashboard.icons import get_icon, get_language_color, get_language_dot  # type: ignore
    from dashboard.theme import ThemePalette, get_active_theme  # type: ignore
    from services.leetcode import LeetCodeUserData  # type: ignore


def _make_progress_bar(count: int, max_count: int = 200, width: int = 16) -> str:
    """Generate a longer visual block progress bar string."""
    if max_count <= 0:
        filled = 0
    else:
        filled = min(width, int((count / max_count) * width))
    empty = width - filled
    return "█" * filled + "░" * empty


class LeetCodeWidget:
    """Renders the LeetCode metrics widget with symmetrical layout and progress bars."""

    def __init__(self, theme: Optional[ThemePalette] = None):
        self.theme = theme or get_active_theme()

    def render(self, lc: Optional[LeetCodeUserData]) -> Panel:
        icon_lc = get_icon("leetcode")
        icon_user = get_icon("user")
        icon_check = get_icon("check")

        if not lc:
            return Panel(
                Text("LeetCode metrics disabled or unavailable.", style=f"italic {self.theme.error}"),
                title=f"[bold yellow]{icon_lc} LeetCode[/bold yellow]",
                border_style=self.theme.muted,
            )

        content_table = Table.grid(expand=True)
        content_table.add_column()

        # Profile Overview Header
        name_display = f"{icon_user} {lc.name} (@{lc.username})" if lc.name else f"{icon_user} @{lc.username}"
        header_grid = Table.grid(expand=True)
        header_grid.add_column(justify="left")
        header_grid.add_column(justify="right")
        header_grid.add_row(
            Text(name_display, style=f"bold {self.theme.primary}"),
            Text(f"Global Rank: #{lc.ranking:,}", style=f"bold {self.theme.secondary}"),
        )

        if lc.contest_stats:
            cs = lc.contest_stats
            header_grid.add_row(
                Text(f"Contest Rating: {cs.rating} (Top {cs.top_percentage}%)", style=f"bold {self.theme.success}"),
                Text(f"Attended: {cs.attended_contests}", style=self.theme.secondary),
            )
        content_table.add_row(header_grid)
        content_table.add_row(Text(""))

        # Solved Problems Grid with Longer Visual Progress Bars
        st = lc.solved_stats
        max_target = max(st.total_solved, 300)

        solved_table = Table(
            show_header=True,
            header_style=f"bold {self.theme.warning}",
            expand=True,
            box=None,
            padding=(0, 1),
        )
        solved_table.add_column("Difficulty")
        solved_table.add_column("Progress Bar")
        solved_table.add_column("Count", justify="right", style="bold")

        solved_table.add_row(
            "Easy",
            Text(_make_progress_bar(st.easy_solved, max_target // 2, width=16), style=self.theme.success),
            f"[{self.theme.success}]{st.easy_solved}[/{self.theme.success}]",
        )
        solved_table.add_row(
            "Medium",
            Text(_make_progress_bar(st.medium_solved, max_target // 2, width=16), style=self.theme.warning),
            f"[{self.theme.warning}]{st.medium_solved}[/{self.theme.warning}]",
        )
        solved_table.add_row(
            "Hard",
            Text(_make_progress_bar(st.hard_solved, max_target // 4, width=16), style=self.theme.error),
            f"[{self.theme.error}]{st.hard_solved}[/{self.theme.error}]",
        )

        content_table.add_row(solved_table)
        content_table.add_row(Text(""))

        # Recent Submissions Table
        sub_table = Table(
            show_header=True,
            header_style=f"bold {self.theme.warning}",
            expand=True,
            box=None,
            padding=(0, 1),
        )
        sub_table.add_column("Recent Accepted Problem", style=self.theme.primary)
        sub_table.add_column("Language")
        sub_table.add_column("Status", justify="right", style=f"bold {self.theme.success}")

        for sub in lc.recent_submissions[:3]:
            lang_style = get_language_color(sub.language)
            dot = get_language_dot(sub.language)
            sub_table.add_row(
                sub.title,
                Text(f"{dot} {sub.language}", style=lang_style),
                f"{icon_check} {sub.status}",
            )

        content_table.add_row(sub_table)

        return Panel(
            content_table,
            title=f"[bold bright_white]{icon_lc} LeetCode[/bold bright_white] [dim](https://leetcode.com/{lc.username})[/dim]",
            border_style=self.theme.warning,
            padding=(1, 2),
        )
