"""
DevPulse - Modern Developer Dashboard Entry Point

Responsibilities:
1. Load configuration from config.py / config.toml
2. Initialize centralized logging via logger.py
3. Aggregate metrics concurrently via dashboard_service.py
4. Render terminal dashboard via renderer.py
5. Handle Ctrl+C (KeyboardInterrupt) and resource cleanup gracefully
"""

import argparse
import sys
import time
from rich.live import Live

# Reconfigure stdout/stderr encoding on Windows to support UTF-8 symbols
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from src.common.config import ConfigError, get_config
    from src.common.logger import get_logger, setup_logger
    from src.dashboard.dashboard_service import fetch_dashboard_data, shutdown_dashboard_service
    from src.dashboard.renderer import DashboardRenderer
except ImportError:
    from common.config import ConfigError, get_config  # type: ignore
    from common.logger import get_logger, setup_logger  # type: ignore
    from dashboard.dashboard_service import fetch_dashboard_data, shutdown_dashboard_service  # type: ignore
    from dashboard.renderer import DashboardRenderer  # type: ignore


def main() -> None:
    parser = argparse.ArgumentParser(description="DevPulse - Modern Developer Dashboard")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force fresh API calls, ignoring cache",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch mode: continuously refresh dashboard with live UI",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Watch mode refresh interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--theme",
        type=str,
        default=None,
        help="Override active theme (e.g. github-dark, catppuccin, dracula, nord, tokyonight)",
    )
    args = parser.parse_args()

    # 1. Initialize Logger
    setup_logger()
    logger = get_logger("main")

    # 2. Load Config
    try:
        config = get_config()
        logger.info("Configuration loaded successfully (theme: %s).", config.get("general", "theme", "github-dark"))
    except ConfigError as err:
        logger.error("Configuration error: %s", err)

    renderer = DashboardRenderer(theme_name=args.theme)

    try:
        # 3. Watch Mode vs Single-Shot Execution
        if args.watch:
            logger.info("Entering Watch Mode (refresh interval: %ds)...", args.interval)
            data = fetch_dashboard_data(force_refresh=args.refresh)
            with Live(renderer.render_layout(data), console=renderer.console, refresh_per_second=1) as live:
                while True:
                    time.sleep(args.interval)
                    data = fetch_dashboard_data(force_refresh=args.refresh)
                    live.update(renderer.render_layout(data))
        else:
            # Single-shot render
            logger.info("Fetching dashboard data...")
            data = fetch_dashboard_data(force_refresh=args.refresh)
            logger.info("Rendering dashboard layout...")
            renderer.render(data)

    except KeyboardInterrupt:
        renderer.console.print(
            "\n[bold yellow]DevPulse session stopped. Have a productive coding day![/bold yellow]\n"
        )
    except Exception as err:
        logger.exception("Unexpected error running DevPulse: %s", err)
    finally:
        # 5. Clean up singleton thread pools and session resources
        shutdown_dashboard_service()
        logger.info("DevPulse shutdown completed cleanly.")


if __name__ == "__main__":
    main()
