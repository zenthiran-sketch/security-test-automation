"""Direct scan orchestrator — runs user-selected tools without AI decision engine."""

from __future__ import annotations

import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from server.findings_parser import parse_tool_output
from server.master_report import create_master_report
from server.report_store import ReportStore
from server.target_normalizer import NormalizedTarget, normalize_target
from server.tool_registry import (
    CATEGORY_WORKER_CAPS,
    get_tool_meta,
    is_tool_available,
    tools_for_profile,
)

logger = logging.getLogger(__name__)

ToolExecutor = Callable[[str, Dict[str, Any]], Dict[str, Any]]

_tool_executors: Dict[str, ToolExecutor] = {}
_active_scans: Dict[str, threading.Event] = {}
_sse_subscribers: Dict[str, List] = {}
_sse_lock = threading.Lock()


def register_tool_executor(name: str, executor: ToolExecutor):
    _tool_executors[name.lower()] = executor


def register_tool_executors(executors: Dict[str, ToolExecutor]):
    for name, fn in executors.items():
        register_tool_executor(name, fn)


def get_registered_tools() -> List[str]:
    return list(_tool_executors.keys())


def _emit_event(scan_id: str, event_type: str, data: Dict[str, Any]):
    payload = {
        "type": event_type,
        "scan_id": scan_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **data,
    }
    with _sse_lock:
        queues = _sse_subscribers.get(scan_id, [])
        for q in queues:
            try:
                q.put(payload)
            except Exception:
                pass


def subscribe_sse(scan_id: str):
    import queue
    q: queue.Queue = queue.Queue()
    with _sse_lock:
        _sse_subscribers.setdefault(scan_id, []).append(q)
    return q


def unsubscribe_sse(scan_id: str, q):
    with _sse_lock:
        subs = _sse_subscribers.get(scan_id, [])
        if q in subs:
            subs.remove(q)
        if not subs and scan_id in _sse_subscribers:
            del _sse_subscribers[scan_id]


def _max_workers(jobs: List[Dict[str, Any]]) -> int:
    env_cap = int(os.environ.get("HEXSTRIKE_SCAN_WORKERS", "12"))
    # Soft category-aware cap: sum of per-category caps for tools present, then global env
    by_cat: Dict[str, int] = {}
    for job in jobs:
        meta = get_tool_meta(job.get("tool_name", "")) or {}
        cat = meta.get("category", "web_security")
        by_cat[cat] = by_cat.get(cat, 0) + 1
    category_budget = 0
    for cat, count in by_cat.items():
        category_budget += min(count, CATEGORY_WORKER_CAPS.get(cat, 4))
    return max(1, min(len(jobs), env_cap, max(category_budget, 4)))


