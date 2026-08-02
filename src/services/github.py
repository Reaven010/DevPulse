"""
GitHub service module for DevPulse.

Responsibilities:
- Reads GitHub username and access token from config.py
- Concurrently calls GitHub REST API endpoints with connection pooling and retries
- Caches profile, repositories, and events independently using cache.py
- Logs activity, rate limits, and network errors using logger.py
- Returns clean, immutable, strongly-typed Python dataclass structures
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
except ImportError:
    from common.cache import get_cache  # type: ignore
    from common.config import get_config  # type: ignore
    from common.logger import get_logger  # type: ignore

logger = get_logger(__name__)

# Constants
GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"
DEFAULT_TIMEOUT = (3, 10)  # (connect_timeout, read_timeout)
DEFAULT_TTL = 600          # seconds (10 minutes)
MAX_REPOS = 5
EVENT_LIMIT = 30

__all__ = [
    "GitHubService",
    "get_github_data",
    "shutdown_github_service",
    "GitHubRepository",
    "GitHubUserData",
]


@dataclass(frozen=True, slots=True)
class GitHubRepository:
    """Clean, immutable data representation of a GitHub repository."""

    name: str
    full_name: str
    html_url: str
    description: Optional[str]
    stars: int
    forks: int
    language: Optional[str]
    updated_at: str


@dataclass(frozen=True, slots=True)
class GitHubUserData:
    """Clean, immutable data representation of a GitHub user profile & activity."""

    username: str
    name: Optional[str]
    avatar_url: str
    html_url: str
    bio: Optional[str]
    public_repos: int
    followers: int
    following: int
    recent_repo_stars: int
    recent_repos: Tuple[GitHubRepository, ...]
    recent_events_count: int


class GitHubService:
    """Service to interact with GitHub API, backed by cache, retries, and logger."""

    def __init__(self):
        self.config = get_config()
        self.cache = get_cache()
        self.session = requests.Session()
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="github_service")
        self._configure_session()

    def _endpoint(self, *parts: str) -> str:
        """Construct GitHub API endpoint URL cleanly."""
        clean_parts = [p.strip("/") for p in parts if p]
        return "/".join((GITHUB_API_BASE, *clean_parts))

    def _get_headers(self) -> Dict[str, str]:
        """Construct request headers with GitHub API versioning and optional auth."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": "DevPulse-Dashboard/0.1.0",
        }
        token = self.config.get("github", "access_token", "")
        if isinstance(token, str) and token.strip():
            headers["Authorization"] = f"Bearer {token.strip()}"
        return headers

    def _configure_session(self) -> None:
        """Configure session with headers and automatic retry policies."""
        self.session.headers.update(self._get_headers())
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

    def _handle_http_status(self, response: requests.Response, endpoint_name: str, username: str) -> None:
        """Log specific warnings/errors based on HTTP status codes."""
        status = response.status_code
        if status == 401:
            logger.error("GitHub API Unauthorized (HTTP 401): Check your access_token for '%s'.", username)
        elif status == 403:
            logger.warning("GitHub API Rate limit exceeded or forbidden (HTTP 403) for '%s'.", username)
        elif status == 404:
            logger.error("GitHub %s not found (HTTP 404) for username '%s'.", endpoint_name, username)
        elif status == 422:
            logger.error("GitHub API Unprocessable Entity (HTTP 422): Invalid parameters for '%s'.", username)
        elif status >= 500:
            logger.error("GitHub server error (HTTP %d) while fetching %s for '%s'.", status, endpoint_name, username)

    def _fetch_profile(self, username: str, force_refresh: bool) -> Optional[Dict[str, Any]]:
        """Fetch user profile data (cached independently)."""
        cache_key = f"github_profile_{username}"
        ttl_seconds = self.config.get("refresh", "github", DEFAULT_TTL)

        if not force_refresh:
            cached_profile = self.cache.get(cache_key, ttl_seconds=ttl_seconds)
            if cached_profile is not None:
                logger.debug("Cache hit for GitHub profile '%s'", username)
                return cached_profile

        url = self._endpoint("users", username)
        try:
            logger.info("Fetching GitHub profile from API for '%s'", username)
            resp = self.session.get(url, timeout=DEFAULT_TIMEOUT)
            self._handle_http_status(resp, "profile", username)
            resp.raise_for_status()

            user_json = resp.json()
            if not isinstance(user_json, dict):
                raise ValueError(f"Expected dict response for profile, got {type(user_json).__name__}")

            self.cache.set(cache_key, user_json)
            return user_json
        except (requests.exceptions.RequestException, ValueError) as err:
            logger.exception("Error fetching profile for '%s': %s", username, err)
            stale = self.cache.get(cache_key, ttl_seconds=None)
            if stale is not None:
                logger.info("Returning stale profile cache for '%s'", username)
            return stale

    def _fetch_repositories(self, username: str, force_refresh: bool) -> List[Dict[str, Any]]:
        """Fetch user repository list (cached independently)."""
        cache_key = f"github_repos_{username}"
        ttl_seconds = self.config.get("refresh", "github", DEFAULT_TTL)

        if not force_refresh:
            cached_repos = self.cache.get(cache_key, ttl_seconds=ttl_seconds)
            if cached_repos is not None:
                logger.debug("Cache hit for GitHub repos '%s'", username)
                return cached_repos

        url = f"{self._endpoint('users', username, 'repos')}?sort=updated&per_page={MAX_REPOS}"
        try:
            logger.info("Fetching GitHub repos from API for '%s'", username)
            resp = self.session.get(url, timeout=DEFAULT_TIMEOUT)
            self._handle_http_status(resp, "repositories", username)
            resp.raise_for_status()

            repos_json = resp.json()
            if not isinstance(repos_json, list):
                raise ValueError(f"Expected list response for repositories, got {type(repos_json).__name__}")

            self.cache.set(cache_key, repos_json)
            return repos_json
        except (requests.exceptions.RequestException, ValueError) as err:
            logger.exception("Error fetching repos for '%s': %s", username, err)
            stale = self.cache.get(cache_key, ttl_seconds=None)
            if isinstance(stale, list):
                logger.info("Returning stale repos cache for '%s'", username)
                return stale
            return []

    def _fetch_events(self, username: str, force_refresh: bool) -> List[Dict[str, Any]]:
        """Fetch user activity events (cached independently)."""
        cache_key = f"github_events_{username}"
        ttl_seconds = self.config.get("refresh", "github", DEFAULT_TTL)

        if not force_refresh:
            cached_events = self.cache.get(cache_key, ttl_seconds=ttl_seconds)
            if cached_events is not None:
                logger.debug("Cache hit for GitHub events '%s'", username)
                return cached_events

        url = f"{self._endpoint('users', username, 'events')}?per_page={EVENT_LIMIT}"
        try:
            logger.info("Fetching GitHub events from API for '%s'", username)
            resp = self.session.get(url, timeout=DEFAULT_TIMEOUT)
            self._handle_http_status(resp, "events", username)
            resp.raise_for_status()

            events_json = resp.json()
            if not isinstance(events_json, list):
                raise ValueError(f"Expected list response for events, got {type(events_json).__name__}")

            self.cache.set(cache_key, events_json)
            return events_json
        except (requests.exceptions.RequestException, ValueError) as err:
            logger.exception("Error fetching events for '%s': %s", username, err)
            stale = self.cache.get(cache_key, ttl_seconds=None)
            if isinstance(stale, list):
                logger.info("Returning stale events cache for '%s'", username)
                return stale
            return []

    def _build_user_data(
        self,
        username: str,
        profile_json: Dict[str, Any],
        repos_json: List[Dict[str, Any]],
        events_json: List[Dict[str, Any]],
    ) -> GitHubUserData:
        """Construct immutable GitHubUserData from parsed JSON payloads safely."""
        recent_repos: List[GitHubRepository] = []
        recent_repo_stars = 0

        for repo in repos_json:
            if not isinstance(repo, dict):
                continue
            try:
                stars = repo.get("stargazers_count", 0)
                recent_repo_stars += stars

                recent_repos.append(
                    GitHubRepository(
                        name=repo["name"],
                        full_name=repo["full_name"],
                        html_url=repo["html_url"],
                        description=repo.get("description"),
                        stars=stars,
                        forks=repo.get("forks_count", 0),
                        language=repo.get("language"),
                        updated_at=repo.get("updated_at", ""),
                    )
                )
            except KeyError as ke:
                logger.warning("Skipping malformed repository item for '%s': missing key %s", username, ke)

        return GitHubUserData(
            username=profile_json.get("login", username),
            name=profile_json.get("name"),
            avatar_url=profile_json.get("avatar_url", ""),
            html_url=profile_json.get("html_url", ""),
            bio=profile_json.get("bio"),
            public_repos=profile_json.get("public_repos", 0),
            followers=profile_json.get("followers", 0),
            following=profile_json.get("following", 0),
            recent_repo_stars=recent_repo_stars,
            recent_repos=tuple(recent_repos),
            recent_events_count=len(events_json),
        )

    def get_user_data(
        self, username: Optional[str] = None, force_refresh: bool = False
    ) -> Optional[GitHubUserData]:
        """
        Fetch GitHub user profile, repos, and events concurrently using persistent ThreadPoolExecutor.

        Args:
            username: GitHub username. If None, resolves from config.
            force_refresh: If True, bypasses cache and forces API requests.

        Returns:
            GitHubUserData instance or None if profile unavailable.
        """
        target_username = username or self.config.get("github", "username", "")
        if not target_username or not isinstance(target_username, str) or not target_username.strip():
            logger.warning("No GitHub username provided or configured.")
            return None

        target_username = target_username.strip()

        # Submit concurrent tasks to reusable executor
        future_profile = self.executor.submit(self._fetch_profile, target_username, force_refresh)
        future_repos = self.executor.submit(self._fetch_repositories, target_username, force_refresh)
        future_events = self.executor.submit(self._fetch_events, target_username, force_refresh)

        profile_json = future_profile.result()
        repos_json = future_repos.result()
        events_json = future_events.result()

        if not profile_json:
            logger.error("Failed to retrieve profile for GitHub user '%s'.", target_username)
            return None

        return self._build_user_data(target_username, profile_json, repos_json, events_json)

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
_service: Optional[GitHubService] = None
_service_lock = threading.Lock()


def get_github_data(
    username: Optional[str] = None, force_refresh: bool = False
) -> Optional[GitHubUserData]:
    """Helper function to fetch GitHub user data using thread-safe GitHubService singleton."""
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = GitHubService()
    return _service.get_user_data(username=username, force_refresh=force_refresh)


def shutdown_github_service() -> None:
    """Shutdown global GitHubService singleton resources cleanly."""
    global _service
    with _service_lock:
        if _service is not None:
            _service.close()
            _service = None
