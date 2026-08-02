"""Unit tests for GitHub service module."""

import tempfile
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.common.cache import CacheManager, clear_global_cache_instance
from src.services.github import (
    GitHubRepository,
    GitHubService,
    GitHubUserData,
    get_github_data,
    shutdown_github_service,
)


@pytest.fixture(autouse=True)
def reset_service_and_cache():
    shutdown_github_service()
    clear_global_cache_instance()
    yield
    shutdown_github_service()
    clear_global_cache_instance()


@patch.object(requests.Session, "get")
def test_github_service_api_fetch_and_cache(mock_get):
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_user_resp = MagicMock()
        mock_user_resp.status_code = 200
        mock_user_resp.json.return_value = {
            "login": "octocat",
            "name": "The Octocat",
            "avatar_url": "https://github.com/images/error/octocat_happy.gif",
            "html_url": "https://github.com/octocat",
            "bio": "GitHub mascot",
            "public_repos": 8,
            "followers": 1000,
            "following": 9,
        }

        mock_repos_resp = MagicMock()
        mock_repos_resp.status_code = 200
        mock_repos_resp.json.return_value = [
            {
                "name": "Hello-World",
                "full_name": "octocat/Hello-World",
                "html_url": "https://github.com/octocat/Hello-World",
                "description": "My first repo",
                "stargazers_count": 1500,
                "forks_count": 500,
                "language": "C",
                "updated_at": "2026-08-01T12:00:00Z",
            }
        ]

        mock_events_resp = MagicMock()
        mock_events_resp.status_code = 200
        mock_events_resp.json.return_value = [{"id": "1"}, {"id": "2"}]

        def side_effect(url, **kwargs):
            if "/repos" in url:
                return mock_repos_resp
            elif "/events" in url:
                return mock_events_resp
            return mock_user_resp

        mock_get.side_effect = side_effect

        service = GitHubService()
        service.cache = CacheManager(cache_dir=tmpdir)

        data = service.get_user_data(username="octocat")

        assert data is not None
        assert isinstance(data, GitHubUserData)
        assert data.username == "octocat"
        assert data.name == "The Octocat"
        assert data.public_repos == 8
        assert data.recent_repo_stars == 1500
        assert len(data.recent_repos) == 1
        assert isinstance(data.recent_repos[0], GitHubRepository)
        assert data.recent_repos[0].name == "Hello-World"

        # Immutability check
        with pytest.raises(AttributeError):
            data.username = "new_user"  # type: ignore

        # Second call uses cache
        mock_get.reset_mock()
        cached_data = service.get_user_data(username="octocat")
        assert cached_data == data
        mock_get.assert_not_called()

        service.close()


@patch.object(requests.Session, "get")
def test_github_service_stale_cache_fallback_on_error(mock_get):
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheManager(cache_dir=tmpdir)
        cache.set(
            "github_profile_testuser",
            {"login": "testuser", "name": "Test User", "public_repos": 5},
        )
        cache.set("github_repos_testuser", [])
        cache.set("github_events_testuser", [])

        mock_get.side_effect = requests.exceptions.ConnectionError("Network down")

        service = GitHubService()
        service.cache = cache

        # Fallback to stale cache
        data = service.get_user_data(username="testuser", force_refresh=True)
        assert data is not None
        assert data.username == "testuser"
        assert data.public_repos == 5

        service.close()
