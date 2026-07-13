"""Data models for scans, jobs, findings, and reports."""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Scan:
    id: str
    name: str
    target: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    config_json: str = "{}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScanJob:
    id: str
    scan_id: str
    tool_name: str
    status: str
    params_json: str = "{}"
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    return_code: Optional[int] = None
    execution_time: Optional[float] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Finding:
    id: str
    scan_id: str
    job_id: Optional[str]
    severity: str
    title: str
    description: Optional[str] = None
    evidence: Optional[str] = None
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    id: str
    scan_id: str
    title: str
    summary_json: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReportSummary:
    scan_id: str
    target: str
    total_findings: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    tools_executed: List[str] = field(default_factory=list)
    tools_failed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
