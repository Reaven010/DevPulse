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
from src.dashboard.widgets import (
    CodeforcesWidget,
    FooterWidget,
    GeeksforGeeksWidget,
    GitHubWidget,
    HeaderWidget,
    LeetCodeWidget,
)
from src.services.codeforces import CodeforcesUserData, CodeforcesSubmission, shutdown_codeforces_service
from src.services.geeksforgeeks import GeeksforGeeksUserData, shutdown_geeksforgeeks_service
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
@patch("src.dashboard.dashboard_service.get_codeforces_data")
@patch("src.dashboard.dashboard_service.get_geeksforgeeks_data")
def test_dashboard_service_aggregation(mock_gfg, mock_cf, mock_lc, mock_gh):
    mock_gh.return_value = GitHubUserData(
        username="octocat",
        name="The Octocat",
        avatar_url="",
        html_url="",
        bio="",
        public_repos=10,
        followers=500,
        following=2,
        recent_repo_stars=150,
        recent_repos=(),
        recent_events_count=5,
    )

    mock_lc.return_value = LeetCodeUserData(
        username="sayujya_tiwari",
        name="Sayujya Tiwari",
        avatar_url="",
        ranking=40000,
        solved_stats=LeetCodeSolvedStats(300, 100, 150, 50),
        contest_stats=None,
        recent_submissions=(),
    )

    mock_cf.return_value = CodeforcesUserData(
        handle="Tourist",
        name="Gennady Korotkevich",
        rating=3850,
        max_rating=3850,
        rank="Legendary Grandmaster",
        max_rank="Legendary Grandmaster",
        avatar_url="",
        contribution=100,
        solved_count=2500,
        recent_submissions=(),
    )

    mock_gfg.return_value = GeeksforGeeksUserData(
        username="sayujya_tiwari",
        name="Sayujya Tiwari",
        profile_score=450,
        overall_coding_score=450,
        total_problems_solved=120,
        monthly_coding_score=50,
        institute_name="University",
        institute_rank="12",
        easy_solved=60,
        medium_solved=40,
        hard_solved=10,
        school_solved=10,
    )

    with patch.dict(
        SERVICE_REGISTRY,
        {"github": mock_gh, "leetcode": mock_lc, "codeforces": mock_cf, "geeksforgeeks": mock_gfg},
    ):
        service = DashboardService()
        data = service.fetch()

        assert isinstance(data, DashboardData)
        assert data.github is not None
        assert data.leetcode is not None
        assert data.codeforces is not None
        assert data.geeksforgeeks is not None
        assert data.codeforces.handle == "Tourist"
        assert data.geeksforgeeks.overall_coding_score == 450

        service.close()


def test_all_modular_widgets():
    mock_data = DashboardData(
        timestamp=datetime.now(timezone.utc),
        github=None,
        leetcode=None,
        codeforces=None,
        geeksforgeeks=None,
    )

    theme = get_active_theme("tokyonight")
    header_w = HeaderWidget(theme)
    gh_w = GitHubWidget(theme)
    lc_w = LeetCodeWidget(theme)
    cf_w = CodeforcesWidget(theme)
    gfg_w = GeeksforGeeksWidget(theme)
    footer_w = FooterWidget(theme)

    assert header_w.render(mock_data) is not None
    assert gh_w.render(mock_data.github) is not None
    assert lc_w.render(mock_data.leetcode) is not None
    assert cf_w.render(mock_data.codeforces) is not None
    assert gfg_w.render(mock_data.geeksforgeeks) is not None
    assert footer_w.render() is not None


def test_renderer_pipeline_and_layout():
    mock_data = DashboardData(timestamp=datetime.now(timezone.utc))
    renderer = DashboardRenderer(theme_name="nord")
    assert renderer.theme.name == "nord"
    layout = renderer.render_layout(mock_data)
    assert layout is not None
    renderer.render(mock_data)
