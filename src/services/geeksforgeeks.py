"""
GeeksforGeeks service module for DevPulse.

Responsibilities:
- Reads GeeksforGeeks username from config.py / config.toml
- Fetches user profile, overall coding score, problems solved by difficulty, and institute rank
- Uses cache.py for TTL caching
- Uses logger.py for activity logging
- Returns immutable, strongly-typed dataclasses
"""

from dataclasses import dataclass
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import threading

try:
    from src.common.cache import get_cache
    from src.common.config import get_config
    from src.common.logger import get_logger
except ImportError:
    from common.cache import get_cache  # type: ignore
    from common.config import get_config  # type: ignore
    from common.logger import get_logger  # type: ignore

logger = get_logger(__name__)

GFG_API_URL = "https://geeksforgeeks-api.vercel.app/user"
DEFAULT_TIMEOUT = (3, 10)
CACHE_TTL = 300  # 5 minutes


@dataclass(frozen=True, slots=True)
class GeeksforGeeksUserData:
    """Represents complete user metrics from GeeksforGeeks."""

    username: str
    name: str
    profile_score: int
    overall_coding_score: int
    total_problems_solved: int
    monthly_coding_score: int
    institute_name: str
    institute_rank: str
    easy_solved: int
    medium_solved: int
    hard_solved: int
    school_solved: int


class GeeksforGeeksService:
    """Service client for fetching GeeksforGeeks user profile statistics."""

    def __init__(self):
        self.config = get_config()
        self.cache = get_cache()
        self.session = requests.Session()

        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def fetch_user_data(
        self, username: Optional[str] = None, force_refresh: bool = False
    ) -> Optional[GeeksforGeeksUserData]:
        """
        Fetch full GeeksforGeeks metrics for the given or configured username.
        """
        target_username = username or self.config.get("geeksforgeeks", "username", "sayujya_tiwari")
        if not target_username:
            logger.warning("GeeksforGeeks username not configured.")
            return None

        cache_key = f"gfg_user_{target_username.lower()}"
        if not force_refresh:
            cached_data = self.cache.get(cache_key, ttl_seconds=CACHE_TTL)
            if cached_data:
                logger.debug("Returning cached GeeksforGeeks user data for '%s'", target_username)
                return self._dict_to_user_data(cached_data)

        logger.info("Fetching GeeksforGeeks profile from API for '%s'", target_username)

        try:
            url = f"{GFG_API_URL}/{target_username}"
            resp = self.session.get(url, timeout=DEFAULT_TIMEOUT)
            if resp.status_code != 200:
                logger.warning("GeeksforGeeks API returned status %d for '%s'", resp.status_code, target_username)
                return None

            data = resp.json()
            if not data or "info" not in data:
                # Fallback structure
                user_info = data.get("userName", target_username)
                overall = int(data.get("overallCodingScore", 0))
                total_solved = int(data.get("totalProblemsSolved", 0))
            else:
                info = data.get("info", {})
                user_info = info.get("userName", target_username)
                overall = int(info.get("overallCodingScore", 0))
                total_solved = int(info.get("totalProblemsSolved", 0))

            info = data.get("info", {}) if "info" in data else data
            name = info.get("userName", target_username)
            institute = info.get("institute", "N/A")
            inst_rank = str(info.get("instituteRank", "N/A"))

            # Difficulty breakdown
            solved_stats = data.get("solvedStats", {}) if "solvedStats" in data else data.get("difficultyWiseSolved", {})
            easy = int(solved_stats.get("easy", {}).get("count", 0)) if isinstance(solved_stats.get("easy"), dict) else int(solved_stats.get("easy", 0))
            medium = int(solved_stats.get("medium", {}).get("count", 0)) if isinstance(solved_stats.get("medium"), dict) else int(solved_stats.get("medium", 0))
            hard = int(solved_stats.get("hard", {}).get("count", 0)) if isinstance(solved_stats.get("hard"), dict) else int(solved_stats.get("hard", 0))
            school = int(solved_stats.get("school", {}).get("count", 0)) if isinstance(solved_stats.get("school"), dict) else int(solved_stats.get("school", 0))

            user_data = GeeksforGeeksUserData(
                username=target_username,
                name=name,
                profile_score=overall,
                overall_coding_score=overall,
                total_problems_solved=total_solved,
                monthly_coding_score=int(info.get("monthlyCodingScore", 0)),
                institute_name=institute,
                institute_rank=inst_rank,
                easy_solved=easy,
                medium_solved=medium,
                hard_solved=hard,
                school_solved=school,
            )

            self.cache.set(cache_key, self._user_data_to_dict(user_data))
            return user_data

        except Exception as err:
            logger.error("Failed to fetch GeeksforGeeks user info for '%s': %s", target_username, err)
            return None

    def _user_data_to_dict(self, data: GeeksforGeeksUserData) -> dict:
        return {
            "username": data.username,
            "name": data.name,
            "profile_score": data.profile_score,
            "overall_coding_score": data.overall_coding_score,
            "total_problems_solved": data.total_problems_solved,
            "monthly_coding_score": data.monthly_coding_score,
            "institute_name": data.institute_name,
            "institute_rank": data.institute_rank,
            "easy_solved": data.easy_solved,
            "medium_solved": data.medium_solved,
            "hard_solved": data.hard_solved,
            "school_solved": data.school_solved,
        }

    def _dict_to_user_data(self, d: dict) -> GeeksforGeeksUserData:
        return GeeksforGeeksUserData(
            username=d["username"],
            name=d["name"],
            profile_score=d["profile_score"],
            overall_coding_score=d["overall_coding_score"],
            total_problems_solved=d["total_problems_solved"],
            monthly_coding_score=d.get("monthly_coding_score", 0),
            institute_name=d.get("institute_name", "N/A"),
            institute_rank=d.get("institute_rank", "N/A"),
            easy_solved=d.get("easy_solved", 0),
            medium_solved=d.get("medium_solved", 0),
            hard_solved=d.get("hard_solved", 0),
            school_solved=d.get("school_solved", 0),
        )

    def close(self) -> None:
        self.session.close()


_service: Optional[GeeksforGeeksService] = None
_service_lock = threading.Lock()


def get_geeksforgeeks_data(
    username: Optional[str] = None, force_refresh: bool = False
) -> Optional[GeeksforGeeksUserData]:
    """Helper function to fetch GeeksforGeeks data using singleton instance."""
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = GeeksforGeeksService()
    return _service.fetch_user_data(username=username, force_refresh=force_refresh)


def shutdown_geeksforgeeks_service() -> None:
    """Shutdown GeeksforGeeks singleton instance and close sessions."""
    global _service
    with _service_lock:
        if _service is not None:
            _service.close()
            _service = None
