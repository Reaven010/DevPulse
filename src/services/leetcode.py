"""
LeetCode service module for DevPulse.

Responsibilities:
- Reads LeetCode username from config.py
- Fetches user profile, ranking, and contest statistics via GraphQL API
- Fetches solved problem counts (Easy, Medium, Hard, Total)
- Fetches recent accepted submissions
- Uses cache.py for independent TTL caching
- Uses logger.py for structured logging
- Returns immutable, strongly-typed Python dataclasses
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import threading
from typing import Any, Dict, List, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

try:
    from src.common.cache import get_cache
    from src.common.config import get_config
    from src.common.logger import get_logger
    from src.services.leetcode_queries import PROFILE_AND_STATS_QUERY, RECENT_SUBMISSIONS_QUERY
except ImportError:
    from common.cache import get_cache  # type: ignore
    from common.config import get_config  # type: ignore
    from common.logger import get_logger  # type: ignore
    from services.leetcode_queries import PROFILE_AND_STATS_QUERY, RECENT_SUBMISSIONS_QUERY  # type: ignore

logger = get_logger(__name__)

# Constants
LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
DEFAULT_TIMEOUT = (3, 10)  # (connect_timeout, read_timeout)
DEFAULT_TTL = 900          # seconds (15 minutes)
SUBMISSION_LIMIT = 10

__all__ = [
    "LeetCodeService",
    "get_leetcode_data",
    "shutdown_leetcode_service",
    "LeetCodeSubmission",
    "LeetCodeSolvedStats",
    "LeetCodeContestStats",
    "LeetCodeUserData",
]


@dataclass(frozen=True, slots=True)
class LeetCodeSubmission:
    """Clean, immutable representation of a recent LeetCode submission."""

    title: str
    title_slug: str
    timestamp: int
    status: str
    language: str


@dataclass(frozen=True, slots=True)
class LeetCodeSolvedStats:
    """Clean, immutable breakdown of solved problem counts."""

    total_solved: int
    easy_solved: int
    medium_solved: int
    hard_solved: int


@dataclass(frozen=True, slots=True)
class LeetCodeContestStats:
    """Clean, immutable contest rating and ranking metrics."""

    rating: float
    global_ranking: int
    attended_contests: int
    top_percentage: float


@dataclass(frozen=True, slots=True)
class LeetCodeUserData:
    """Clean, immutable data representation of a LeetCode user profile."""

    username: str
    name: Optional[str]
    avatar_url: Optional[str]
    ranking: int
    solved_stats: LeetCodeSolvedStats
    contest_stats: Optional[LeetCodeContestStats]
    recent_submissions: Tuple[LeetCodeSubmission, ...]


class LeetCodeService:
    """Service to interact with LeetCode GraphQL API, backed by cache, retries, and logger."""

    def __init__(self):
        self.config = get_config()
        self.cache = get_cache()
        self.session = requests.Session()
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="leetcode_service")
        self._configure_session()

    def _configure_session(self) -> None:
        """Configure session with headers and automatic retry policies."""
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "DevPulse-Dashboard/0.1.0",
                "Referer": "https://leetcode.com",
            }
        )
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(
            max_retries=retries,
            pool_connections=10,
            pool_maxsize=10,
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _post_graphql(self, query: str, variables: Dict[str, Any], endpoint_name: str) -> Optional[Dict[str, Any]]:
        """Send a POST request to LeetCode GraphQL API endpoint."""
        try:
            resp = self.session.post(
                LEETCODE_GRAPHQL_URL,
                json={"query": query, "variables": variables},
                timeout=DEFAULT_TIMEOUT,
            )

            if resp.status_code == 404:
                logger.error("LeetCode %s endpoint not found (HTTP 404).", endpoint_name)
                return None
            elif resp.status_code == 429:
                logger.warning("LeetCode API rate limit hit (HTTP 429).")
                return None

            resp.raise_for_status()
            data = resp.json()

            if not isinstance(data, dict):
                raise ValueError(f"Expected dict response for LeetCode {endpoint_name}, got {type(data).__name__}")

            if "errors" in data and data["errors"]:
                logger.warning("LeetCode GraphQL returned errors for %s: %s", endpoint_name, data["errors"])

            return data.get("data")
        except (requests.exceptions.RequestException, ValueError) as err:
            logger.exception("Error executing LeetCode GraphQL query for %s: %s", endpoint_name, err)
            return None

    def _fetch_profile_and_stats(self, username: str, force_refresh: bool) -> Optional[Dict[str, Any]]:
        """Fetch user profile, solved stats, and contest ranking (cached independently)."""
        cache_key = f"leetcode_profile_{username}"
        ttl_seconds = self.config.get("refresh", "leetcode", DEFAULT_TTL)

        if not force_refresh:
            cached_data = self.cache.get(cache_key, ttl_seconds=ttl_seconds)
            if cached_data is not None:
                logger.debug("Cache hit for LeetCode profile '%s'", username)
                return cached_data

        logger.info("Fetching LeetCode profile and stats from API for '%s'", username)
        payload = self._post_graphql(
            PROFILE_AND_STATS_QUERY,
            variables={"username": username},
            endpoint_name=f"profile ({username})",
        )

        if payload and isinstance(payload, dict):
            # Check explicitly for non-existent user response
            if "matchedUser" in payload and payload["matchedUser"] is None:
                logger.warning("LeetCode user '%s' does not exist (matchedUser is null).", username)
                return None

            if payload.get("matchedUser"):
                self.cache.set(cache_key, payload)
                return payload

        stale = self.cache.get(cache_key, ttl_seconds=None)
        if stale is not None:
            logger.info("Returning stale LeetCode profile cache for '%s'", username)
        return stale

    def _fetch_recent_submissions(self, username: str, force_refresh: bool) -> List[Dict[str, Any]]:
        """Fetch user recent submissions (cached independently)."""
        cache_key = f"leetcode_submissions_{username}"
        ttl_seconds = self.config.get("refresh", "leetcode", DEFAULT_TTL)

        if not force_refresh:
            cached_data = self.cache.get(cache_key, ttl_seconds=ttl_seconds)
            if cached_data is not None:
                logger.debug("Cache hit for LeetCode submissions '%s'", username)
                return cached_data

        logger.info("Fetching LeetCode recent submissions from API for '%s'", username)
        payload = self._post_graphql(
            RECENT_SUBMISSIONS_QUERY,
            variables={"username": username, "limit": SUBMISSION_LIMIT},
            endpoint_name=f"submissions ({username})",
        )

        submissions_list = []
        if payload and isinstance(payload, dict):
            raw_list = payload.get("recentAcSubmissionList")
            if isinstance(raw_list, list):
                submissions_list = raw_list

        if payload is not None:
            self.cache.set(cache_key, submissions_list)
            return submissions_list

        stale = self.cache.get(cache_key, ttl_seconds=None)
        if isinstance(stale, list):
            logger.info("Returning stale LeetCode submissions cache for '%s'", username)
            return stale
        return []

    def _build_user_data(
        self,
        username: str,
        profile_payload: Dict[str, Any],
        submissions_payload: List[Dict[str, Any]],
    ) -> Optional[LeetCodeUserData]:
        """Construct immutable LeetCodeUserData from GraphQL data payloads safely."""
        matched_user = profile_payload.get("matchedUser")
        if not isinstance(matched_user, dict):
            logger.warning("No matchedUser data found for LeetCode user '%s'", username)
            return None

        profile = matched_user.get("profile", {})
        if not isinstance(profile, dict):
            profile = {}

        # Solved counts by difficulty
        submit_stats = matched_user.get("submitStats", {})
        ac_submissions = []
        if isinstance(submit_stats, dict) and isinstance(submit_stats.get("acSubmissionNum"), list):
            ac_submissions = submit_stats["acSubmissionNum"]

        total_solved = 0
        easy_solved = 0
        medium_solved = 0
        hard_solved = 0

        for item in ac_submissions:
            if not isinstance(item, dict):
                continue
            diff = item.get("difficulty", "").lower()
            count = item.get("count", 0)
            if diff == "all":
                total_solved = count
            elif diff == "easy":
                easy_solved = count
            elif diff == "medium":
                medium_solved = count
            elif diff == "hard":
                hard_solved = count

        solved_stats = LeetCodeSolvedStats(
            total_solved=total_solved,
            easy_solved=easy_solved,
            medium_solved=medium_solved,
            hard_solved=hard_solved,
        )

        # Contest Ranking Stats
        contest_payload = profile_payload.get("userContestRanking")
        contest_stats: Optional[LeetCodeContestStats] = None
        if isinstance(contest_payload, dict):
            try:
                contest_stats = LeetCodeContestStats(
                    rating=round(float(contest_payload.get("rating", 0.0)), 1),
                    global_ranking=int(contest_payload.get("globalRanking", 0)),
                    attended_contests=int(contest_payload.get("attendedContestsCount", 0)),
                    top_percentage=round(float(contest_payload.get("topPercentage", 0.0)), 2),
                )
            except (ValueError, TypeError) as err:
                logger.warning("Error parsing contest stats for '%s': %s", username, err)

        # Recent Submissions
        recent_submissions: List[LeetCodeSubmission] = []
        for sub in submissions_payload:
            if not isinstance(sub, dict):
                continue
            try:
                recent_submissions.append(
                    LeetCodeSubmission(
                        title=sub["title"],
                        title_slug=sub.get("titleSlug", ""),
                        timestamp=int(sub.get("timestamp", 0)),
                        status=sub.get("statusDisplay", "Accepted"),
                        language=sub.get("lang", ""),
                    )
                )
            except KeyError as ke:
                logger.warning("Skipping malformed LeetCode submission item for '%s': missing key %s", username, ke)

        return LeetCodeUserData(
            username=matched_user.get("username", username),
            name=profile.get("realName"),
            avatar_url=profile.get("userAvatar"),
            ranking=int(profile.get("ranking", 0)),
            solved_stats=solved_stats,
            contest_stats=contest_stats,
            recent_submissions=tuple(recent_submissions),
        )

    def get_user_data(
        self, username: Optional[str] = None, force_refresh: bool = False
    ) -> Optional[LeetCodeUserData]:
        """
        Fetch LeetCode profile, solved counts, contest stats, and recent submissions.

        Args:
            username: LeetCode username. If None, resolves from config.
            force_refresh: If True, bypasses cache and forces API requests.

        Returns:
            LeetCodeUserData instance or None if user not found / unavailable.
        """
        target_username = username or self.config.get("leetcode", "username", "")
        if not target_username or not isinstance(target_username, str) or not target_username.strip():
            logger.warning("No LeetCode username provided or configured.")
            return None

        target_username = target_username.strip()

        # Concurrent fetching of profile+stats and recent submissions
        future_profile = self.executor.submit(self._fetch_profile_and_stats, target_username, force_refresh)
        future_submissions = self.executor.submit(self._fetch_recent_submissions, target_username, force_refresh)

        profile_payload = future_profile.result()
        submissions_payload = future_submissions.result()

        if not profile_payload:
            logger.error("Failed to retrieve profile for LeetCode user '%s'.", target_username)
            return None

        return self._build_user_data(target_username, profile_payload, submissions_payload)

    def close(self) -> None:
        """Release session connections and executor threads."""
        try:
            self.session.close()
        except Exception:
            pass
        try:
            self.executor.shutdown(wait=False)
        except Exception:
            pass

    def __del__(self) -> None:
        self.close()


# Reusable service singleton & thread safety lock
_service: Optional[LeetCodeService] = None
_service_lock = threading.Lock()


def get_leetcode_data(
    username: Optional[str] = None, force_refresh: bool = False
) -> Optional[LeetCodeUserData]:
    """Helper function to fetch LeetCode user data using thread-safe LeetCodeService singleton."""
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = LeetCodeService()
    return _service.get_user_data(username=username, force_refresh=force_refresh)


def shutdown_leetcode_service() -> None:
    """Shutdown global LeetCodeService singleton resources cleanly."""
    global _service
    with _service_lock:
        if _service is not None:
            _service.close()
            _service = None
