"""
Codeforces service module for DevPulse.

Responsibilities:
- Reads Codeforces username from config.py / config.toml
- Fetches user profile, rating, rank, max rating, and submission stats via official API
- Uses cache.py for TTL caching
- Uses logger.py for activity logging
- Returns immutable, strongly-typed dataclasses
"""

from dataclasses import dataclass
from typing import Optional, Tuple
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

CODEFORCES_BASE_URL = "https://codeforces.com/api"
DEFAULT_TIMEOUT = (3, 10)
CACHE_TTL = 300  # 5 minutes


@dataclass(frozen=True, slots=True)
class CodeforcesSubmission:
    """Represents a single Codeforces submission."""

    title: str
    problem_index: str
    contest_id: Optional[int]
    language: str
    verdict: str
    creation_time: int
    problem_rating: Optional[int]


@dataclass(frozen=True, slots=True)
class CodeforcesUserData:
    """Represents complete user metrics from Codeforces."""

    handle: str
    name: str
    rating: int
    max_rating: int
    rank: str
    max_rank: str
    avatar_url: str
    contribution: int
    solved_count: int
    recent_submissions: Tuple[CodeforcesSubmission, ...]


class CodeforcesService:
    """Service client for fetching Codeforces user profile & submission statistics."""

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

    def fetch_user_data(self, username: Optional[str] = None, force_refresh: bool = False) -> Optional[CodeforcesUserData]:
        """
        Fetch full Codeforces metrics for the given or configured username.
        """
        target_username = username or self.config.get("codeforces", "username", "Tourist")
        if not target_username:
            logger.warning("Codeforces username not configured.")
            return None

        cache_key = f"codeforces_user_{target_username.lower()}"
        if not force_refresh:
            cached_data = self.cache.get(cache_key, ttl_seconds=CACHE_TTL)
            if cached_data:
                logger.debug("Returning cached Codeforces user data for '%s'", target_username)
                return self._dict_to_user_data(cached_data)

        logger.info("Fetching Codeforces profile from API for '%s'", target_username)

        # 1. User Info API
        try:
            info_url = f"{CODEFORCES_BASE_URL}/user.info?handles={target_username}"
            resp = self.session.get(info_url, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "OK" or not data.get("result"):
                logger.warning("Codeforces user '%s' not found or API error.", target_username)
                return None

            user_raw = data["result"][0]
        except Exception as err:
            logger.error("Failed to fetch Codeforces user info for '%s': %s", target_username, err)
            return None

        # 2. User Status (Submissions) API
        recent_subs = []
        solved_problems = set()
        try:
            status_url = f"{CODEFORCES_BASE_URL}/user.status?handle={target_username}&from=1&count=50"
            status_resp = self.session.get(status_url, timeout=DEFAULT_TIMEOUT)
            if status_resp.status_code == 200:
                status_data = status_resp.json()
                if status_data.get("status") == "OK":
                    for sub in status_data.get("result", []):
                        verdict = sub.get("verdict", "")
                        problem = sub.get("problem", {})
                        prob_name = problem.get("name", "Unknown Problem")
                        prob_index = problem.get("index", "")
                        contest_id = problem.get("contestId")
                        prob_rating = problem.get("rating")
                        lang = sub.get("programmingLanguage", "Unknown")

                        if verdict == "OK":
                            prob_key = f"{contest_id}_{prob_index}" if contest_id else prob_name
                            solved_problems.add(prob_key)

                        if len(recent_subs) < 5 and verdict == "OK":
                            recent_subs.append(
                                CodeforcesSubmission(
                                    title=prob_name,
                                    problem_index=prob_index,
                                    contest_id=contest_id,
                                    language=lang,
                                    verdict="Accepted",
                                    creation_time=sub.get("creationTimeSeconds", 0),
                                    problem_rating=prob_rating,
                                )
                            )
        except Exception as err:
            logger.warning("Failed to fetch Codeforces user submissions for '%s': %s", target_username, err)

        first_name = user_raw.get("firstName", "")
        last_name = user_raw.get("lastName", "")
        full_name = f"{first_name} {last_name}".strip()

        user_data = CodeforcesUserData(
            handle=user_raw.get("handle", target_username),
            name=full_name or user_raw.get("handle", target_username),
            rating=user_raw.get("rating", 0),
            max_rating=user_raw.get("maxRating", 0),
            rank=user_raw.get("rank", "unrated").title(),
            max_rank=user_raw.get("maxRank", "unrated").title(),
            avatar_url=user_raw.get("titlePhoto", ""),
            contribution=user_raw.get("contribution", 0),
            solved_count=len(solved_problems),
            recent_submissions=tuple(recent_subs),
        )

        self.cache.set(cache_key, self._user_data_to_dict(user_data))
        return user_data

    def _user_data_to_dict(self, data: CodeforcesUserData) -> dict:
        return {
            "handle": data.handle,
            "name": data.name,
            "rating": data.rating,
            "max_rating": data.max_rating,
            "rank": data.rank,
            "max_rank": data.max_rank,
            "avatar_url": data.avatar_url,
            "contribution": data.contribution,
            "solved_count": data.solved_count,
            "recent_submissions": [
                {
                    "title": s.title,
                    "problem_index": s.problem_index,
                    "contest_id": s.contest_id,
                    "language": s.language,
                    "verdict": s.verdict,
                    "creation_time": s.creation_time,
                    "problem_rating": s.problem_rating,
                }
                for s in data.recent_submissions
            ],
        }

    def _dict_to_user_data(self, d: dict) -> CodeforcesUserData:
        subs = tuple(
            CodeforcesSubmission(
                title=s["title"],
                problem_index=s.get("problem_index", ""),
                contest_id=s.get("contest_id"),
                language=s["language"],
                verdict=s["verdict"],
                creation_time=s["creation_time"],
                problem_rating=s.get("problem_rating"),
            )
            for s in d.get("recent_submissions", [])
        )
        return CodeforcesUserData(
            handle=d["handle"],
            name=d["name"],
            rating=d["rating"],
            max_rating=d["max_rating"],
            rank=d["rank"],
            max_rank=d["max_rank"],
            avatar_url=d.get("avatar_url", ""),
            contribution=d.get("contribution", 0),
            solved_count=d.get("solved_count", 0),
            recent_submissions=subs,
        )

    def close(self) -> None:
        self.session.close()


_service: Optional[CodeforcesService] = None
_service_lock = threading.Lock()


def get_codeforces_data(username: Optional[str] = None, force_refresh: bool = False) -> Optional[CodeforcesUserData]:
    """Helper function to fetch Codeforces data using singleton instance."""
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = CodeforcesService()
    return _service.fetch_user_data(username=username, force_refresh=force_refresh)


def shutdown_codeforces_service() -> None:
    """Shutdown Codeforces singleton instance and close sessions."""
    global _service
    with _service_lock:
        if _service is not None:
            _service.close()
            _service = None
