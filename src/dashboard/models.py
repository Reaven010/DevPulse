"""
Aggregated data models for DevPulse Dashboard.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    from src.services.github import GitHubUserData
    from src.services.leetcode import LeetCodeUserData
except ImportError:
    from services.github import GitHubUserData  # type: ignore
    from services.leetcode import LeetCodeUserData  # type: ignore


@dataclass(frozen=True, slots=True)
class DashboardData:
    """Aggregated container holding data from all active services."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    github: Optional[GitHubUserData] = None
    leetcode: Optional[LeetCodeUserData] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def formatted_time(self) -> str:
        """Return human-readable local time string of aggregation timestamp."""
        local_dt = self.timestamp.astimezone()
        tz_name = local_dt.tzname() or "LOCAL"
        return local_dt.strftime(f"%H:%M:%S {tz_name}")

    @property
    def relative_time(self) -> str:
        """Return human-readable relative time (e.g., 'Just now', '5s ago')."""
        now = datetime.now(timezone.utc)
        diff_seconds = max(0, int((now - self.timestamp).total_seconds()))
        if diff_seconds < 5:
            return "Just now"
        elif diff_seconds < 60:
            return f"{diff_seconds}s ago"
        elif diff_seconds < 3600:
            return f"{diff_seconds // 60}m ago"
        else:
            return f"{diff_seconds // 3600}h ago"
