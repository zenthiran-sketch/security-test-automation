"""Resolve wordlist paths for dir/fuzz tools across Linux and Windows."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUNDLED = PROJECT_ROOT / "wordlists" / "common.txt"
LINUX_DEFAULTS = [
    "/usr/share/wordlists/dirb/common.txt",
    "/usr/share/seclists/Discovery/Web-Content/common.txt",
    "/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt",
]


def resolve_wordlist(preferred: str = "") -> str:
    """Return first existing wordlist path."""
    candidates = []
    env = os.environ.get("HEXSTRIKE_WORDLIST", "").strip()
    if preferred:
        candidates.append(preferred)
    if env:
        candidates.append(env)
    candidates.extend(LINUX_DEFAULTS)
    candidates.append(str(BUNDLED))

    for path in candidates:
        if path and Path(path).is_file():
            return path
    # Always fallback to bundled path even if missing (caller may create)
    BUNDLED.parent.mkdir(parents=True, exist_ok=True)
    if not BUNDLED.exists():
        BUNDLED.write_text(
            "\n".join(
                [
                    "admin",
                    "login",
                    "api",
                    "backup",
                    "config",
                    "dashboard",
                    "robots.txt",
                    "sitemap.xml",
                    "index",
                    "test",
                    "dev",
                    "staging",
                    "uploads",
                    "assets",
                    "static",
                    "js",
                    "css",
                    "images",
                    "wp-admin",
                    "wp-login.php",
                    ".git",
                    ".env",
                    "server-status",
                    "phpinfo.php",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    return str(BUNDLED)
