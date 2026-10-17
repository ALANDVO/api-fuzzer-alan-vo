# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to `api-fuzzer-alan-vo` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-12

### Added
- **Full-Stack Application Architecture:**
  - FastAPI modular backend in `backend/app` with SQLite persistent database, parameterized SQL, and audit logging.
  - React 19 + TypeScript + Vite responsive dashboard in `frontend/src`.
- **OpenAPI Schema Ingestion:**
  - Support for OpenAPI 3.0, 3.1, and Swagger specifications in JSON and YAML formats.
  - Semantic extraction of endpoints, parameters, request body schemas, and response codes.
- **Adversarial Mutation Engine:**
  - Deterministic test case generation across 6 security attack dimensions:
    1. Boundary values (min/max limits, empty strings, 5KB+ oversized payloads).
    2. Type coercion (string-to-integer, null body injection, unexpected arrays/objects).
    3. Injection payloads (SQL injection, XSS script injection, path traversal, CRLF header injection).
    4. Auth/permission bypass (missing bearer tokens, forged signatures, unauthorized escalation).
    5. Idempotency and race conditions (duplicate requests, concurrency simulation).
    6. Unicode and locale edge cases (emoji bombs, RTL overrides, null-byte injections, non-ASCII casing).
- **Live Fuzz Runner & Execution:**
  - Asynchronous execution against target endpoints with timeout guards and latency profiling.
  - Response diffing against OpenAPI contract definitions.
- **Deterministic Severity Scoring:**
  - Rule-based classification: `critical`, `moderate`, `minor`, `pass`.
  - Automatic single-line `curl` reproduction command generation for every finding.
- **Multi-Provider LLM Advisory Adapter:**
  - Optional advisory reasoning grounded in actual records supporting OpenAI, Anthropic, Gemini, and Ollama.
  - Server-side only key handling via `LLM_API_KEY` with automatic error message credential redaction.
  - Fully offline deterministic baseline execution without API keys.
- **OIDC & SAML Brokered Authentication:**
  - Keycloak realm configuration with PKCE, state/nonce verification, and standard roles (`viewer`, `operator`, `admin`).
  - Secure local demo mode refusing production startup.
  - In-memory access token storage avoiding localStorage token persistence.
- **Reporting & Export:**
  - Structured JSON export.
  - GitHub-Flavored Markdown security audit reports.
  - SARIF 2.1.0 output for GitHub Code Scanning integration.
- **AI/ML Evaluation Benchmark:**
  - Curated 24-case ground-truth dataset across 6 dimensions measuring accuracy, critical precision, recall, and F1-score.

### Fixed
- Restored the missing ground-truth benchmark dataset `backend/app/data/benchmark_dataset.json` (24 labeled cases across 6 attack dimensions), restoring the AI/ML evaluation benchmark endpoint and reactivating `test_benchmark_dataset_integrity` and `test_run_evaluation_benchmark_metrics`.
- Restored the missing frontend sample OpenAPI target `frontend/src/data/sample_spec.json` consumed by `SpecManager` (PetStore-style schema), fixing TypeScript typecheck and the `FuzzJobRunner`/`SpecManager` tests.
- Anchored the `.gitignore` `data/` pattern to the repository root (`/data/`) so product data directories are no longer ignored alongside local SQLite databases.

Maintainer: Alan Vo <alanvo@gmail.com>
