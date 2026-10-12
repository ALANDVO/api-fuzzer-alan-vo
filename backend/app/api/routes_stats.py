"""Statistics and audit logging endpoints for the operational dashboard."""
import json
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query
from backend.app.core.auth import TokenUser, require_role
from backend.app.core.database import get_db
from backend.app.models.schemas import AuditLogResponse, StatsOverviewResponse

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats", response_model=StatsOverviewResponse)
def get_stats(user: TokenUser = Depends(require_role("viewer"))) -> StatsOverviewResponse:
    """Retrieve aggregate statistics and metrics across all fuzzer operations."""
    db = get_db()
    with db.get_connection() as conn:
        total_specs = conn.execute("SELECT COUNT(*) FROM specs").fetchone()[0]
        total_jobs = conn.execute("SELECT COUNT(*) FROM fuzz_jobs").fetchone()[0]

        total_cases = conn.execute("SELECT COUNT(*) FROM test_cases").fetchone()[0]
        total_findings = conn.execute("SELECT COUNT(*) FROM test_results WHERE severity != 'pass'").fetchone()[0]

        # Severity breakdown
        sev_rows = conn.execute(
            "SELECT severity, COUNT(*) FROM test_results GROUP BY severity"
        ).fetchall()
        sev_counts: Dict[str, int] = {"critical": 0, "moderate": 0, "minor": 0, "pass": 0}
        for s, count in sev_rows:
            if s in sev_counts:
                sev_counts[s] = count

        # Dimension breakdown
        dim_rows = conn.execute(
            """SELECT c.dimension, COUNT(*)
               FROM test_results r
               JOIN test_cases c ON r.case_id = c.id
               WHERE r.severity != 'pass'
               GROUP BY c.dimension"""
        ).fetchall()
        dim_counts: Dict[str, int] = {}
        for d, count in dim_rows:
            dim_counts[d] = count

    return StatsOverviewResponse(
        total_specs=total_specs,
        total_jobs=total_jobs,
        total_cases_fuzzed=total_cases,
        total_findings=total_findings,
        findings_by_severity=sev_counts,
        findings_by_dimension=dim_counts
    )


@router.get("/audit", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: TokenUser = Depends(require_role("admin"))
) -> List[AuditLogResponse]:
    """Retrieve immutable audit log records (administrative access only)."""
    db = get_db()
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()

    return [
        AuditLogResponse(
            id=r["id"],
            timestamp=r["timestamp"],
            user_id=r["user_id"],
            action=r["action"],
            resource=r["resource"],
            details=json.loads(r["details"]) if r["details"] else {}
        )
        for r in rows
    ]