class ScanOrchestrator:
    def __init__(self, store: Optional[ReportStore] = None):
        self.store = store or ReportStore()

    def expand_all_web_tools(self, available_only: bool = True) -> List[Dict[str, Any]]:
        tools = tools_for_profile("web_url", available_only=available_only)
        # Keep only tools that have executors registered
        return [t for t in tools if t["name"].lower() in _tool_executors]

    def start_scan(
        self,
        target: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        name: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not target:
            raise ValueError("Target is required")

        mode = (mode or "").strip().lower()
        if mode == "all_web":
            # Include unavailable so preflight can mark skipped explicitly
            tools = tools_for_profile("web_url", available_only=False)
            tools = [t for t in tools if t["name"].lower() in _tool_executors]
            if not tools:
                raise ValueError("No web tools registered")
        elif not tools:
            raise ValueError("At least one tool is required (or mode=all_web)")

        valid_names = set(_tool_executors.keys())
        for t in tools:
            tool_name = t.get("name", "").lower()
            if tool_name not in valid_names:
                raise ValueError(f"Unknown or unsupported tool: {tool_name}")

        normalize_target(target)  # validate early
        scan = self.store.create_scan(target=target, name=name, tools=tools)
        scan_id = scan["id"]

        cancel_event = threading.Event()
        _active_scans[scan_id] = cancel_event

        thread = threading.Thread(
            target=self._run_scan,
            args=(scan_id, target, cancel_event),
            daemon=True,
        )
        thread.start()
        return scan

    def cancel_scan(self, scan_id: str) -> bool:
        event = _active_scans.get(scan_id)
        if event:
            event.set()
            self.store.update_scan_status(scan_id, "cancelled", datetime.utcnow().isoformat() + "Z")
            _emit_event(scan_id, "scan_cancelled", {})
            return True
        return False

    def _resolve_target(self, tool_name: str, normalized: NormalizedTarget) -> str:
        meta = get_tool_meta(tool_name) or {}
        kind = meta.get("target", "url")
        # gobuster dns mode needs host — handled via params in executor params override below
        return normalized.for_kind(kind)

    def _run_scan(self, scan_id: str, target: str, cancel_event: threading.Event):
        self.store.update_scan_status(scan_id, "running")
        try:
            normalized = normalize_target(target)
        except Exception as exc:
            self.store.update_scan_status(
                scan_id, "failed", datetime.utcnow().isoformat() + "Z"
            )
            _emit_event(scan_id, "scan_completed", {"status": "failed", "error": str(exc)})
            return

        _emit_event(scan_id, "scan_started", {
            "target": target,
            "normalized": {
                "url": normalized.url,
                "host": normalized.host,
                "ip": normalized.ip,
            },
        })

        scan = self.store.get_scan(scan_id)
        if not scan:
            return

        jobs = scan.get("jobs", [])
        any_failed = False
        workers = _max_workers(jobs)

        def run_job(job: Dict[str, Any]):
            nonlocal any_failed
            if cancel_event.is_set():
                self.store.update_job_completed(job["id"], "cancelled", stderr="scan cancelled")
                return

            job_id = job["id"]
            tool_name = job["tool_name"].lower()
            params = json.loads(job.get("params_json") or "{}")

            # PATH preflight
            if not is_tool_available(tool_name):
                msg = f"tool_not_installed: {tool_name}"
                self.store.update_job_completed(job_id, "skipped", stderr=msg)
                _emit_event(scan_id, "tool_completed", {
                    "job_id": job_id, "tool": tool_name, "status": "skipped", "reason": msg,
                })
                return

            self.store.update_job_running(job_id)
            _emit_event(scan_id, "tool_started", {"job_id": job_id, "tool": tool_name})

            executor = _tool_executors.get(tool_name)
            if not executor:
                self.store.update_job_completed(job_id, "failed", stderr=f"No executor for {tool_name}")
                any_failed = True
                _emit_event(scan_id, "tool_completed", {
                    "job_id": job_id, "tool": tool_name, "status": "failed",
                })
                return

            try:
                tool_target = self._resolve_target(tool_name, normalized)
                # Special-case gobuster dns → host
                if tool_name == "gobuster" and (params.get("mode") or "dir") == "dns":
                    tool_target = normalized.host

                result = executor(tool_target, params)
                success = bool(result.get("success", False))
                status = "completed" if success else "failed"
                stdout = result.get("stdout", "") or ""
                stderr = result.get("stderr", "") or result.get("error", "") or ""
                return_code = result.get("return_code")
                execution_time = result.get("execution_time", 0)

                self.store.update_job_completed(
                    job_id, status, stdout, stderr, return_code, execution_time,
                )

                findings = []
                if success:
                    findings = parse_tool_output(
                        tool_name, stdout, stderr, scan_id, job_id, success=True
                    )
                    self.store.save_findings(findings)
                else:
                    any_failed = True

                _emit_event(scan_id, "tool_completed", {
                    "job_id": job_id,
                    "tool": tool_name,
                    "status": status,
                    "findings_count": len(findings),
                    "execution_time": execution_time,
                })
            except Exception as exc:
                logger.exception("Job %s failed: %s", job_id, exc)
                any_failed = True
                self.store.update_job_completed(job_id, "failed", stderr=str(exc))
                _emit_event(scan_id, "tool_completed", {
                    "job_id": job_id, "tool": tool_name, "status": "failed",
                    "error": str(exc),
                })

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(run_job, job) for job in jobs]
            for future in as_completed(futures):
                if cancel_event.is_set():
                    break
                try:
                    future.result()
                except Exception as exc:
                    logger.exception("Scan job error: %s", exc)
                    any_failed = True

        if cancel_event.is_set():
            final_status = "cancelled"
        else:
            scan = self.store.get_scan(scan_id)
            job_statuses = [j.get("status") for j in scan.get("jobs", [])]
            has_fail = any_failed or "failed" in job_statuses
            has_ok = "completed" in job_statuses
            if has_fail and has_ok:
                final_status = "completed_with_errors"
            elif has_fail and not has_ok:
                final_status = "completed_with_errors"
            else:
                final_status = "completed"

        completed_at = datetime.utcnow().isoformat() + "Z"
        self.store.update_scan_status(scan_id, final_status, completed_at)

        try:
            create_master_report(self.store, scan_id)
        except Exception as exc:
            logger.exception("Failed to create master report: %s", exc)
            try:
                self.store.create_report(scan_id)
            except Exception:
                logger.exception("Fallback report also failed")

        _emit_event(scan_id, "scan_completed", {"status": final_status})

        if scan_id in _active_scans:
            del _active_scans[scan_id]
