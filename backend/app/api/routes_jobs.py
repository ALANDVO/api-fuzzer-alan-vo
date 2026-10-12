"""API routes for fuzz test execution, job monitoring, finding inspection, and report export."""
import json
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from backend.app.core.auth import TokenUser, require_role
from backend.app.core.database import get_db, utc_now
from backend.app.models.schemas import EndpointSummary, FuzzJobCreateRequest, FuzzJobDetailResponse, FuzzJobResponse, TestResultResponse
from backend.app.services.export_service import ExportService
from backend.app.services.fuzz_runner import FuzzRunner
from backend.app.services.mutation_engine import MutationEngine

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _map_job(r: Any) -> FuzzJobResponse:
    return FuzzJobResponse(
        id=r["id"], spec_id=r["spec_id"], target_base_url=r["target_base_url"], status=r["status"],
        total_cases=r["total_cases"], passed_cases=r["passed_cases"], findings_count=r["findings_count"],
        created_at=r["created_at"], completed_at=r["completed_at"], triggered_by=r["triggered_by"]
    )


@router.post("", response_model=FuzzJobDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_fuzz_job(req: FuzzJobCreateRequest, user: TokenUser = Depends(require_role("operator"))) -> FuzzJobDetailResponse:
    db = get_db()
    with db.get_connection() as conn:
        spec_row = conn.execute("SELECT * FROM specs WHERE id = ?", (req.spec_id,)).fetchone()
    if not spec_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Spec {req.spec_id} not found")

    endpoints = [EndpointSummary(**ep) for ep in json.loads(spec_row["endpoints_summary"])][:req.max_endpoints]
    if not endpoints:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The selected specification has no endpoints.")

    mutation = MutationEngine()
    cases = []
    for ep in endpoints:
        cases.extend(mutation.build_cases(endpoint=ep, dimensions=req.dimensions, cases_per_endpoint=req.cases_per_endpoint))

    job_id = str(uuid.uuid4())
    cfg = {"dimensions": req.dimensions, "cases_per_endpoint": req.cases_per_endpoint, "max_endpoints": req.max_endpoints, "llm": req.enable_llm_advisory}

    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO fuzz_jobs (id, spec_id, target_base_url, status, config, total_cases, passed_cases, findings_count, created_at, triggered_by) VALUES (?, ?, ?, 'pending', ?, 0, 0, 0, ?, ?)",
            (job_id, req.spec_id, req.target_base_url.rstrip("/"), json.dumps(cfg), utc_now(), user.email)
        )
        conn.commit()

    db.record_audit(user.user_id, "job.create", f"job:{job_id}", {"target": req.target_base_url, "cases_count": len(cases)})
    runner = FuzzRunner(target_base_url=req.target_base_url, enable_llm=req.enable_llm_advisory)
    raw_results = await runner.run_job(job_id=job_id, cases=cases)

    with db.get_connection() as conn:
        job_row = conn.execute("SELECT * FROM fuzz_jobs WHERE id = ?", (job_id,)).fetchone()

    formatted = [
        TestResultResponse(
            id=r["result_id"], case_id=r["case_id"], job_id=r["job_id"], test_name=r["test_name"],
            endpoint=r["endpoint"], method=r["method"], dimension=r["dimension"], status_code=r["status_code"],
            latency_ms=r["latency_ms"], response_body=r["response_body"], error_message=r["error_message"],
            severity=r["severity"], reasoning=r["reasoning"], reproduction_curl=r["reproduction_curl"],
            advisory_notes=r["advisory_notes"], created_at=utc_now()
        )
        for r in raw_results
    ]
    return FuzzJobDetailResponse(job=_map_job(job_row), results=formatted)


@router.get("", response_model=List[FuzzJobResponse])
def list_jobs(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), user: TokenUser = Depends(require_role("viewer"))) -> List[FuzzJobResponse]:
    db = get_db()
    with db.get_connection() as conn:
        rows = conn.execute("SELECT * FROM fuzz_jobs ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
    return [_map_job(r) for r in rows]


@router.get("/{job_id}", response_model=FuzzJobDetailResponse)
def get_job(job_id: str, severity: Optional[str] = Query(None), user: TokenUser = Depends(require_role("viewer"))) -> FuzzJobDetailResponse:
    db = get_db()
    with db.get_connection() as conn:
        job_row = conn.execute("SELECT * FROM fuzz_jobs WHERE id = ?", (job_id,)).fetchone()
        if not job_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")
        q = "SELECT r.*, c.test_name, c.endpoint_path, c.endpoint_method, c.dimension FROM test_results r JOIN test_cases c ON r.case_id = c.id WHERE r.job_id = ?"
        params = [job_id]
        if severity:
            q += " AND r.severity = ?"
            params.append(severity)
        rows = conn.execute(q + " ORDER BY r.created_at ASC", tuple(params)).fetchall()

    results = [
        TestResultResponse(
            id=r["id"], case_id=r["case_id"], job_id=r["job_id"], test_name=r["test_name"],
            endpoint=r["endpoint_path"], method=r["endpoint_method"], dimension=r["dimension"],
            status_code=r["status_code"], latency_ms=r["latency_ms"], response_body=r["response_body"],
            error_message=r["error_message"], severity=r["severity"], reasoning=r["reasoning"],
            reproduction_curl=r["reproduction_curl"], advisory_notes=r["advisory_notes"], created_at=r["created_at"]
        )
        for r in rows
    ]
    return FuzzJobDetailResponse(job=_map_job(job_row), results=results)


@router.get("/{job_id}/export")
def export_job_report(job_id: str, format: str = Query("json", pattern="^(json|markdown|sarif)$"), user: TokenUser = Depends(require_role("viewer"))) -> Response:
    db = get_db()
    with db.get_connection() as conn:
        job_row = conn.execute("SELECT * FROM fuzz_jobs WHERE id = ?", (job_id,)).fetchone()
        if not job_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")
        rows = conn.execute(
            "SELECT r.*, c.test_name, c.endpoint_path as endpoint, c.endpoint_method as method, c.dimension FROM test_results r JOIN test_cases c ON r.case_id = c.id WHERE r.job_id = ?",
            (job_id,)
        ).fetchall()

    j_dict, r_list = dict(job_row), [dict(r) for r in rows]
    if format == "markdown":
        content, m_type, ext = ExportService.export_markdown(j_dict, r_list), "text/markdown", "md"
    elif format == "sarif":
        content, m_type, ext = ExportService.export_sarif(j_dict, r_list), "application/json", "sarif"
    else:
        content, m_type, ext = ExportService.export_json(j_dict, r_list), "application/json", "json"

    db.record_audit(user.user_id, "job.export", f"job:{job_id}", {"format": format})
    return Response(content=content, media_type=m_type, headers={"Content-Disposition": f"attachment; filename=fuzz-report-{job_id[:8]}.{ext}"})
