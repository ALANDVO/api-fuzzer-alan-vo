"""Asynchronous fuzz execution engine running adversarial tests against live or sandbox APIs."""
import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional
import httpx
from backend.app.core.database import get_db, utc_now
from backend.app.models.schemas import TestCaseModel, TestResultResponse
from backend.app.services.llm_service import LLMService
from backend.app.services.severity_classifier import SeverityClassifier


class FuzzRunner:
    """Executes generated test cases, logs metrics, evaluates severities, and updates job state."""

    def __init__(self, target_base_url: str, enable_llm: bool = False):
        self.target_base_url = target_base_url.rstrip("/")
        self.enable_llm = enable_llm
        self.classifier = SeverityClassifier()
        self.llm_service = LLMService() if enable_llm else None

    async def execute_case(self, case: TestCaseModel, job_id: str) -> Dict[str, Any]:
        """Execute a single test case against the target endpoint."""
        url = f"{self.target_base_url}{case.path}"
        start_time = time.perf_counter()
        status_code = None
        response_body = None
        error_msg = None

        try:
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                req_kwargs: Dict[str, Any] = {"headers": case.headers}
                if case.body is not None:
                    if isinstance(case.body, (dict, list)):
                        req_kwargs["json"] = case.body
                    else:
                        req_kwargs["content"] = str(case.body)

                resp = await client.request(case.method, url, **req_kwargs)
                status_code = resp.status_code
                response_body = resp.text[:1000]
        except Exception as e:
            error_msg = str(e)[:300]

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        severity, reasoning, curl_cmd = self.classifier.classify(
            test_name=case.name,
            dimension=case.dimension,
            method=case.method,
            url=url,
            headers=case.headers,
            body=case.body,
            expected_status=case.expected_status,
            actual_status=status_code,
            response_body=response_body,
            latency_ms=latency_ms,
            error_msg=error_msg,
        )

        advisory_notes = None
        if self.enable_llm and self.llm_service and severity != "pass":
            advisory_prompt = (
                f"Fuzz test '{case.name}' returned status {status_code} with severity {severity}.\n"
                f"Reasoning: {reasoning}\nResponse snippet: {response_body or error_msg}\n"
                "Briefly analyze the potential vulnerability impact and suggest remediation."
            )
            advisory_result = await self.llm_service.generate_advisory(advisory_prompt)
            advisory_notes = advisory_result.get("advisory")

        case_id = str(uuid.uuid4())
        result_id = str(uuid.uuid4())

        return {
            "result_id": result_id,
            "case_id": case_id,
            "job_id": job_id,
            "test_name": case.name,
            "endpoint": case.path,
            "method": case.method,
            "dimension": case.dimension,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "response_body": response_body,
            "error_message": error_msg,
            "severity": severity,
            "reasoning": reasoning,
            "reproduction_curl": curl_cmd,
            "advisory_notes": advisory_notes,
            "case_model": case,
        }

    async def run_job(self, job_id: str, cases: List[TestCaseModel]) -> List[Dict[str, Any]]:
        """Run all test cases for a job, persist records in SQLite, and return results."""
        db = get_db()
        results: List[Dict[str, Any]] = []

        with db.get_connection() as conn:
            conn.execute("UPDATE fuzz_jobs SET status = 'running' WHERE id = ?", (job_id,))
            conn.commit()

        # Execute cases sequentially or in small batches to prevent target flooding
        for case in cases:
            res = await self.execute_case(case, job_id)
            results.append(res)

        total_cases = len(results)
        passed_cases = sum(1 for r in results if r["severity"] == "pass")
        findings_count = total_cases - passed_cases

        # Persist test cases and results in transaction
        with db.get_connection() as conn:
            for r in results:
                c: TestCaseModel = r["case_model"]
                conn.execute(
                    """INSERT INTO test_cases (id, job_id, endpoint_method, endpoint_path, dimension, test_name, request_payload, expected_status, generated_by, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        r["case_id"],
                        job_id,
                        c.method,
                        c.path,
                        c.dimension,
                        c.name,
                        json.dumps(c.body) if c.body is not None else "",
                        c.expected_status,
                        c.generated_by,
                        utc_now(),
                    ),
                )
                conn.execute(
                    """INSERT INTO test_results (id, case_id, job_id, status_code, latency_ms, response_body, error_message, severity, reasoning, reproduction_curl, advisory_notes, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        r["result_id"],
                        r["case_id"],
                        job_id,
                        r["status_code"],
                        r["latency_ms"],
                        r["response_body"],
                        r["error_message"],
                        r["severity"],
                        r["reasoning"],
                        r["reproduction_curl"],
                        r["advisory_notes"],
                        utc_now(),
                    ),
                )
            conn.execute(
                """UPDATE fuzz_jobs
                   SET status = 'completed', total_cases = ?, passed_cases = ?, findings_count = ?, completed_at = ?
                   WHERE id = ?""",
                (total_cases, passed_cases, findings_count, utc_now(), job_id),
            )
            conn.commit()

        return results
