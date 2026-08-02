"""
Footer widget component for DevPulse Dashboard.
"""

from typing import Optional

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

try:
    from src.dashboard.icons import get_icon
    from src.dashboard.theme import ThemePalette, get_active_theme
except ImportError:
    from dashboard.icons import get_icon  # type: ignore
    from dashboard.theme import ThemePalette, get_active_theme  # type: ignore


def _make_resource_gauge(percentage: float, width: int = 8) -> str:
    """Generate a block progress bar string for CPU/RAM utilization."""
    percentage = max(0.0, min(100.0, percentage))
    filled = int((percentage / 100.0) * width)
    empty = width - filled
    return "█" * filled + "░" * empty


class FooterWidget:
    """Renders system metrics, visual resource gauges, version, and shortcut hints."""

    def __init__(self, theme: Optional[ThemePalette] = None):
        self.theme = theme or get_active_theme()

    def render(self) -> Panel:
        icon_cpu = get_icon("cpu")
        icon_mem = get_icon("memory")

        cpu_usage = 0.0
        mem_usage = 0.0

        if psutil is not None:
            try:
                cpu_usage = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                mem_usage = mem.percent
            except Exception:
                pass

        cpu_gauge = _make_resource_gauge(cpu_usage, width=8)
        ram_gauge = _make_resource_gauge(mem_usage, width=8)

        grid = Table.grid(expand=True)
        grid.add_column(justify="left")
        grid.add_column(justify="center")
        grid.add_column(justify="right")

        grid.add_row(
            Text.assemble(
                (f"{icon_cpu} CPU ", self.theme.secondary),
                (f"{cpu_gauge} ", self.theme.success if cpu_usage < 80 else self.theme.error),
                (f"{cpu_usage:.1f}%  │  ", self.theme.secondary),
                (f"{icon_mem} RAM ", self.theme.secondary),
                (f"{ram_gauge} ", self.theme.warning if mem_usage > 70 else self.theme.success),
                (f"{mem_usage:.1f}%", self.theme.secondary),
            ),
            Text("DevPulse v0.1.0", style=f"bold {self.theme.primary}"),
            Text("Press Ctrl+C / [Q] to quit  •  [R] to refresh", style=self.theme.muted),
        )

        return Panel(
            grid,
            style=self.theme.muted,
            border_style=self.theme.border,
            padding=(0, 2),
        )
