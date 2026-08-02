"""Unit tests for Codeforces service."""

import pytest
from unittest.mock import MagicMock, patch

from src.common.cache import clear_global_cache_instance
from src.services.codeforces import CodeforcesService, get_codeforces_data, shutdown_codeforces_service


@pytest.fixture(autouse=True)
def cleanup():
    shutdown_codeforces_service()
    clear_global_cache_instance()
    yield
    shutdown_codeforces_service()
    clear_global_cache_instance()


@patch("src.services.codeforces.requests.Session.get")
def test_fetch_user_data_success(mock_get):
    # Mock user.info response
    mock_info = MagicMock()
    mock_info.status_code = 200
    mock_info.json.return_value = {
        "status": "OK",
        "result": [
            {
                "handle": "Tourist",
                "firstName": "Gennady",
                "lastName": "Korotkevich",
                "rating": 3850,
                "maxRating": 3850,
                "rank": "legendary grandmaster",
                "maxRank": "legendary grandmaster",
                "titlePhoto": "https://avatar.png",
                "contribution": 100,
            }
        ],
    }

    # Mock user.status response
    mock_status = MagicMock()
    mock_status.status_code = 200
    mock_status.json.return_value = {
        "status": "OK",
        "result": [
            {
                "verdict": "OK",
                "programmingLanguage": "GNU C++20",
                "creationTimeSeconds": 1754160000,
                "problem": {"name": "Watermelon", "index": "A", "contestId": 4, "rating": 800},
            }
        ],
    }

    mock_get.side_effect = [mock_info, mock_status]

    service = CodeforcesService()
    data = service.fetch_user_data("Tourist", force_refresh=True)

    assert data is not None
    assert data.handle == "Tourist"
    assert data.rating == 3850
    assert data.rank == "Legendary Grandmaster"
    assert len(data.recent_submissions) == 1
    assert data.recent_submissions[0].title == "Watermelon"
