"""Central registry for web-console tools — catalog metadata + execution hints."""

from __future__ import annotations

import shutil
from typing import Any, Dict, List, Optional

# target kinds: url | host | ip
# category used for concurrency buckets
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    # --- existing ---
    "nmap": {
        "label": "Nmap",
        "binary": "nmap",
        "category": "network",
        "profile": "web_url",
        "target": "ip",
        "description": "Port and service discovery",
        "params": [
            {"name": "scan_type", "type": "string", "default": "-sV", "label": "Scan type"},
            {"name": "ports", "type": "string", "default": "80,443,8080,8443", "label": "Ports"},
            {"name": "additional_args", "type": "string", "default": "-T4 -Pn", "label": "Extra args"},
        ],
    },
    "nmap-advanced": {
        "label": "Nmap Advanced",
        "binary": "nmap",
        "category": "network",
        "profile": "web_url",
        "target": "ip",
        "description": "Deeper nmap scripts (-sC -sV)",
        "params": [
            {"name": "ports", "type": "string", "default": "1-1000", "label": "Ports"},
            {"name": "additional_args", "type": "string", "default": "-sC -sV -T4 -Pn", "label": "Extra args"},
        ],
    },
    "rustscan": {
        "label": "RustScan",
        "binary": "rustscan",
        "category": "network",
        "profile": "web_url",
        "target": "ip",
        "description": "Fast port scanner",
        "params": [
            {"name": "additional_args", "type": "string", "default": "-a", "label": "Extra args"},
        ],
    },
    "masscan": {
        "label": "Masscan",
        "binary": "masscan",
        "category": "network",
        "profile": "web_url",
        "target": "ip",
        "description": "High-speed port scanner",
        "params": [
            {"name": "ports", "type": "string", "default": "80,443", "label": "Ports"},
            {"name": "additional_args", "type": "string", "default": "--rate 1000", "label": "Extra args"},
        ],
    },
    "nuclei": {
        "label": "Nuclei",
        "binary": "nuclei",
        "category": "vuln_scanning",
        "profile": "web_url",
        "target": "url",
        "description": "Template-based vulnerability scanner",
        "params": [
            {"name": "severity", "type": "string", "default": "", "label": "Severity filter"},
            {"name": "tags", "type": "string", "default": "", "label": "Tags"},
            {"name": "additional_args", "type": "string", "default": "-json -silent", "label": "Extra args"},
        ],
    },
    "gobuster": {
        "label": "Gobuster",
        "binary": "gobuster",
        "category": "web_security",
        "profile": "web_url",
        "target": "url",
        "description": "Directory/DNS brute forcing",
        "params": [
            {"name": "mode", "type": "select", "default": "dir", "options": ["dir", "dns", "fuzz", "vhost"], "label": "Mode"},
            {"name": "wordlist", "type": "string", "default": "", "label": "Wordlist"},
            {"name": "additional_args", "type": "string", "default": "", "label": "Extra args"},
        ],
    },
    "dirb": {
        "label": "Dirb",
        "binary": "dirb",
        "category": "web_security",
        "profile": "web_url",
        "target": "url",
        "description": "Classic web content scanner",
        "params": [
            {"name": "wordlist", "type": "string", "default": "", "label": "Wordlist"},
            {"name": "additional_args", "type": "string", "default": "", "label": "Extra args"},
        ],
    },
    "nikto": {
        "label": "Nikto",
        "binary": "nikto",
        "category": "web_security",
        "profile": "web_url",
        "target": "url",
        "description": "Web server vulnerability scanner",
        "params": [
            {"name": "additional_args", "type": "string", "default": "", "label": "Extra args"},
        ],
    },
    "sqlmap": {
        "label": "SQLMap",
        "binary": "sqlmap",
        "category": "web_security",
        "profile": "web_url",
        "target": "url",
        "description": "SQL injection detection",
        "params": [
            {"name": "additional_args", "type": "string", "default": "--batch --random-agent --level=1 --risk=1", "label": "Extra args"},
        ],
    },
    "ffuf": {
        "label": "FFuf",
        "binary": "ffuf",
        "category": "web_security",
        "profile": "web_url",
        "target": "url",
        "description": "Fast web fuzzer",
        "params": [
            {"name": "wordlist", "type": "string", "default": "", "label": "Wordlist"},
            {"name": "additional_args", "type": "string", "default": "-mc 200,301,302,403", "label": "Extra args"},
        ],
    },
    "feroxbuster": {
        "label": "Feroxbuster",
        "binary": "feroxbuster",
        "category": "web_security",
        "profile": "web_url",
        "target": "url",
        "description": "Recursive content discovery",
        "params": [
            {"name": "wordlist", "type": "string", "default": "", "label": "Wordlist"},
            {"name": "additional_args", "type": "string", "default": "-q", "label": "Extra args"},
        ],
    },
    "dirsearch": {
        "label": "Dirsearch",
        "binary": "dirsearch",
        "category": "web_security",
        "profile": "web_url",
        "target": "url",
        "description": "Web path scanner",
        "params": [
            {"name": "additional_args", "type": "string", "default": "", "label": "Extra args"},
        ],
    },
    "wfuzz": {
        "label": "Wfuzz",
        "binary": "wfuzz",
        "category": "web_security",
        "profile": "web_url",
        "target": "url",
        "description": "Web application fuzzer",
        "params": [
            {"name": "wordlist", "type": "string", "default": "", "label": "Wordlist"},
            {"name": "additional_args", "type": "string", "default": "-c --hc 404", "label": "Extra args"},
        ],
    },
    "httpx": {
        "label": "HTTPX",
        "binary": "httpx",
        "category": "web_security",
        "profile": "web_url",
        "target": "url",
        "description": "HTTP probing and tech detection",
        "params": [
            {"name": "additional_args", "type": "string", "default": "-tech-detect -status-code -title -silent", "label": "Extra args"},
        ],
    },
    "katana": {
        "label": "Katana",
        "binary": "katana",
        "category": "web_security",
        "profile": "web_url",
        "target": "url",
        "description": "Web crawler",
        "params": [
            {"name": "additional_args", "type": "string", "default": "-silent -d 2", "label": "Extra args"},
        ],
    },
    "wpscan": {
        "label": "WPScan",
        "binary": "wpscan",
        "category": "vuln_scanning",
        "profile": "web_url",
        "target": "url",
        "description": "WordPress vulnerability scanner",
        "params": [
            {"name": "additional_args", "type": "string", "default": "--enumerate p,t,u --no-banner", "label": "Extra args"},
        ],
    },
    "arjun": {
        "label": "Arjun",
        "binary": "arjun",
        "category": "web_security",
        "profile": "web_url",
        "target": "url",
        "description": "HTTP parameter discovery",
        "params": [
            {"name": "additional_args", "type": "string", "default": "", "label": "Extra args"},
        ],
    },
    "paramspider": {
        "label": "ParamSpider",
        "binary": "paramspider",
        "category": "web_security",
        "profile": "web_url",
        "target": "host",
        "description": "Parameter mining from web archives",
        "params": [
            {"name": "additional_args", "type": "string", "default": "", "label": "Extra args"},
        ],
    },
    "dalfox": {
        "label": "Dalfox",
        "binary": "dalfox",
        "category": "web_security",
        "profile": "web_url",
        "target": "url",
        "description": "XSS vulnerability scanner",
        "params": [
            {"name": "additional_args", "type": "string", "default": "--silence", "label": "Extra args"},
        ],
    },
    "jaeles": {
        "label": "Jaeles",
        "binary": "jaeles",
        "category": "vuln_scanning",
        "profile": "web_url",
        "target": "url",
        "description": "Signature-based web scanner",
        "params": [
            {"name": "additional_args", "type": "string", "default": "scan -s /tmp", "label": "Extra args"},
        ],
    },
    "x8": {
        "label": "x8",
        "binary": "x8",
        "category": "web_security",
        "profile": "web_url",
        "target": "url",
        "description": "Hidden parameter discovery",
        "params": [
            {"name": "additional_args", "type": "string", "default": "", "label": "Extra args"},
        ],
    },
    "amass": {
        "label": "Amass",
        "binary": "amass",
        "category": "osint",
        "profile": "web_url",
        "target": "host",
        "description": "Subdomain enumeration",
        "params": [
            {"name": "additional_args", "type": "string", "default": "-passive", "label": "Extra args"},
        ],
    },
    "subfinder": {
        "label": "Subfinder",
        "binary": "subfinder",
        "category": "osint",
        "profile": "web_url",
        "target": "host",
        "description": "Passive subdomain discovery",
        "params": [
            {"name": "additional_args", "type": "string", "default": "-silent", "label": "Extra args"},
        ],
    },
    "fierce": {
        "label": "Fierce",
        "binary": "fierce",
        "category": "osint",
        "profile": "web_url",
        "target": "host",
        "description": "DNS reconnaissance",
        "params": [
            {"name": "additional_args", "type": "string", "default": "", "label": "Extra args"},
        ],
    },
    "dnsenum": {
        "label": "DNSenum",
        "binary": "dnsenum",
        "category": "osint",
        "profile": "web_url",
        "target": "host",
        "description": "DNS enumeration",
        "params": [
            {"name": "additional_args", "type": "string", "default": "", "label": "Extra args"},
        ],
    },
    "gau": {
        "label": "GAU",
        "binary": "gau",
        "category": "osint",
        "profile": "web_url",
        "target": "host",
        "description": "Get All URLs from archives",
        "params": [
            {"name": "additional_args", "type": "string", "default": "--subs", "label": "Extra args"},
        ],
    },
    "waybackurls": {
        "label": "Waybackurls",
        "binary": "waybackurls",
        "category": "osint",
        "profile": "web_url",
        "target": "host",
        "description": "URLs from Wayback Machine",
        "params": [
            {"name": "additional_args", "type": "string", "default": "", "label": "Extra args"},
        ],
    },
    "hakrawler": {
        "label": "Hakrawler",
        "binary": "hakrawler",
        "category": "web_security",
        "profile": "web_url",
        "target": "url",
        "description": "Simple web crawler",
        "params": [
            {"name": "additional_args", "type": "string", "default": "-plain", "label": "Extra args"},
        ],
    },
    "wafw00f": {
        "label": "Wafw00f",
        "binary": "wafw00f",
        "category": "web_security",
        "profile": "web_url",
        "target": "url",
        "description": "WAF fingerprinting",
        "params": [
            {"name": "additional_args", "type": "string", "default": "", "label": "Extra args"},
        ],
    },
    "uro": {
        "label": "Uro",
        "binary": "uro",
        "category": "osint",
        "profile": "web_url",
        "target": "host",
        "description": "URL filtering / dedup helper (expects stdin URLs)",
        "params": [
            {"name": "additional_args", "type": "string", "default": "", "label": "Extra args"},
        ],
    },
}


