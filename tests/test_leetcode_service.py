"""Unit tests for LeetCode service module."""

import tempfile
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.common.cache import CacheManager, clear_global_cache_instance
from src.services.leetcode import (
    LeetCodeContestStats,
    LeetCodeService,
    LeetCodeSolvedStats,
    LeetCodeSubmission,
    LeetCodeUserData,
    get_leetcode_data,
    shutdown_leetcode_service,
)


@pytest.fixture(autouse=True)
def reset_service_and_cache():
    shutdown_leetcode_service()
    clear_global_cache_instance()
    yield
    shutdown_leetcode_service()
    clear_global_cache_instance()


@patch.object(requests.Session, "post")
def test_leetcode_service_api_fetch_and_cache(mock_post):
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_profile_resp = MagicMock()
        mock_profile_resp.status_code = 200
        mock_profile_resp.json.return_value = {
            "data": {
                "matchedUser": {
                    "username": "testcoder",
                    "profile": {
                        "realName": "Test Coder",
                        "userAvatar": "https://leetcode.com/avatar/testcoder.png",
                        "ranking": 45000,
                    },
                    "submitStats": {
                        "acSubmissionNum": [
                            {"difficulty": "All", "count": 250},
                            {"difficulty": "Easy", "count": 100},
                            {"difficulty": "Medium", "count": 120},
                            {"difficulty": "Hard", "count": 30},
                        ]
                    },
                },
                "userContestRanking": {
                    "attendedContestsCount": 15,
                    "rating": 1785.4,
                    "globalRanking": 12000,
                    "topPercentage": 8.5,
                },
            }
        }

        mock_subs_resp = MagicMock()
        mock_subs_resp.status_code = 200
        mock_subs_resp.json.return_value = {
            "data": {
                "recentAcSubmissionList": [
                    {
                        "title": "Two Sum",
                        "titleSlug": "two-sum",
                        "timestamp": "1754160000",
                        "statusDisplay": "Accepted",
                        "lang": "python3",
                    }
                ]
            }
        }

        def side_effect(url, json, **kwargs):
            query = json.get("query", "")
            if "getRecentSubmissions" in query:
                return mock_subs_resp
            return mock_profile_resp

        mock_post.side_effect = side_effect

        service = LeetCodeService()
        service.cache = CacheManager(cache_dir=tmpdir)

        data = service.get_user_data(username="testcoder")

        assert data is not None
        assert isinstance(data, LeetCodeUserData)
        assert data.username == "testcoder"
        assert data.name == "Test Coder"
        assert data.ranking == 45000

        # Verify solved stats
        assert isinstance(data.solved_stats, LeetCodeSolvedStats)
        assert data.solved_stats.total_solved == 250
        assert data.solved_stats.easy_solved == 100
        assert data.solved_stats.medium_solved == 120
        assert data.solved_stats.hard_solved == 30

        # Verify contest stats
        assert isinstance(data.contest_stats, LeetCodeContestStats)
        assert data.contest_stats.rating == 1785.4
        assert data.contest_stats.attended_contests == 15

        # Verify recent submissions
        assert len(data.recent_submissions) == 1
        assert isinstance(data.recent_submissions[0], LeetCodeSubmission)
        assert data.recent_submissions[0].title == "Two Sum"
        assert data.recent_submissions[0].language == "python3"

        # Verify immutability
        with pytest.raises(AttributeError):
            data.username = "changed"  # type: ignore

        # Second call uses cache
        mock_post.reset_mock()
        cached_data = service.get_user_data(username="testcoder")
        assert cached_data == data
        mock_post.assert_not_called()

        service.close()


@patch.object(requests.Session, "post")
def test_leetcode_service_null_matched_user(mock_post):
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_null_resp = MagicMock()
        mock_null_resp.status_code = 200
        mock_null_resp.json.return_value = {
            "data": {
                "matchedUser": None,
                "userContestRanking": None,
            }
        }
        mock_post.return_value = mock_null_resp

        service = LeetCodeService()
        service.cache = CacheManager(cache_dir=tmpdir)

        data = service.get_user_data(username="nonexistent_user")
        assert data is None
        service.close()


@patch.object(requests.Session, "post")
def test_leetcode_service_stale_cache_fallback(mock_post):
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheManager(cache_dir=tmpdir)
        cache.set(
            "leetcode_profile_testcoder",
            {
                "matchedUser": {
                    "username": "testcoder",
                    "profile": {"realName": "Stale Coder", "ranking": 50000},
                    "submitStats": {
                        "acSubmissionNum": [
                            {"difficulty": "All", "count": 200},
                            {"difficulty": "Easy", "count": 80},
                            {"difficulty": "Medium", "count": 100},
                            {"difficulty": "Hard", "count": 20},
                        ]
                    },
                }
            },
        )
        cache.set("leetcode_submissions_testcoder", [])

        mock_post.side_effect = requests.exceptions.ConnectionError("Network unreachable")

        service = LeetCodeService()
        service.cache = cache

        # Fallback to stale cache
        data = service.get_user_data(username="testcoder", force_refresh=True)
        assert data is not None
        assert data.username == "testcoder"
        assert data.name == "Stale Coder"
        assert data.solved_stats.total_solved == 200

        service.close()
