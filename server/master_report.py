"""Rule-based master intelligence report builder (no LLM)."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from server.report_store import ReportStore

PORT_TITLE = re.compile(r"open port\s+(\d+)/(\w+)", re.IGNORECASE)
HOST_TITLE = re.compile(r"subdomain:\s*(.+)", re.IGNORECASE)
URL_TITLE = re.compile(r"url:\s*(.+)", re.IGNORECASE)


def _norm_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def build_master_digest(store: ReportStore, scan_id: str) -> Dict[str, Any]:
    scan = store.get_scan(scan_id)
    if not scan:
        raise ValueError(f"Scan {scan_id} not found")

    findings = store.get_findings(scan_id=scan_id, limit=10000)
    jobs = scan.get("jobs", [])

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in findings:
        sev = (f.get("severity") or "info").lower()
        if sev not in severity_counts:
            sev = "info"
        severity_counts[sev] += 1

    tools_executed = []
    tools_failed = []
    tools_skipped = []
    failures: List[Dict[str, Any]] = []

    for job in jobs:
        status = job.get("status")
        name = job.get("tool_name")
        if status == "completed":
            tools_executed.append(name)
        elif status == "skipped":
            tools_skipped.append(name)
            failures.append({
                "tool": name,
                "status": "skipped",
                "reason": (job.get("stderr") or "tool_not_installed")[:500],
            })
        elif status in ("failed", "cancelled"):
            tools_failed.append(name)
            failures.append({
                "tool": name,
                "status": status,
                "reason": (job.get("stderr") or "")[:500],
            })

    # Deduplicate findings
    deduped = []
    seen = set()
    for f in findings:
        key = (
            _norm_title(f.get("title", "")),
            (f.get("severity") or "").lower(),
            (f.get("tool_name") or f.get("tool") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(f)

    ports: List[Dict[str, str]] = []
    subdomains: List[str] = []
    endpoints: List[str] = []
    for f in deduped:
        title = f.get("title") or ""
        evidence = f.get("evidence") or ""
        m = PORT_TITLE.search(title)
        if m:
            ports.append({"port": m.group(1), "proto": m.group(2), "evidence": evidence[:200]})
            continue
        m = HOST_TITLE.search(title)
        if m:
            subdomains.append(m.group(1).strip())
            continue
        m = URL_TITLE.search(title)
        if m:
            endpoints.append(m.group(1).strip())
            continue
        # also pull raw URLs/hosts from evidence for recon tools
        if evidence.startswith("http"):
            endpoints.append(evidence.split()[0][:300])

    # unique preserve order
    def uniq(items):
        out, s = [], set()
        for i in items:
            if i not in s:
                s.add(i)
                out.append(i)
        return out

    created = scan.get("created_at")
    completed = scan.get("completed_at")
    duration_sec = None
    try:
        if created and completed:
            c0 = datetime.fromisoformat(created.replace("Z", ""))
            c1 = datetime.fromisoformat(completed.replace("Z", ""))
            duration_sec = round((c1 - c0).total_seconds(), 2)
    except Exception:
        duration_sec = None

    risk_score = (
        severity_counts["critical"] * 10
        + severity_counts["high"] * 5
        + severity_counts["medium"] * 2
        + severity_counts["low"]
    )

    return {
        "scan_id": scan_id,
        "target": scan.get("target"),
        "status": scan.get("status"),
        "duration_seconds": duration_sec,
        "risk_score": risk_score,
        "executive_summary": {
            "total_findings": len(deduped),
            **severity_counts,
            "tools_executed": tools_executed,
            "tools_failed": tools_failed,
            "tools_skipped": tools_skipped,
            "tools_total": len(jobs),
        },
        "attack_surface": {
            "open_ports": ports[:100],
            "subdomains": uniq(subdomains)[:200],
            "endpoints": uniq(endpoints)[:300],
        },
        "findings_board": deduped[:500],
        "tool_failures": failures,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def create_master_report(
    store: ReportStore,
    scan_id: str,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    digest = build_master_digest(store, scan_id)
    scan = store.get_scan(scan_id)
    report_title = title or f"Arena Master Report: {scan['target']}"
    return store.create_report_with_summary(scan_id, report_title, digest)
