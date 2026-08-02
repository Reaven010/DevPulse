"""Unit tests for GeeksforGeeks service."""

import pytest
from unittest.mock import MagicMock, patch

from src.common.cache import clear_global_cache_instance
from src.services.geeksforgeeks import GeeksforGeeksService, get_geeksforgeeks_data, shutdown_geeksforgeeks_service


@pytest.fixture(autouse=True)
def cleanup():
    shutdown_geeksforgeeks_service()
    clear_global_cache_instance()
    yield
    shutdown_geeksforgeeks_service()
    clear_global_cache_instance()


@patch("src.services.geeksforgeeks.requests.Session.get")
def test_fetch_gfg_user_data_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "info": {
            "userName": "sayujya_tiwari",
            "overallCodingScore": 450,
            "totalProblemsSolved": 120,
            "institute": "University",
            "instituteRank": "12",
        },
        "solvedStats": {
            "school": {"count": 10},
            "easy": {"count": 60},
            "medium": {"count": 40},
            "hard": {"count": 10},
        },
    }
    mock_get.return_value = mock_resp

    service = GeeksforGeeksService()
    data = service.fetch_user_data("sayujya_tiwari", force_refresh=True)

    assert data is not None
    assert data.username == "sayujya_tiwari"
    assert data.overall_coding_score == 450
    assert data.total_problems_solved == 120
    assert data.easy_solved == 60
    assert data.medium_solved == 40
