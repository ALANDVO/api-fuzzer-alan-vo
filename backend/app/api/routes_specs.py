"""API routes for OpenAPI specification management, schema parsing, and endpoint inspection."""
import json
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from backend.app.core.auth import TokenUser, require_role
from backend.app.core.database import get_db, utc_now
from backend.app.models.schemas import EndpointSummary, SpecResponse, SpecUploadRequest
from backend.app.services.spec_parser import SpecParserError, parse_spec_full

router = APIRouter(prefix="/api/specs", tags=["specs"])


@router.post("", response_model=SpecResponse, status_code=status.HTTP_201_CREATED)
def upload_spec(
    req: SpecUploadRequest,
    user: TokenUser = Depends(require_role("operator"))
) -> SpecResponse:
    """Upload and parse an OpenAPI specification in JSON or YAML format."""
    try:
        spec_dict, endpoints = parse_spec_full(req.raw_spec)
    except SpecParserError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"OpenAPI parsing failed: {str(e)}"
        ) from e

    spec_id = str(uuid.uuid4())
    spec_version = req.version or spec_dict.get("info", {}).get("version", "1.0.0")
    detected_format = "yaml" if req.raw_spec.strip().startswith(("openapi:", "swagger:", "---")) else "json"

    endpoints_data = [ep.model_dump() for ep in endpoints]
    db = get_db()

    with db.get_connection() as conn:
        conn.execute(
            """INSERT INTO specs (id, name, version, format, raw_spec, endpoints_summary, created_at, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                spec_id,
                req.name.strip(),
                spec_version,
                detected_format,
                req.raw_spec,
                json.dumps(endpoints_data),
                utc_now(),
                user.email
            )
        )
        conn.commit()

    db.record_audit(
        user_id=user.user_id,
        action="spec.upload",
        resource=f"spec:{spec_id}",
        details={"name": req.name, "endpoints_count": len(endpoints), "format": detected_format}
    )

    return SpecResponse(
        id=spec_id,
        name=req.name.strip(),
        version=spec_version,
        format=detected_format,
        endpoints_count=len(endpoints),
        endpoints=endpoints,
        created_at=utc_now(),
        created_by=user.email
    )


@router.get("", response_model=List[SpecResponse])
def list_specs(
    search: Optional[str] = Query(None, description="Filter specs by name"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: TokenUser = Depends(require_role("viewer"))
) -> List[SpecResponse]:
    """Retrieve list of uploaded OpenAPI specs with pagination and filtering."""
    db = get_db()
    with db.get_connection() as conn:
        if search:
            cursor = conn.execute(
                "SELECT * FROM specs WHERE name LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (f"%{search}%", limit, offset)
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM specs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
        rows = cursor.fetchall()

    results: List[SpecResponse] = []
    for r in rows:
        endpoints_raw = json.loads(r["endpoints_summary"])
        endpoints = [EndpointSummary(**ep) for ep in endpoints_raw]
        results.append(SpecResponse(
            id=r["id"],
            name=r["name"],
            version=r["version"],
            format=r["format"],
            endpoints_count=len(endpoints),
            endpoints=endpoints,
            created_at=r["created_at"],
            created_by=r["created_by"]
        ))
    return results


@router.get("/{spec_id}", response_model=SpecResponse)
def get_spec(
    spec_id: str,
    user: TokenUser = Depends(require_role("viewer"))
) -> SpecResponse:
    """Retrieve a single specification by identifier with parsed endpoints."""
    db = get_db()
    with db.get_connection() as conn:
        row = conn.execute("SELECT * FROM specs WHERE id = ?", (spec_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Spec {spec_id} not found")

    endpoints_raw = json.loads(row["endpoints_summary"])
    endpoints = [EndpointSummary(**ep) for ep in endpoints_raw]
    return SpecResponse(
        id=row["id"],
        name=row["name"],
        version=row["version"],
        format=row["format"],
        endpoints_count=len(endpoints),
        endpoints=endpoints,
        created_at=row["created_at"],
        created_by=row["created_by"]
    )


@router.delete("/{spec_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_spec(
    spec_id: str,
    user: TokenUser = Depends(require_role("admin"))
) -> None:
    """Delete an OpenAPI specification and associated jobs."""
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.execute("DELETE FROM specs WHERE id = ?", (spec_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Spec {spec_id} not found")

    db.record_audit(
        user_id=user.user_id,
        action="spec.delete",
        resource=f"spec:{spec_id}",
        details={"deleted_by": user.email}
    )
