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


# Celery task for distributed execution of individual fuzz cases
def execute_fuzz_case_celery(
    case_name: str,
    dimension: str,
    method: str,
    url: str,
    headers: str,
    body: Optional[str],
    expected_status: Optional[int],
    job_id: str,
) -> Dict[str, Any]:
    """Celery task: execute a single fuzz case against the target endpoint.

    This is a synchronous Celery task that runs httpx async inside asyncio.run().
    """
    import asyncio as _asyncio
    import httpx as _httpx
    from backend.app.services.severity_classifier import SeverityClassifier

    classifier = SeverityClassifier()
    target_url = url.rstrip("/")

    # Parse headers from JSON string
    try:
        parsed_headers = json.loads(headers) if headers else {}
    except (json.JSONDecodeError, TypeError):
        parsed_headers = {}

    # Parse body
    case_body = None
    if body is not None:
        try:
            case_body = json.loads(body) if isinstance(body, str) else body
        except (json.JSONDecodeError, TypeError):
            case_body = body

    async def _run_case():
        start_time = time.perf_counter()
        status_code = None
        response_body = None
        error_msg = None

        try:
            async with _httpx.AsyncClient(timeout=10.0, verify=False) as client:
                req_kwargs: Dict[str, Any] = {"headers": parsed_headers}
                if case_body is not None:
                    if isinstance(case_body, (dict, list)):
                        req_kwargs["json"] = case_body
                    else:
                        req_kwargs["content"] = str(case_body)

                resp = await client.request(method, target_url, **req_kwargs)
                status_code = resp.status_code
                response_body = resp.text[:1000]
        except Exception as e:
            error_msg = str(e)[:300]

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        severity, reasoning, curl_cmd = classifier.classify(
            test_name=case_name,
            dimension=dimension,
            method=method,
            url=target_url,
            headers=parsed_headers,
            body=case_body,
            expected_status=expected_status,
            actual_status=status_code,
            response_body=response_body,
            latency_ms=latency_ms,
            error_msg=error_msg,
        )

        return {
            "test_name": case_name,
            "dimension": dimension,
            "method": method,
            "url": target_url,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "response_body": response_body,
            "error_message": error_msg,
            "severity": severity,
            "reasoning": reasoning,
            "reproduction_curl": curl_cmd,
        }

    return _asyncio.run(_run_case())


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

    async def run_job_sequential(self, job_id: str, cases: List[TestCaseModel]) -> List[Dict[str, Any]]:
        """Run all test cases sequentially (original blocking behavior)."""
        db = get_db()
        results: List[Dict[str, Any]] = []

        with db.get_connection() as conn:
            conn.execute("UPDATE fuzz_jobs SET status = 'running' WHERE id = ?", (job_id,))
            conn.commit()

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

    async def run_job_distributed(
        self,
        job_id: str,
        cases: List[TestCaseModel],
        celery_mode: bool = True,
    ) -> List[Dict[str, Any]]:
        """Run all test cases using Celery distributed workers.

        When celery_mode=True, individual cases are dispatched as Celery tasks
        and results are collected asynchronously. When False, falls back to
        sequential execution for compatibility.
        """
        from backend.app.celery_app import execute_fuzz_case_celery as _exec_task

        if not celery_mode:
            return await self.run_job_sequential(job_id, cases)

        total_cases = len(cases)
        results: Dict[int, Dict[str, Any]] = {}  # index -> result

        # Dispatch all cases as Celery tasks
        task_ids: List[str] = []
        for idx, case in enumerate(cases):
            task = _exec_task.s(
                case_name=case.name,
                dimension=case.dimension,
                method=case.method,
                url=f"{self.target_base_url}{case.path}",
                headers=json.dumps(case.headers) if case.headers else "{}",
                body=json.dumps(case.body) if case.body is not None else None,
                expected_status=case.expected_status,
                job_id=job_id,
            )
            task_id = task.apply_async()
            task_ids.append(task_id)

        # Collect results as tasks complete
        completed = 0
        while completed < total_cases:
            for ti in list(task_ids):
                if ti.ready():
                    try:
                        result = ti.get()
                        if result is not None:
                            results[len(results)] = result
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"Celery task {ti.id} failed: {e}")
                    completed += 1
                    task_ids.remove(ti)
            if task_ids:
                asyncio.sleep(0.1)

        # Convert dict values to list preserving submission order
        final_results: List[Dict[str, Any]] = []
        for idx in range(total_cases):
            if idx in results:
                final_results.append(results[idx])

        # Persist results in transaction
        with db.get_connection() as conn:
            # Update job status incrementally as results complete
            passed = sum(1 for r in final_results if r["severity"] == "pass")
            findings = total_cases - passed
            conn.execute(
                """UPDATE fuzz_jobs
                   SET status = 'completed', total_cases = ?, passed_cases = ?, findings_count = ?, completed_at = ?
                   WHERE id = ?""",
                (total_cases, passed, findings, utc_now(), job_id),
            )

            for r in final_results:
                conn.execute(
                    """INSERT INTO test_cases (id, job_id, endpoint_method, endpoint_path, dimension, test_name, request_payload, expected_status, generated_by, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        r.get("case_id", str(uuid.uuid4())),
                        job_id,
                        r.get("method", "GET"),
                        r.get("endpoint", ""),
                        r.get("dimension", ""),
                        r.get("test_name", ""),
                        r.get("response_body", "")[:500],
                        r.get("status_code", None),
                        "distributed-worker",
                        utc_now(),
                    ),
                )
                conn.execute(
                    """INSERT INTO test_results (id, case_id, job_id, status_code, latency_ms, response_body, error_message, severity, reasoning, reproduction_curl, advisory_notes, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid.uuid4()),
                        r.get("case_id", str(uuid.uuid4())),
                        job_id,
                        r.get("status_code"),
                        r.get("latency_ms"),
                        r.get("response_body"),
                        r.get("error_message"),
                        r.get("severity", "unknown"),
                        r.get("reasoning", ""),
                        r.get("reproduction_curl", ""),
                        r.get("advisory_notes"),
                        utc_now(),
                    ),
                )

            # Record progress milestone for SSE streaming
            conn.execute(
                """INSERT INTO progress_events (job_id, completed_cases, severity, created_at)
                   VALUES (?, ?, ?, ?)""",
                (job_id, len(final_results), "completed", utc_now()),
            )
            conn.commit()

        return final_results
