"""Unit tests for dashboard aggregation and rendering layer."""

from datetime import datetime, timezone
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.common.cache import clear_global_cache_instance
from src.dashboard.dashboard_service import (
    DashboardService,
    SERVICE_REGISTRY,
    fetch_dashboard_data,
    shutdown_dashboard_service,
)
from src.dashboard.icons import get_icon, get_language_color, is_utf8_supported, ICONS, ASCII_FALLBACKS
from src.dashboard.models import DashboardData
from src.dashboard.renderer import DashboardRenderer
from src.dashboard.theme import get_active_theme, THEMES
from src.dashboard.widgets import HeaderWidget, GitHubWidget, LeetCodeWidget, FooterWidget
from src.services.github import GitHubUserData, GitHubRepository, shutdown_github_service
from src.services.leetcode import (
    LeetCodeUserData,
    LeetCodeSolvedStats,
    LeetCodeContestStats,
    LeetCodeSubmission,
    shutdown_leetcode_service,
)


@pytest.fixture(autouse=True)
def cleanup():
    shutdown_dashboard_service()
    clear_global_cache_instance()
    yield
    shutdown_dashboard_service()
    clear_global_cache_instance()


def test_icons_and_language_colors():
    assert get_icon("bolt") is not None
    assert get_icon("bolt", fallback_ascii=True) == "*"
    assert get_language_color("python") == "bold yellow"
    assert get_language_color("c++") == "bold blue"
    assert get_language_color("unknown_lang") == "magenta"


def test_theme_properties():
    theme = get_active_theme("dracula")
    assert theme.name == "dracula"
    assert theme.panel_title == "bold bright_magenta"
    assert theme.table_header == "bold bright_magenta"


@patch("src.dashboard.dashboard_service.get_github_data")
@patch("src.dashboard.dashboard_service.get_leetcode_data")
def test_dashboard_service_aggregation(mock_lc, mock_gh):
    mock_gh.return_value = GitHubUserData(
        username="octocat",
        name="The Octocat",
        avatar_url="https://github.com/avatar.png",
        html_url="https://github.com/octocat",
        bio="Mascot",
        public_repos=10,
        followers=500,
        following=2,
        recent_repo_stars=150,
        recent_repos=(
            GitHubRepository("demo", "octocat/demo", "https://...", "desc", 150, 20, "Python", "2026-08-01"),
        ),
        recent_events_count=5,
    )

    mock_lc.return_value = LeetCodeUserData(
        username="sayujya_tiwari",
        name="Sayujya Tiwari",
        avatar_url="https://leetcode.com/avatar.png",
        ranking=40000,
        solved_stats=LeetCodeSolvedStats(total_solved=300, easy_solved=100, medium_solved=150, hard_solved=50),
        contest_stats=LeetCodeContestStats(rating=1820.5, global_ranking=10000, attended_contests=20, top_percentage=5.0),
        recent_submissions=(
            LeetCodeSubmission("Two Sum", "two-sum", 1754160000, "Accepted", "python3"),
        ),
    )

    with patch.dict(SERVICE_REGISTRY, {"github": mock_gh, "leetcode": mock_lc}):
        service = DashboardService()
        data = service.fetch()

        assert isinstance(data, DashboardData)
        assert isinstance(data.timestamp, datetime)
        assert data.github is not None
        assert data.github.username == "octocat"
        assert data.leetcode is not None
        assert data.leetcode.username == "sayujya_tiwari"
        assert data.leetcode.solved_stats.total_solved == 300

        service.close()


def test_modular_widgets():
    mock_data = DashboardData(
        timestamp=datetime.now(timezone.utc),
        github=GitHubUserData(
            username="octocat",
            name="The Octocat",
            avatar_url="",
            html_url="https://github.com/octocat",
            bio="Mascot",
            public_repos=5,
            followers=100,
            following=10,
            recent_repo_stars=50,
            recent_repos=(
                GitHubRepository("demo", "octocat/demo", "https://...", "desc", 50, 5, "Python", "2026-08-01"),
            ),
            recent_events_count=2,
        ),
        leetcode=LeetCodeUserData(
            username="sayujya_tiwari",
            name="Sayujya Tiwari",
            avatar_url="",
            ranking=1000,
            solved_stats=LeetCodeSolvedStats(total_solved=100, easy_solved=50, medium_solved=40, hard_solved=10),
            contest_stats=None,
            recent_submissions=(),
        ),
    )

    theme = get_active_theme("tokyonight")
    header_w = HeaderWidget(theme)
    gh_w = GitHubWidget(theme)
    lc_w = LeetCodeWidget(theme)
    footer_w = FooterWidget(theme)

    assert header_w.render(mock_data) is not None
    assert gh_w.render(mock_data.github) is not None
    assert lc_w.render(mock_data.leetcode) is not None
    assert footer_w.render() is not None


def test_renderer_pipeline_and_layout():
    mock_data = DashboardData(timestamp=datetime.now(timezone.utc))
    renderer = DashboardRenderer(theme_name="nord")
    assert renderer.theme.name == "nord"
    layout = renderer.render_layout(mock_data)
    assert layout is not None
    renderer.render(mock_data)
