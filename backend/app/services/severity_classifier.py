"""Deterministic severity classifier and curl reproduction generator for API fuzz findings."""
import json
import re
from typing import Any, Dict, List, Optional, Tuple

SQL_ERRORS = [
    "syntax error", "sql syntax", "sqlite3.operationalerror", "psycopg2",
    "ora-00936", "mysql_fetch", "unclosed quotation mark", "sqlstate"
]
TRAVERSAL_INDICATORS = ["root:x:0:0:", "[boot loader]", "/bin/sh", "/bin/bash"]
STACK_TRACE_INDICATORS = ["traceback (most recent call last)", "exception in thread", "fatal error:"]


class SeverityClassifier:
    """Evaluates actual API response vs expected behavior and assigns severity and evidence."""

    def classify(
        self,
        test_name: str,
        dimension: str,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Any,
        expected_status: int,
        actual_status: Optional[int],
        response_body: Optional[str],
        latency_ms: float,
        error_msg: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """Returns (severity, reasoning, reproduction_curl)."""
        repro_curl = self.generate_curl(method, url, headers, body)

        if error_msg:
            return "critical", f"Network or connection level crash occurred: {error_msg}", repro_curl

        if actual_status is None:
            return "critical", "Target server dropped connection or failed to return response.", repro_curl

        resp_lower = (response_body or "").lower()

        # 1. Critical checks
        # 1a. SQL injection leakage
        if dimension == "injection_payloads" and any(err in resp_lower for err in SQL_ERRORS):
            return "critical", "SQL database syntax or driver exception leaked in HTTP response body.", repro_curl

        # 1b. Path traversal leakage
        if any(ind in resp_lower for ind in TRAVERSAL_INDICATORS):
            return "critical", "Path traversal succeeded: sensitive operating system file contents returned.", repro_curl

        # 1c. Unhandled 500 Server Error
        if actual_status >= 500:
            if any(st in resp_lower for st in STACK_TRACE_INDICATORS):
                return "critical", f"Unhandled server 500 exception with active stack trace leaked.", repro_curl
            return "critical", f"Internal Server Error {actual_status} triggered on input payload.", repro_curl

        # 1d. Auth bypass
        if dimension == "auth_bypass" and actual_status in (200, 201, 204):
            return "critical", f"Security violation: Unauthenticated or malformed token was granted {actual_status} access.", repro_curl

        # 2. Moderate checks
        # Status code deviation: expected validation error (4xx) but received 200 success on malformed/injection data
        if dimension in ("injection_payloads", "type_coercion", "boundary_values") and actual_status == 200 and expected_status in (400, 422):
            return "moderate", f"Input validation failure: Malformed/injection input was accepted as valid (status 200).", repro_curl

        if actual_status != expected_status and actual_status not in (200, 201, 204, 400, 401, 403, 404, 422):
            return "moderate", f"Unexpected HTTP status code {actual_status} received (expected {expected_status}).", repro_curl

        # 3. Minor checks: Latency spikes
        if latency_ms > 2500.0:
            return "minor", f"Performance degradation: request latency {latency_ms:.1f}ms exceeds 2500ms threshold.", repro_curl

        # 4. Pass
        return "pass", f"Response conforms to expected behavior: status {actual_status} in {latency_ms:.1f}ms.", repro_curl

    def generate_curl(self, method: str, url: str, headers: Dict[str, str], body: Any) -> str:
        """Construct exact single-line curl command for reproduction."""
        cmd = ["curl", "-sS", "-X", method.upper(), f"'{url}'"]
        for k, v in headers.items():
            cmd.append(f"-H '{k}: {v}'")
        if body is not None:
            if isinstance(body, (dict, list)):
                cmd.append(f"-d '{json.dumps(body)}'")
            else:
                cmd.append(f"-d '{str(body)}'")
        cmd.append("--max-time 15")
        return " ".join(cmd)
