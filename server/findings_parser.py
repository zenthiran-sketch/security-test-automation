"""Rule-based findings parser — no AI/LLM processing."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

SEVERITY_KEYWORDS = [
    ("critical", ["critical", "cve-", "rce", "remote code execution"]),
    ("high", ["high", "sql injection", "sqli", "xss", "csrf", "lfi", "rfi", "ssrf"]),
    ("medium", ["medium", "misconfiguration", "exposed", "default credentials"]),
    ("low", ["low", "information disclosure", "verbose"]),
]

GENERIC_INDICATORS = [
    "VULNERABILITY", "EXPLOIT", "SQL injection", "XSS", "CSRF",
    "CRITICAL", "HIGH", "MEDIUM", "LOW",
]

HOST_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)
URL_RE = re.compile(r"^https?://\S+", re.IGNORECASE)
PORT_RE = re.compile(
    r"(?:^|\s)(\d{1,5})/(tcp|udp)\s+(open|filtered)\s+(\S+)", re.IGNORECASE
)
HTTPX_STATUS_RE = re.compile(r"\[(\d{3})\]")


def _new_finding(
    scan_id: str,
    job_id: Optional[str],
    tool: str,
    severity: str,
    title: str,
    description: str = "",
    evidence: str = "",
    line_ref: Optional[int] = None,
) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "scan_id": scan_id,
        "job_id": job_id,
        "severity": severity,
        "title": title,
        "description": description,
        "evidence": evidence[:8000] if evidence else "",
        "tool": tool,
        "tool_name": tool,
        "line_ref": line_ref,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


def _infer_severity(text: str) -> str:
    lower = text.lower()
    for severity, keywords in SEVERITY_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return severity
    return "info"


def parse_nuclei(stdout: str, scan_id: str, job_id: str, tool: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for line_no, line in enumerate(stdout.splitlines(), start=1):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        info = data.get("info", {})
        severity = str(info.get("severity", "info")).lower()
        title = info.get("name") or info.get("template-id") or "Nuclei finding"
        matched = data.get("matched-at") or data.get("host", "")
        findings.append(_new_finding(
            scan_id, job_id, tool, severity, title,
            description=info.get("description", ""),
            evidence=f"{matched} | {line[:500]}",
            line_ref=line_no,
        ))
    return findings


def parse_nmap(stdout: str, scan_id: str, job_id: str, tool: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for line_no, line in enumerate(stdout.splitlines(), start=1):
        match = PORT_RE.search(line)
        if not match:
            continue
        port, proto, state, service = match.groups()
        if state.lower() != "open":
            continue
        findings.append(_new_finding(
            scan_id, job_id, tool, "info",
            f"Open port {port}/{proto}",
            description=f"Service: {service.strip()}",
            evidence=line.strip(),
            line_ref=line_no,
        ))
    return findings


def parse_httpx(stdout: str, scan_id: str, job_id: str, tool: str) -> List[Dict[str, Any]]:
    findings = []
    for line_no, line in enumerate(stdout.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        status_m = HTTPX_STATUS_RE.search(stripped)
        status = status_m.group(1) if status_m else ""
        sev = "info"
        if status and status.startswith("5"):
            sev = "medium"
        elif status == "403":
            sev = "low"
        title = f"HTTP live {status}" if status else "HTTP probe result"
        findings.append(_new_finding(
            scan_id, job_id, tool, sev, title[:120],
            description="Tech/status from httpx",
            evidence=stripped[:500],
            line_ref=line_no,
        ))
    return findings[:50]


def parse_host_list(stdout: str, scan_id: str, job_id: str, tool: str) -> List[Dict[str, Any]]:
    findings = []
    seen = set()
    for line_no, line in enumerate(stdout.splitlines(), start=1):
        host = line.strip().split()[0] if line.strip() else ""
        host = host.lower().rstrip(".")
        if not host or host in seen:
            continue
        if not HOST_RE.match(host) and not host.startswith("*."):
            continue
        seen.add(host)
        findings.append(_new_finding(
            scan_id, job_id, tool, "info",
            f"Subdomain: {host}",
            description="Discovered host",
            evidence=line.strip(),
            line_ref=line_no,
        ))
    return findings[:200]


def parse_url_list(stdout: str, scan_id: str, job_id: str, tool: str) -> List[Dict[str, Any]]:
    findings = []
    seen = set()
    for line_no, line in enumerate(stdout.splitlines(), start=1):
        url = line.strip().split()[0] if line.strip() else ""
        if not URL_RE.match(url) or url in seen:
            continue
        seen.add(url)
        findings.append(_new_finding(
            scan_id, job_id, tool, "info",
            f"URL: {url[:100]}",
            description="Discovered endpoint",
            evidence=url[:500],
            line_ref=line_no,
        ))
    return findings[:200]


def parse_wafw00f(stdout: str, scan_id: str, job_id: str, tool: str) -> List[Dict[str, Any]]:
    findings = []
    for line_no, line in enumerate(stdout.splitlines(), start=1):
        lower = line.lower()
        if "is behind" in lower or "waf" in lower and "detect" in lower:
            findings.append(_new_finding(
                scan_id, job_id, tool, "info",
                line.strip()[:120],
                description="WAF fingerprint",
                evidence=line.strip(),
                line_ref=line_no,
            ))
    return findings


def parse_dalfox(stdout: str, scan_id: str, job_id: str, tool: str) -> List[Dict[str, Any]]:
    findings = []
    for line_no, line in enumerate(stdout.splitlines(), start=1):
        lower = line.lower()
        if "poc" in lower or "reflected" in lower or "xss" in lower:
            findings.append(_new_finding(
                scan_id, job_id, tool, "high",
                line.strip()[:120] or "Potential XSS",
                description="Dalfox XSS signal",
                evidence=line.strip(),
                line_ref=line_no,
            ))
    return findings


def parse_nikto(stdout: str, scan_id: str, job_id: str, tool: str) -> List[Dict[str, Any]]:
    findings = []
    for line_no, line in enumerate(stdout.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("+") or "OSVDB" in stripped or "CVE-" in stripped:
            findings.append(_new_finding(
                scan_id, job_id, tool, _infer_severity(stripped),
                stripped[:120],
                evidence=stripped,
                line_ref=line_no,
            ))
    return findings[:100]


def parse_sqlmap(stdout: str, scan_id: str, job_id: str, tool: str) -> List[Dict[str, Any]]:
    findings = []
    for line_no, line in enumerate(stdout.splitlines(), start=1):
        lower = line.lower()
        if "is vulnerable" in lower or "sql injection" in lower or "injectable" in lower:
            findings.append(_new_finding(
                scan_id, job_id, tool, "critical",
                line.strip()[:120],
                description="SQLMap injection signal",
                evidence=line.strip(),
                line_ref=line_no,
            ))
    return findings


def parse_generic(stdout: str, scan_id: str, job_id: str, tool: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for line_no, line in enumerate(stdout.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if not any(ind.lower() in lower for ind in GENERIC_INDICATORS):
            continue
        severity = _infer_severity(stripped)
        findings.append(_new_finding(
            scan_id, job_id, tool, severity,
            stripped[:120],
            evidence=stripped,
            line_ref=line_no,
        ))
    return findings


def parse_tool_output(
    tool: str,
    stdout: str,
    stderr: str,
    scan_id: str,
    job_id: str,
    *,
    success: bool = True,
) -> List[Dict[str, Any]]:
    """Parse successful tool stdout into structured findings.

    Failed jobs must not invent findings from stderr.
    """
    if not success:
        return []
    if not stdout or not stdout.strip():
        return []

    tool_lower = tool.lower()
    findings: List[Dict[str, Any]] = []

    if tool_lower in ("nuclei",):
        findings = parse_nuclei(stdout, scan_id, job_id, tool)
    elif tool_lower in ("nmap", "nmap-advanced", "rustscan", "masscan"):
        findings = parse_nmap(stdout, scan_id, job_id, tool)
    elif tool_lower == "httpx":
        findings = parse_httpx(stdout, scan_id, job_id, tool)
    elif tool_lower in ("amass", "subfinder", "fierce", "dnsenum"):
        findings = parse_host_list(stdout, scan_id, job_id, tool)
    elif tool_lower in ("gau", "waybackurls", "katana", "hakrawler"):
        findings = parse_url_list(stdout, scan_id, job_id, tool)
    elif tool_lower == "wafw00f":
        findings = parse_wafw00f(stdout, scan_id, job_id, tool)
    elif tool_lower == "dalfox":
        findings = parse_dalfox(stdout, scan_id, job_id, tool)
    elif tool_lower == "nikto":
        findings = parse_nikto(stdout, scan_id, job_id, tool)
    elif tool_lower == "sqlmap":
        findings = parse_sqlmap(stdout, scan_id, job_id, tool)

    if not findings:
        findings = parse_generic(stdout, scan_id, job_id, tool)

    # Only attach a lightweight output-captured stub for recon tools with lots of noise
    # when nothing structured matched — skip stderr-as-finding entirely.
    return findings