CATEGORY_WORKER_CAPS = {
    "network": 4,
    "vuln_scanning": 4,
    "web_security": 6,
    "osint": 4,
}


def get_tool_meta(name: str) -> Optional[Dict[str, Any]]:
    return TOOL_REGISTRY.get(name.lower())


def get_binary(name: str) -> str:
    meta = get_tool_meta(name)
    return (meta or {}).get("binary", name)


def is_tool_available(name: str) -> bool:
    binary = get_binary(name)
    return shutil.which(binary) is not None


def catalog_entries(include_availability: bool = True) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for name, meta in TOOL_REGISTRY.items():
        entry = {
            "name": name,
            "label": meta["label"],
            "category": meta["category"],
            "profile": meta.get("profile", "web_url"),
            "target_kind": meta.get("target", "url"),
            "description": meta["description"],
            "params": meta.get("params", []),
            "binary": meta.get("binary", name),
        }
        if include_availability:
            entry["available"] = is_tool_available(name)
        out.append(entry)
    return out


def tools_for_profile(profile: str = "web_url", available_only: bool = True) -> List[Dict[str, Any]]:
    tools = []
    for name, meta in TOOL_REGISTRY.items():
        if meta.get("profile") != profile:
            continue
        if available_only and not is_tool_available(name):
            continue
        params = {}
        for p in meta.get("params", []):
            params[p["name"]] = p.get("default", "")
        tools.append({"name": name, "params": params})
    return tools


def default_params(name: str) -> Dict[str, str]:
    meta = get_tool_meta(name)
    if not meta:
        return {}
    return {p["name"]: p.get("default", "") for p in meta.get("params", [])}
