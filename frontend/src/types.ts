/**
 * Data contracts and response envelope types for api-fuzzer-alan-vo.
 */

export interface EndpointParam {
  name: string;
  in: string;
  required: boolean;
  schema?: Record<string, unknown>;
}

export interface EndpointSummary {
  method: string;
  path: string;
  summary: string;
  params: EndpointParam[];
  body_schema?: Record<string, unknown> | null;
  responses: string[];
}

export interface Spec {
  id: string;
  name: string;
  version: string;
  format: string;
  endpoints_count: number;
  endpoints: EndpointSummary[];
  created_at: string;
  created_by: string;
}

export interface FuzzJob {
  id: string;
  spec_id: string;
  target_base_url: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  total_cases: number;
  passed_cases: number;
  findings_count: number;
  created_at: string;
  completed_at?: string | null;
  triggered_by: string;
}

export type FindingSeverity = 'critical' | 'moderate' | 'minor' | 'pass';

export interface TestResult {
  id: string;
  case_id: string;
  job_id: string;
  test_name: string;
  endpoint: string;
  method: string;
  dimension: string;
  status_code: number | null;
  latency_ms: number;
  response_body: string | null;
  error_message: string | null;
  severity: FindingSeverity;
  reasoning: string;
  reproduction_curl: string;
  advisory_notes?: string | null;
  created_at: string;
}

export interface FuzzJobDetail {
  job: FuzzJob;
  results: TestResult[];
}

export interface StatsOverview {
  total_specs: number;
  total_jobs: number;
  total_cases_fuzzed: number;
  total_findings: number;
  findings_by_severity: {
    critical: number;
    moderate: number;
    minor: number;
    pass: number;
  };
  findings_by_dimension: Record<string, number>;
}

export interface EvaluationMetrics {
  benchmark_cases: number;
  baseline_accuracy: number;
  heuristic_accuracy: number;
  precision_critical: number;
  recall_critical: number;
  f1_score: number;
  dimension_metrics: Record<string, { cases: number; accuracy: number }>;
  evaluated_at: string;
  execution_latency_ms: number;
}

export interface User {
  user_id: string;
  email: string;
  roles: string[];
  auth_method: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in_seconds: number;
  user_id: string;
  email: string;
  roles: string[];
}
