"""Flask blueprints for scans, reports, and tool catalog."""

import json
import logging
import time

from flask import Blueprint, Response, jsonify, request, stream_with_context

from server.db import check_db_health
from server.report_store import ReportStore
from server.scan_orchestrator import ScanOrchestrator, subscribe_sse, unsubscribe_sse
from server.tools_catalog import get_catalog

logger = logging.getLogger(__name__)

scans_bp = Blueprint("scans", __name__)
reports_bp = Blueprint("reports", __name__)
tools_bp = Blueprint("tools", __name__)

store = ReportStore()
orchestrator = ScanOrchestrator(store)


@tools_bp.route("/catalog", methods=["GET"])
def tools_catalog():
    tools = get_catalog(include_availability=True)
    available = sum(1 for t in tools if t.get("available"))
    return jsonify({
        "tools": tools,
        "count": len(tools),
        "available_count": available,
    })


@scans_bp.route("", methods=["POST"])
def create_scan():
    data = request.get_json(silent=True) or {}
    target = data.get("target", "").strip()
    tools = data.get("tools", [])
    name = data.get("name")
    mode = data.get("mode")

    if not target:
        return jsonify({"error": "Target is required"}), 400
    if not tools and mode != "all_web":
        return jsonify({"error": "At least one tool is required (or set mode=all_web)"}), 400

    try:
        scan = orchestrator.start_scan(
            target=target,
            tools=tools or None,
            name=name,
            mode=mode,
        )
        return jsonify({"success": True, "scan": scan}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Create scan failed: %s", exc)
        return jsonify({"error": str(exc)}), 500


@scans_bp.route("", methods=["GET"])
def list_scans():
    status = request.args.get("status")
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))
    scans = store.list_scans(status=status, limit=limit, offset=offset)
    return jsonify({"scans": scans, "count": len(scans)})


@scans_bp.route("/<scan_id>", methods=["GET"])
def get_scan(scan_id):
    scan = store.get_scan(scan_id)
    if not scan:
        return jsonify({"error": "Scan not found"}), 404
    findings = store.get_findings(scan_id=scan_id)
    scan["findings"] = findings
    scan["findings_count"] = len(findings)
    return jsonify(scan)


@scans_bp.route("/<scan_id>/stream", methods=["GET"])
def stream_scan(scan_id):
    scan = store.get_scan(scan_id)
    if not scan:
        return jsonify({"error": "Scan not found"}), 404

    def generate():
        q = subscribe_sse(scan_id)
        try:
            yield f"data: {json.dumps({'type': 'connected', 'scan_id': scan_id})}\n\n"
            if scan.get("status") in ("completed", "completed_with_errors", "cancelled", "failed"):
                yield f"data: {json.dumps({'type': 'scan_completed', 'scan_id': scan_id, 'status': scan['status']})}\n\n"
                return

            while True:
                try:
                    event = q.get(timeout=30)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") in ("scan_completed", "scan_cancelled"):
                        break
                except Exception:
                    yield f"data: {json.dumps({'type': 'heartbeat', 'scan_id': scan_id, 'ts': time.time()})}\n\n"
                    refreshed = store.get_scan(scan_id)
                    if refreshed and refreshed.get("status") in (
                        "completed", "completed_with_errors", "cancelled", "failed",
                    ):
                        yield f"data: {json.dumps({'type': 'scan_completed', 'scan_id': scan_id, 'status': refreshed['status']})}\n\n"
                        break
        finally:
            unsubscribe_sse(scan_id, q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@scans_bp.route("/<scan_id>/cancel", methods=["POST"])
def cancel_scan(scan_id):
    if orchestrator.cancel_scan(scan_id):
        return jsonify({"success": True, "message": "Scan cancelled"})
    return jsonify({"error": "Scan not running or not found"}), 404


@reports_bp.route("", methods=["GET"])
def list_reports():
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))
    reports = store.list_reports(limit=limit, offset=offset)
    for r in reports:
        if r.get("summary_json"):
            try:
                r["summary"] = json.loads(r["summary_json"])
            except json.JSONDecodeError:
                r["summary"] = {}
    return jsonify({"reports": reports, "count": len(reports)})


@reports_bp.route("/<report_id>", methods=["GET"])
def get_report(report_id):
    report = store.get_report(report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report)


@reports_bp.route("/<report_id>/export", methods=["POST"])
def export_report(report_id):
    report = store.get_report(report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify({
        "success": True,
        "export": report,
        "format": "json",
    })


@reports_bp.route("/<report_id>", methods=["DELETE"])
def delete_report(report_id):
    if store.delete_report(report_id):
        return jsonify({"success": True})
    return jsonify({"error": "Report not found"}), 404


@scans_bp.route("/health/db", methods=["GET"])
def db_health():
    return jsonify(check_db_health())
