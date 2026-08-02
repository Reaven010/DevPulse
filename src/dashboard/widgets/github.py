"""
GitHub widget component for DevPulse Dashboard.
"""

from typing import Optional
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

try:
    from src.dashboard.icons import get_icon, get_language_color, get_language_dot
    from src.dashboard.theme import ThemePalette, get_active_theme
    from src.services.github import GitHubUserData
except ImportError:
    from dashboard.icons import get_icon, get_language_color, get_language_dot  # type: ignore
    from dashboard.theme import ThemePalette, get_active_theme  # type: ignore
    from services.github import GitHubUserData  # type: ignore


class GitHubWidget:
    """Renders the GitHub metrics widget with symmetrical layout."""

    def __init__(self, theme: Optional[ThemePalette] = None):
        self.theme = theme or get_active_theme()

    def render(self, gh: Optional[GitHubUserData]) -> Panel:
        icon_gh = get_icon("github")
        icon_user = get_icon("user")
        icon_star = get_icon("star")
        icon_fork = get_icon("fork")

        if not gh:
            return Panel(
                Text("GitHub metrics disabled or unavailable.", style=f"italic {self.theme.error}"),
                title=f"[bold white]{icon_gh} GitHub[/bold white]",
                border_style=self.theme.muted,
            )

        content_table = Table.grid(expand=True)
        content_table.add_column()

        # Profile Header
        name_display = f"{icon_user} {gh.name} (@{gh.username})" if gh.name else f"{icon_user} @{gh.username}"
        header_grid = Table.grid(expand=True)
        header_grid.add_column(justify="left")
        header_grid.add_column(justify="right")
        header_grid.add_row(
            Text(name_display, style=f"bold {self.theme.primary}"),
            Text(f"{icon_star} Stars (Recent): {gh.recent_repo_stars}", style=f"bold {self.theme.warning}"),
        )
        content_table.add_row(header_grid)

        if gh.bio:
            content_table.add_row(Text(f'"{gh.bio}"', style=f"italic {self.theme.muted}"))

        content_table.add_row(
            Text(
                f"Public Repos: {gh.public_repos}  •  Followers: {gh.followers}  •  Following: {gh.following}",
                style=self.theme.secondary,
            )
        )
        content_table.add_row(Text(""))

        # Repositories Table
        repo_table = Table(
            show_header=True,
            header_style=f"bold {self.theme.accent}",
            expand=True,
            box=None,
            padding=(0, 1),
        )
        repo_table.add_column("Recent Repository", style=self.theme.primary)
        repo_table.add_column("Language")
        repo_table.add_column("Stars", justify="right", style=self.theme.warning)
        repo_table.add_column("Forks", justify="right", style=self.theme.secondary)

        for repo in gh.recent_repos[:4]:
            lang = repo.language or "Plain Text"
            lang_style = get_language_color(repo.language)
            dot = get_language_dot(repo.language)

            repo_table.add_row(
                repo.name,
                Text(f"{dot} {lang}", style=lang_style),
                f"{icon_star} {repo.stars}",
                f"{icon_fork} {repo.forks}",
            )

        content_table.add_row(repo_table)

        return Panel(
            content_table,
            title=f"[bold bright_white]{icon_gh} GitHub[/bold bright_white] [dim]({gh.html_url})[/dim]",
            border_style=self.theme.accent,
            padding=(1, 2),
        )
