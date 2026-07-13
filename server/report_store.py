"""CRUD operations for scans, jobs, findings, and reports."""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from server.db import get_connection
from server.models import ReportSummary


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _row_to_dict(row) -> Dict[str, Any]:
    return dict(row) if row else {}


class ReportStore:
    def create_scan(
        self,
        target: str,
        name: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        scan_id = str(uuid.uuid4())
        created_at = _now()
        scan_name = name or f"Scan {target} {created_at[:19]}"
        config = {"tools": tools or []}

        with get_connection() as conn:
            conn.execute(
                """INSERT INTO scans (id, name, target, status, created_at, config_json)
                   VALUES (?, ?, ?, 'queued', ?, ?)""",
                (scan_id, scan_name, target, created_at, json.dumps(config)),
            )
            for tool_entry in tools or []:
                job_id = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO scan_jobs (id, scan_id, tool_name, status, params_json)
                       VALUES (?, ?, ?, 'queued', ?)""",
                    (
                        job_id,
                        scan_id,
                        tool_entry.get("name", ""),
                        json.dumps(tool_entry.get("params", {})),
                    ),
                )
            conn.commit()

        return self.get_scan(scan_id)

    def list_scans(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM scans"
        params: List[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            scan = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
            if not scan:
                return None
            jobs = conn.execute(
                "SELECT * FROM scan_jobs WHERE scan_id = ? ORDER BY started_at ASC",
                (scan_id,),
            ).fetchall()
        result = _row_to_dict(scan)
        result["jobs"] = [_row_to_dict(j) for j in jobs]
        return result

    def update_scan_status(self, scan_id: str, status: str, completed_at: Optional[str] = None):
        with get_connection() as conn:
            if completed_at:
                conn.execute(
                    "UPDATE scans SET status = ?, completed_at = ? WHERE id = ?",
                    (status, completed_at, scan_id),
                )
            else:
                conn.execute("UPDATE scans SET status = ? WHERE id = ?", (status, scan_id))
            conn.commit()

    def update_job_running(self, job_id: str):
        with get_connection() as conn:
            conn.execute(
                "UPDATE scan_jobs SET status = 'running', started_at = ? WHERE id = ?",
                (_now(), job_id),
            )
            conn.commit()

    def update_job_completed(
        self,
        job_id: str,
        status: str,
        stdout: str = "",
        stderr: str = "",
        return_code: Optional[int] = None,
        execution_time: Optional[float] = None,
    ):
        with get_connection() as conn:
            conn.execute(
                """UPDATE scan_jobs SET status = ?, stdout = ?, stderr = ?,
                   return_code = ?, execution_time = ?, completed_at = ?
                   WHERE id = ?""",
                (status, stdout, stderr, return_code, execution_time, _now(), job_id),
            )
            conn.commit()

    def save_findings(self, findings: List[Dict[str, Any]]):
        if not findings:
            return
        with get_connection() as conn:
            for f in findings:
                conn.execute(
                    """INSERT INTO findings
                       (id, scan_id, job_id, severity, title, description, evidence, tool_name, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        f.get("id", str(uuid.uuid4())),
                        f["scan_id"],
                        f.get("job_id"),
                        f.get("severity", "info"),
                        f["title"],
                        f.get("description", ""),
                        f.get("evidence", ""),
                        f.get("tool_name") or f.get("tool") or "",
                        f.get("created_at", _now()),
                    ),
                )
            conn.commit()

    def get_findings(
        self,
        scan_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM findings WHERE 1=1"
        params: List[Any] = []
        if scan_id:
            query += " AND scan_id = ?"
            params.append(scan_id)
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(r) for r in rows]

    def build_summary(self, scan_id: str) -> ReportSummary:
        scan = self.get_scan(scan_id)
        if not scan:
            return ReportSummary(scan_id=scan_id, target="")

        findings = self.get_findings(scan_id=scan_id, limit=10000)
        summary = ReportSummary(
            scan_id=scan_id,
            target=scan["target"],
            total_findings=len(findings),
        )
        for f in findings:
            sev = f.get("severity", "info").lower()
            if sev == "critical":
                summary.critical += 1
            elif sev == "high":
                summary.high += 1
            elif sev == "medium":
                summary.medium += 1
            elif sev == "low":
                summary.low += 1
            else:
                summary.info += 1

        for job in scan.get("jobs", []):
            if job.get("status") == "completed":
                summary.tools_executed.append(job["tool_name"])
            elif job.get("status") in ("failed", "cancelled", "skipped"):
                summary.tools_failed.append(job["tool_name"])

        return summary

    def create_report(self, scan_id: str, title: Optional[str] = None) -> Dict[str, Any]:
        scan = self.get_scan(scan_id)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")
        summary = self.build_summary(scan_id)
        report_title = title or f"Report: {scan['target']}"
        return self.create_report_with_summary(scan_id, report_title, summary.to_dict())

    def create_report_with_summary(
        self,
        scan_id: str,
        title: str,
        summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        report_id = str(uuid.uuid4())
        created_at = _now()
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO reports (id, scan_id, title, summary_json, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (report_id, scan_id, title, json.dumps(summary), created_at),
            )
            conn.commit()
        return self.get_report(report_id)

    def list_reports(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT r.*, s.target, s.name as scan_name, s.status as scan_status
                   FROM reports r
                   JOIN scans s ON s.id = r.scan_id
                   ORDER BY r.created_at DESC LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            report = conn.execute(
                """SELECT r.*, s.target, s.name as scan_name, s.status as scan_status,
                          s.created_at as scan_created_at, s.completed_at as scan_completed_at
                   FROM reports r
                   JOIN scans s ON s.id = r.scan_id
                   WHERE r.id = ?""",
                (report_id,),
            ).fetchone()
            if not report:
                return None

            scan_id = report["scan_id"]
            jobs = conn.execute(
                "SELECT id, tool_name, status, return_code, execution_time, started_at, completed_at FROM scan_jobs WHERE scan_id = ?",
                (scan_id,),
            ).fetchall()
            findings = conn.execute(
                "SELECT * FROM findings WHERE scan_id = ? ORDER BY severity, created_at",
                (scan_id,),
            ).fetchall()

        result = _row_to_dict(report)
        result["summary"] = json.loads(result.get("summary_json", "{}"))
        result["jobs"] = [_row_to_dict(j) for j in jobs]
        result["findings"] = [_row_to_dict(f) for f in findings]

        scan_detail = self.get_scan(scan_id)
        if scan_detail:
            result["job_outputs"] = [
                {
                    "id": j["id"],
                    "tool_name": j["tool_name"],
                    "status": j["status"],
                    "stdout": j.get("stdout", ""),
                    "stderr": j.get("stderr", ""),
                    "return_code": j.get("return_code"),
                    "execution_time": j.get("execution_time"),
                }
                for j in scan_detail.get("jobs", [])
            ]
        return result

    def delete_report(self, report_id: str) -> bool:
        with get_connection() as conn:
            cur = conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
            conn.commit()
            return cur.rowcount > 0

    def get_report_by_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM reports WHERE scan_id = ? ORDER BY created_at DESC LIMIT 1",
                (scan_id,),
            ).fetchone()
        if not row:
            return None
        return self.get_report(row["id"])
