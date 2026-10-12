"""Integration tests crossing HTTP boundary covering spec upload, fuzz run, export, and stats."""
import json
import pytest

TEST_SPEC_JSON = json.dumps({
    "openapi": "3.0.0",
    "info": {"title": "Integration Test API", "version": "1.0.0"},
    "paths": {
        "/api/echo": {
            "post": {
                "summary": "Echo payload",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"msg": {"type": "string"}}
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "OK"}, "400": {"description": "Bad Request"}}
            }
        }
    }
})


def test_full_api_workflow_integration(client, operator_token, admin_token):
    headers_op = {"Authorization": f"Bearer {operator_token}"}
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    # 1. Healthcheck
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    # 2. Upload OpenAPI specification
    upload_resp = client.post(
        "/api/specs",
        headers=headers_op,
        json={"name": "Integration Echo Spec", "raw_spec": TEST_SPEC_JSON}
    )
    assert upload_resp.status_code == 201
    spec_data = upload_resp.json()
    spec_id = spec_data["id"]
    assert spec_data["endpoints_count"] == 1
    assert spec_data["endpoints"][0]["path"] == "/api/echo"

    # 3. Retrieve specification by ID
    get_spec_resp = client.get(f"/api/specs/{spec_id}", headers=headers_op)
    assert get_spec_resp.status_code == 200
    assert get_spec_resp.json()["name"] == "Integration Echo Spec"

    # 4. Launch Fuzz Job against local target
    job_resp = client.post(
        "/api/jobs",
        headers=headers_op,
        json={
            "spec_id": spec_id,
            "target_base_url": "http://127.0.0.1:8000",
            "dimensions": ["boundary_values", "type_coercion"],
            "cases_per_endpoint": 2,
            "max_endpoints": 1,
            "enable_llm_advisory": False
        }
    )
    assert job_resp.status_code == 201
    job_data = job_resp.json()
    job_id = job_data["job"]["id"]
    assert job_data["job"]["status"] == "completed"
    assert len(job_data["results"]) > 0

    # 5. Fetch Job Details and Filter by Severity
    detail_resp = client.get(f"/api/jobs/{job_id}", headers=headers_op)
    assert detail_resp.status_code == 200
    assert len(detail_resp.json()["results"]) > 0

    # 6. Export Reports (JSON, Markdown, SARIF)
    json_export = client.get(f"/api/jobs/{job_id}/export?format=json", headers=headers_op)
    assert json_export.status_code == 200
    assert json_export.headers["content-type"] == "application/json"
    assert "findings" in json_export.json()

    md_export = client.get(f"/api/jobs/{job_id}/export?format=markdown", headers=headers_op)
    assert md_export.status_code == 200
    assert "API Fuzz Security Audit Report" in md_export.text

    sarif_export = client.get(f"/api/jobs/{job_id}/export?format=sarif", headers=headers_op)
    assert sarif_export.status_code == 200
    assert "runs" in sarif_export.json()

    # 7. Aggregate Stats Overview
    stats_resp = client.get("/api/stats", headers=headers_op)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_specs"] >= 1
    assert stats["total_jobs"] >= 1

    # 8. Admin Audit Log Verification
    audit_resp = client.get("/api/audit", headers=headers_admin)
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    assert len(logs) > 0
    actions = [l["action"] for l in logs]
    assert "spec.upload" in actions
    assert "job.create" in actions

    # 9. Admin deletes spec
    del_resp = client.delete(f"/api/specs/{spec_id}", headers=headers_admin)
    assert del_resp.status_code == 204
