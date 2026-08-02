"""
Dashboard aggregation service for DevPulse.

Responsibilities:
- Manages an extensible registry of backend metric services
- Concurrently fetches metrics using a persistent thread pool
- Maps futures dynamically using a future-to-service map
- Assembles and returns immutable DashboardData model
- Measures performance and logs cycle completion
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import threading
import time
from typing import Any, Callable, Dict, Optional

try:
    from src.common.config import get_config
    from src.common.logger import get_logger
    from src.dashboard.models import DashboardData
    from src.services.codeforces import get_codeforces_data, shutdown_codeforces_service
    from src.services.geeksforgeeks import get_geeksforgeeks_data, shutdown_geeksforgeeks_service
    from src.services.github import get_github_data, shutdown_github_service
    from src.services.leetcode import get_leetcode_data, shutdown_leetcode_service
except ImportError:
    from common.config import get_config  # type: ignore
    from common.logger import get_logger  # type: ignore
    from dashboard.models import DashboardData  # type: ignore
    from services.codeforces import get_codeforces_data, shutdown_codeforces_service  # type: ignore
    from services.geeksforgeeks import get_geeksforgeeks_data, shutdown_geeksforgeeks_service  # type: ignore
    from services.github import get_github_data, shutdown_github_service  # type: ignore
    from services.leetcode import get_leetcode_data, shutdown_leetcode_service  # type: ignore

logger = get_logger(__name__)

# Extensible Service Registry: Maps service section name -> fetch function
SERVICE_REGISTRY: Dict[str, Callable[[Optional[str], bool], Any]] = {
    "github": get_github_data,
    "leetcode": get_leetcode_data,
    "codeforces": get_codeforces_data,
    "geeksforgeeks": get_geeksforgeeks_data,
}

__all__ = [
    "DashboardService",
    "fetch_dashboard_data",
    "shutdown_dashboard_service",
    "SERVICE_REGISTRY",
]


class DashboardService:
    """Aggregates metrics from registered backend services concurrently."""

    def __init__(self):
        self.config = get_config()
        self.executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="dashboard")

    def fetch(self, force_refresh: bool = False) -> DashboardData:
        """
        Fetch metrics from all enabled registered services concurrently.

        Args:
            force_refresh: If True, forces fresh API calls across all services.

        Returns:
            Aggregated DashboardData object.
        """
        start_time = time.perf_counter()
        logger.info("Starting dashboard data aggregation cycle...")

        future_map = {}
        for service_name, fetch_fn in SERVICE_REGISTRY.items():
            if self.config.get(service_name, "enabled", True):
                logger.debug("Submitting metric task for service '%s'", service_name)
                future = self.executor.submit(fetch_fn, None, force_refresh)
                future_map[future] = service_name

        results: Dict[str, Any] = {}
        for future in as_completed(future_map):
            service_name = future_map[future]
            try:
                result = future.result()
                results[service_name] = result
                logger.debug("Service '%s' task completed successfully.", service_name)
            except Exception as err:
                logger.exception("Error executing service task '%s': %s", service_name, err)
                results[service_name] = None

        elapsed = time.perf_counter() - start_time
        logger.info("Dashboard data aggregation completed in %.2fs.", elapsed)

        return DashboardData(
            timestamp=datetime.now(timezone.utc),
            github=results.get("github"),
            leetcode=results.get("leetcode"),
            codeforces=results.get("codeforces"),
            geeksforgeeks=results.get("geeksforgeeks"),
            extra_data={
                k: v
                for k, v in results.items()
                if k not in ("github", "leetcode", "codeforces", "geeksforgeeks")
            },
        )

    def close(self) -> None:
        """Release persistent executor pool."""
        try:
            self.executor.shutdown(wait=False)
        except Exception:
            pass

    def __del__(self) -> None:
        self.close()


_service: Optional[DashboardService] = None
_service_lock = threading.Lock()


def fetch_dashboard_data(force_refresh: bool = False) -> DashboardData:
    """Helper function to fetch aggregated dashboard data using DashboardService singleton."""
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = DashboardService()
    return _service.fetch(force_refresh=force_refresh)


def shutdown_dashboard_service() -> None:
    """Shutdown DashboardService singleton and all underlying backend services."""
    global _service
    with _service_lock:
        if _service is not None:
            _service.close()
            _service = None

    # Shutdown individual backend services
    shutdown_github_service()
    shutdown_leetcode_service()
    shutdown_codeforces_service()
    shutdown_geeksforgeeks_service()
