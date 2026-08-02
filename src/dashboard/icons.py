"""
Icon map, language colors, language dots, and terminal capability utilities for DevPulse Dashboard.
"""

import os
import sys
from typing import Dict, Optional

# Icon mapping supporting modern UTF-8 / Nerd Font symbols with clean fallbacks
ICONS: Dict[str, str] = {
    "bolt": "⚡",
    "github": "🐙",
    "leetcode": "🧩",
    "codeforces": "⚔️",
    "geeksforgeeks": "🟢",
    "star": "⭐",
    "fork": "⑂",
    "check": "✓",
    "user": "👤",
    "repo": "📦",
    "trophy": "🏆",
    "fire": "🔥",
    "clock": "🕒",
    "heart": "❤️",
    "chart": "📊",
    "circle": "●",
    "arrow_right": "→",
    "dot": "•",
    "cpu": "💻",
    "memory": "🧠",
}

ASCII_FALLBACKS: Dict[str, str] = {
    "bolt": "*",
    "github": "[GH]",
    "leetcode": "[LC]",
    "codeforces": "[CF]",
    "geeksforgeeks": "[GFG]",
    "star": "*",
    "fork": "Y",
    "check": "v",
    "user": "@",
    "repo": "repo",
    "trophy": "[T]",
    "fire": "!",
    "clock": "T",
    "heart": "<3",
    "chart": "#",
    "circle": "o",
    "arrow_right": "->",
    "dot": "-",
    "cpu": "CPU",
    "memory": "RAM",
}

# Language Color & Dot Symbol Mappings
LANGUAGE_COLORS: Dict[str, str] = {
    "python": "bold yellow",
    "pythondata": "bold yellow",
    "c++": "bold blue",
    "cpp": "bold blue",
    "c": "bold cyan",
    "javascript": "yellow",
    "js": "yellow",
    "typescript": "bold cyan",
    "ts": "bold cyan",
    "rust": "bold red",
    "go": "bold cyan",
    "golang": "bold cyan",
    "java": "bold red",
    "kotlin": "bold magenta",
    "swift": "bold red",
    "shell": "bold green",
    "bash": "bold green",
    "html": "red",
    "css": "blue",
    "sql": "magenta",
}

LANGUAGE_DOTS: Dict[str, str] = {
    "python": "🟡",
    "pythondata": "🟡",
    "c++": "🔵",
    "cpp": "🔵",
    "c": "🔵",
    "javascript": "🟡",
    "js": "🟡",
    "typescript": "🔵",
    "ts": "🔵",
    "rust": "🔴",
    "go": "🔵",
    "golang": "🔵",
    "java": "🔴",
    "kotlin": "🟣",
    "swift": "🔴",
    "shell": "🟢",
    "bash": "🟢",
    "html": "🔴",
    "css": "🔵",
    "sql": "🟣",
}


def is_utf8_supported() -> bool:
    """Check if current terminal supports UTF-8 encoding."""
    if sys.platform == "win32":
        encoding = getattr(sys.stdout, "encoding", "") or ""
        return encoding.lower().replace("-", "") in ("utf8", "utf-8")
    lang = os.environ.get("LANG", "") + os.environ.get("LC_ALL", "")
    return "UTF-8" in lang.upper() or "UTF8" in lang.upper()


def get_icon(name: str, fallback_ascii: bool = False) -> str:
    """Retrieve an icon by name with automatic UTF-8 capability check."""
    if fallback_ascii or not is_utf8_supported():
        return ASCII_FALLBACKS.get(name, ICONS.get(name, ""))
    return ICONS.get(name, "")


def get_language_color(lang: Optional[str]) -> str:
    """Retrieve Rich style string for a programming language."""
    if not lang:
        return "dim white"
    return LANGUAGE_COLORS.get(lang.lower().strip(), "magenta")


def get_language_dot(lang: Optional[str]) -> str:
    """Retrieve a colored circle dot symbol for a programming language."""
    if not lang or not is_utf8_supported():
        return "●"
    return LANGUAGE_DOTS.get(lang.lower().strip(), "⚪")
