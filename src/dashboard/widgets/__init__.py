"""
Modular UI Widget Components for DevPulse.
"""

try:
    from src.dashboard.widgets.header import HeaderWidget
    from src.dashboard.widgets.github import GitHubWidget
    from src.dashboard.widgets.leetcode import LeetCodeWidget
    from src.dashboard.widgets.footer import FooterWidget
except ImportError:
    from dashboard.widgets.header import HeaderWidget  # type: ignore
    from dashboard.widgets.github import GitHubWidget  # type: ignore
    from dashboard.widgets.leetcode import LeetCodeWidget  # type: ignore
    from dashboard.widgets.footer import FooterWidget  # type: ignore

__all__ = [
    "HeaderWidget",
    "GitHubWidget",
    "LeetCodeWidget",
    "FooterWidget",
]
