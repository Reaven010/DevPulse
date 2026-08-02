"""
Widget component renderers for DevPulse Dashboard.
"""

from typing import Optional
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

try:
    from src.dashboard.icons import get_icon
    from src.dashboard.models import DashboardData
    from src.dashboard.theme import ThemePalette, get_active_theme
    from src.services.github import GitHubUserData
    from src.services.leetcode import LeetCodeUserData
except ImportError:
    from dashboard.icons import get_icon  # type: ignore
    from dashboard.models import DashboardData  # type: ignore
    from dashboard.theme import ThemePalette, get_active_theme  # type: ignore
    from services.github import GitHubUserData  # type: ignore
    from services.leetcode import LeetCodeUserData  # type: ignore


class HeaderWidget:
    """Renders the top banner widget."""

    def __init__(self, theme: Optional[ThemePalette] = None):
        self.theme = theme or get_active_theme()

    def render(self, data: DashboardData) -> Panel:
        bolt = get_icon("bolt")
        title_text = Text(f"{bolt} DEVPULSE DEVELOPER DASHBOARD {bolt}", style=f"bold {self.theme.secondary}")
        subtitle_text = Text(
            f"Last Refreshed: {data.formatted_time}  |  Theme: {self.theme.name}  |  Status: ONLINE",
            style=self.theme.muted,
        )

        content = Text.assemble(title_text, "\n", subtitle_text, justify="center")
        return Panel(
            content,
            style=f"bold {self.theme.secondary}",
            border_style=self.theme.border,
            padding=(0, 2),
        )


class GitHubWidget:
    """Renders the GitHub metrics widget."""

    def __init__(self, theme: Optional[ThemePalette] = None):
        self.theme = theme or get_active_theme()

    def render(self, gh: Optional[GitHubUserData]) -> Panel:
        icon_gh = get_icon("github")
        icon_star = get_icon("star")
        icon_fork = get_icon("fork")

        if not gh:
            return Panel(
                Text("GitHub metrics disabled or unavailable.", style=f"italic {self.theme.error}"),
                title=f"[bold white]{icon_gh} GitHub[/bold white]",
                border_style=self.theme.muted,
            )

        # Profile Overview
        overview_table = Table.grid(expand=True)
        overview_table.add_column(justify="left")
        overview_table.add_column(justify="right")

        name_display = f"{gh.name} (@{gh.username})" if gh.name else f"@{gh.username}"
        overview_table.add_row(
            Text(name_display, style=f"bold {self.theme.primary}"),
            Text(f"{icon_star} {gh.recent_repo_stars} Recent Stars", style=f"bold {self.theme.warning}"),
        )
        if gh.bio:
            overview_table.add_row(Text(f'"{gh.bio}"', style=f"italic {self.theme.muted}"), Text(""))

        overview_table.add_row(
            Text(
                f"Public Repos: {gh.public_repos}  •  Followers: {gh.followers}  •  Following: {gh.following}",
                style=self.theme.secondary,
            ),
            Text(f"Activity Events: {gh.recent_events_count}", style=self.theme.success),
        )

        # Repositories Table
        repo_table = Table(
            show_header=True,
            header_style=f"bold {self.theme.accent}",
            expand=True,
            box=None,
            padding=(0, 1),
        )
        repo_table.add_column("Repository", style=self.theme.primary)
        repo_table.add_column("Language", style=self.theme.secondary)
        repo_table.add_column("Stars", justify="right", style=self.theme.warning)
        repo_table.add_column("Forks", justify="right", style=self.theme.secondary)

        for repo in gh.recent_repos[:4]:
            repo_table.add_row(
                repo.name,
                repo.language or "Plain Text",
                f"{icon_star} {repo.stars}",
                f"{icon_fork} {repo.forks}",
            )

        return Panel(
            Columns([overview_table, repo_table], equal=False, expand=True),
            title=f"[bold bright_white]{icon_gh} GitHub[/bold bright_white] [dim]({gh.html_url})[/dim]",
            border_style=self.theme.accent,
            padding=(1, 2),
        )


class LeetCodeWidget:
    """Renders the LeetCode metrics widget."""

    def __init__(self, theme: Optional[ThemePalette] = None):
        self.theme = theme or get_active_theme()

    def render(self, lc: Optional[LeetCodeUserData]) -> Panel:
        icon_lc = get_icon("leetcode")
        icon_check = get_icon("check")

        if not lc:
            return Panel(
                Text("LeetCode metrics disabled or unavailable.", style=f"italic {self.theme.error}"),
                title=f"[bold yellow]{icon_lc} LeetCode[/bold yellow]",
                border_style=self.theme.muted,
            )

        # Profile Overview
        overview_table = Table.grid(expand=True)
        overview_table.add_column(justify="left")
        overview_table.add_column(justify="right")

        name_display = f"{lc.name} (@{lc.username})" if lc.name else f"@{lc.username}"
        overview_table.add_row(
            Text(name_display, style=f"bold {self.theme.primary}"),
            Text(f"Global Rank: #{lc.ranking:,}", style=f"bold {self.theme.secondary}"),
        )

        if lc.contest_stats:
            cs = lc.contest_stats
            overview_table.add_row(
                Text(f"Contest Rating: {cs.rating} (Top {cs.top_percentage}%)", style=f"bold {self.theme.success}"),
                Text(f"Contests Attended: {cs.attended_contests}", style=self.theme.secondary),
            )

        # Solved Problems Table
        st = lc.solved_stats
        solved_table = Table(
            show_header=True,
            header_style=f"bold {self.theme.warning}",
            expand=True,
            box=None,
            padding=(0, 1),
        )
        solved_table.add_column("Difficulty", style="bold")
        solved_table.add_column("Solved", justify="right", style="bold")

        solved_table.add_row("Total Solved", f"[bold {self.theme.secondary}]{st.total_solved}[/bold {self.theme.secondary}]")
        solved_table.add_row("Easy", f"[{self.theme.success}]{st.easy_solved}[/{self.theme.success}]")
        solved_table.add_row("Medium", f"[{self.theme.warning}]{st.medium_solved}[/{self.theme.warning}]")
        solved_table.add_row("Hard", f"[{self.theme.error}]{st.hard_solved}[/{self.theme.error}]")

        # Submissions Table
        sub_table = Table(
            show_header=True,
            header_style=f"bold {self.theme.warning}",
            expand=True,
            box=None,
            padding=(0, 1),
        )
        sub_table.add_column("Recent Accepted Problem", style=self.theme.primary)
        sub_table.add_column("Language", style=self.theme.secondary)
        sub_table.add_column("Status", justify="right", style=f"bold {self.theme.success}")

        for sub in lc.recent_submissions[:4]:
            sub_table.add_row(sub.title, sub.language, f"{icon_check} {sub.status}")

        return Panel(
            Columns([overview_table, solved_table, sub_table], equal=False, expand=True),
            title=f"[bold bright_white]{icon_lc} LeetCode[/bold bright_white] [dim](https://leetcode.com/{lc.username})[/dim]",
            border_style=self.theme.warning,
            padding=(1, 2),
        )
