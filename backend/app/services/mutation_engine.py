"""Deterministic adversarial test case mutation engine spanning 6 security & robustness dimensions."""
from typing import Any, Dict, List, Optional
from backend.app.models.schemas import EndpointSummary, TestCaseModel

INJECTION_PAYLOADS = [
    ("SQL Injection Single Quote", "' OR '1'='1' --", "injection_payloads"),
    ("SQL Injection Stacked Query", "1; DROP TABLE test_fuzz; --", "injection_payloads"),
    ("XSS Script Tag Injection", "<script>alert('xss-vuln')</script>", "injection_payloads"),
    ("Path Traversal Escape", "../../../../etc/passwd", "injection_payloads"),
    ("Header Injection CRLF", "safe_val\r\nInjected-Header: malicious", "injection_payloads"),
    ("Command Injection Pipe", "; cat /etc/hosts |", "injection_payloads")
]
UNICODE_PAYLOADS = [
    ("Unicode Emoji Bomb", "🔥💥🚀🎉" * 15, "unicode_locale"),
    ("Right-to-Left Override", "\u202Ereversed_admin_token", "unicode_locale"),
    ("Null Byte Injection", "valid_param\x00malicious_suffix", "unicode_locale"),
    ("Non-ASCII Turkish Case", "İıŞşĞğÇçÖö", "unicode_locale"),
]


class MutationEngine:
    """Generates concrete adversarial test cases from OpenAPI endpoint metadata."""

    def build_cases(
        self,
        endpoint: EndpointSummary,
        dimensions: Optional[List[str]] = None,
        cases_per_endpoint: int = 6
    ) -> List[TestCaseModel]:
        dims = list(dimensions or ["boundary_values", "type_coercion", "injection_payloads", "auth_bypass", "idempotency_race", "unicode_locale"])
        cases: List[TestCaseModel] = []
        path, method = endpoint.path, endpoint.method
        dims_used = set()

        def add(name: str, path_val: Any, body_val: Any, status: int, behavior: str, dim: str, hdrs: Optional[Dict[str, str]] = None):
            if dim in dims and len(cases) < cases_per_endpoint:
                h = {"Content-Type": "application/json"}
                if hdrs:
                    h.update(hdrs)
                cases.append(TestCaseModel(
                    name=f"{name} on {method} {path}",
                    method=method,
                    path=self._substitute_path_params(path, endpoint.params, path_val),
                    headers=h,
                    body=self._generate_body_with_value(endpoint.body_schema, body_val),
                    expected_status=status,
                    expected_behavior=behavior,
                    dimension=dim
                ))
                dims_used.add(dim)

        # Generate all candidate cases first, grouped by dimension
        candidates_by_dim: Dict[str, List[Dict[str, Any]]] = {}

        def queue(dim: str, name: str, path_val: Any, body_val: Any, status: int, behavior: str, hdrs: Optional[Dict[str, str]] = None):
            if dim not in candidates_by_dim:
                candidates_by_dim[dim] = []
            candidates_by_dim[dim].append({
                "name": name,
                "path_val": path_val,
                "body_val": body_val,
                "status": status,
                "behavior": behavior,
                "hdrs": hdrs
            })

        # 1. Boundary Values
        queue("boundary_values", "Boundary empty string", "", "", 400, "Reject empty string with 4xx or process gracefully")
        queue("boundary_values", "Boundary oversized 5k string", "A" * 50, "A" * 5000, 400, "Reject oversized payload with 400/413, no 500 crash")

        # 2. Type Coercion
        queue("type_coercion", "Type coercion string to integer", "not_a_number", "not-a-number", 422, "FastAPI / Pydantic rejects with 422 Unprocessable Entity")
        queue("type_coercion", "Type coercion null body", "1", None, 400, "Reject null or missing request body cleanly")

        # 3. Injection Payloads
        for inj_name, payload, dim in INJECTION_PAYLOADS[:3]:
            queue(dim, inj_name, payload, payload, 400, "Sanitize or reject injection payload; never leak SQL trace or 500")

        # 4. Auth Bypass
        queue("auth_bypass", "Auth bypass missing authorization", "1", "test", 401, "Require authenticated identity or validate public route safely")
        queue("auth_bypass", "Auth bypass forged invalid token", "1", "test", 401, "Reject invalid bearer token with 401 Unauthorized", {"Authorization": "Bearer malformed.jwt.signature"})

        # 5. Idempotency & Race
        queue("idempotency_race", "Duplicate mutation idempotency", "1", "idempotent_sample", 200, "Support idempotent execution without corruption", {"X-Idempotency-Key": "dup-test-uuid-001"})

        # 6. Unicode & Locale
        for uni_name, payload, dim in UNICODE_PAYLOADS[:2]:
            queue(dim, uni_name, payload, payload, 400, "Process UTF-8 or reject safely without encoding exception")

        # Now pick cases: first one per requested dimension (round-robin), then fill remaining slots
        for dim in dims:
            if dim in candidates_by_dim and len(cases) < cases_per_endpoint:
                c = candidates_by_dim[dim].pop(0)
                add(c["name"], c["path_val"], c["body_val"], c["status"], c["behavior"], dim, c["hdrs"])

        # Fill remaining slots with remaining candidates in dimension order
        for dim in dims:
            while dim in candidates_by_dim and candidates_by_dim[dim] and len(cases) < cases_per_endpoint:
                c = candidates_by_dim[dim].pop(0)
                add(c["name"], c["path_val"], c["body_val"], c["status"], c["behavior"], dim, c["hdrs"])

        return cases

    def _substitute_path_params(self, path: str, params: List[Dict[str, Any]], fill_value: Any) -> str:
        res = path
        for p in params:
            name = p.get("name")
            if p.get("in") == "path" and name and f"{{{name}}}" in res:
                res = res.replace(f"{{{name}}}", str(fill_value) if fill_value != "" else "1")
        return res

    def _generate_body_with_value(self, schema: Optional[Dict[str, Any]], val: Any) -> Optional[Dict[str, Any]]:
        if not schema or not isinstance(schema, dict):
            return {"payload": val} if val is not None else None
        props = schema.get("properties", {})
        if not props:
            return {"payload": val}
        body: Dict[str, Any] = {}
        for k, spec in props.items():
            t = spec.get("type", "string") if isinstance(spec, dict) else "string"
            body[k] = val if isinstance(val, int) else (1 if t == "integer" else (False if t == "boolean" else val))
        return body
