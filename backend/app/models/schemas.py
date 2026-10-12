"""Pydantic request and response schemas for api-fuzzer-alan-vo."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EndpointParam(BaseModel):
    name: str
    in_location: str = Field(alias="in", default="query")
    required: bool = False
    schema_type: str = "string"


class EndpointSummary(BaseModel):
    method: str
    path: str
    summary: str = ""
    params: List[Dict[str, Any]] = Field(default_factory=list)
    body_schema: Optional[Dict[str, Any]] = None
    responses: List[str] = Field(default_factory=list)


class SpecUploadRequest(BaseModel):
    name: str
    version: Optional[str] = "1.0.0"
    raw_spec: str
    format: Optional[str] = "json"


class SpecResponse(BaseModel):
    id: str
    name: str
    version: str
    format: str
    endpoints_count: int
    endpoints: List[EndpointSummary]
    created_at: str
    created_by: str


class FuzzJobCreateRequest(BaseModel):
    spec_id: str
    target_base_url: str
    dimensions: List[str] = Field(
        default_factory=lambda: [
            "boundary_values",
            "type_coercion",
            "injection_payloads",
            "auth_bypass",
            "idempotency_race",
            "unicode_locale"
        ]
    )
    cases_per_endpoint: int = Field(default=6, ge=1, le=50)
    max_endpoints: int = Field(default=10, ge=1, le=100)
    enable_llm_advisory: bool = False


class TestCaseModel(BaseModel):
    name: str
    method: str
    path: str
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Optional[Any] = None
    expected_status: int = 200
    expected_behavior: str = "API handles request or validates with 4xx"
    dimension: str
    generated_by: str = "deterministic_engine"


class TestResultResponse(BaseModel):
    id: str
    case_id: str
    job_id: str
    test_name: str
    endpoint: str
    method: str
    dimension: str
    status_code: Optional[int]
    latency_ms: float
    response_body: Optional[str]
    error_message: Optional[str]
    severity: str  # pass, minor, moderate, critical
    reasoning: str
    reproduction_curl: str
    advisory_notes: Optional[str] = None
    created_at: str


class FuzzJobResponse(BaseModel):
    id: str
    spec_id: str
    target_base_url: str
    status: str
    total_cases: int
    passed_cases: int
    findings_count: int
    created_at: str
    completed_at: Optional[str]
    triggered_by: str


class FuzzJobDetailResponse(BaseModel):
    job: FuzzJobResponse
    results: List[TestResultResponse]


class AuditLogResponse(BaseModel):
    id: str
    timestamp: str
    user_id: str
    action: str
    resource: str
    details: Dict[str, Any]


class StatsOverviewResponse(BaseModel):
    total_specs: int
    total_jobs: int
    total_cases_fuzzed: int
    total_findings: int
    findings_by_severity: Dict[str, int]
    findings_by_dimension: Dict[str, int]


class EvaluationRunResponse(BaseModel):
    benchmark_cases: int
    baseline_accuracy: float
    heuristic_accuracy: float
    precision_critical: float
    recall_critical: float
    f1_score: float
    dimension_metrics: Dict[str, Dict[str, float]]
    evaluated_at: str
    execution_latency_ms: float


class AuthLoginRequest(BaseModel):
    email: str
    password: Optional[str] = "demo-password"
    role: Optional[str] = "operator"


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in_seconds: int
    user_id: str
    email: str
    roles: List[str]
