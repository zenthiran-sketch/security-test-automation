"""Normalize a user target string into url / host / ip forms for tools."""

from __future__ import annotations

import re
import socket
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse


@dataclass
class NormalizedTarget:
    raw: str
    url: str
    host: str
    ip: Optional[str] = None

    def for_kind(self, kind: str) -> str:
        kind = (kind or "url").lower()
        if kind == "host":
            return self.host
        if kind == "ip":
            return self.ip or self.host
        if kind == "url":
            return self.url
        return self.raw


_IPV4 = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")


def normalize_target(raw: str) -> NormalizedTarget:
    text = (raw or "").strip()
    if not text:
        raise ValueError("Target is required")

    # Bare host/IP → assume https URL for web tools
    if "://" not in text:
        host = text.split("/")[0].split(":")[0]
        url = f"https://{text}" if not text.startswith("/") else text
        if _IPV4.match(host) or host.lower() == "localhost":
            url = f"http://{text}"
    else:
        parsed = urlparse(text)
        host = parsed.hostname or text
        url = text

    host = host.rstrip(".")
    ip: Optional[str] = None
    try:
        if _IPV4.match(host):
            ip = host
        else:
            ip = socket.gethostbyname(host)
    except Exception:
        ip = None

    return NormalizedTarget(raw=text, url=url, host=host, ip=ip)
