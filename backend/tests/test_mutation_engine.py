"""Tests covering adversarial test case generation across all 6 attack dimensions."""
from backend.app.models.schemas import EndpointSummary
from backend.app.services.mutation_engine import MutationEngine


def test_mutation_engine_generates_all_dimensions():
    engine = MutationEngine()
    endpoint = EndpointSummary(
        method="POST",
        path="/api/accounts/{id}/transfer",
        summary="Transfer funds",
        params=[{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
        body_schema={
            "type": "object",
            "properties": {
                "amount": {"type": "integer"},
                "recipient": {"type": "string"}
            }
        },
        responses=["200", "400", "401", "422"]
    )

    cases = engine.build_cases(endpoint, cases_per_endpoint=10)
    assert len(cases) >= 6

    dimensions = {c.dimension for c in cases}
    assert "boundary_values" in dimensions
    assert "type_coercion" in dimensions
    assert "injection_payloads" in dimensions
    assert "auth_bypass" in dimensions

    # Assert path parameter substitution replaced {id} with concrete values
    for c in cases:
        assert "{id}" not in c.path


def test_mutation_dimension_filtering():
    engine = MutationEngine()
    endpoint = EndpointSummary(
        method="GET",
        path="/api/users",
        summary="List users",
        params=[],
        body_schema=None,
        responses=["200"]
    )

    # Only request boundary_values and unicode_locale
    cases = engine.build_cases(
        endpoint,
        dimensions=["boundary_values", "unicode_locale"],
        cases_per_endpoint=4
    )
    for c in cases:
        assert c.dimension in ("boundary_values", "unicode_locale")


def test_injection_payload_structure():
    engine = MutationEngine()
    endpoint = EndpointSummary(
        method="POST",
        path="/api/search",
        summary="Search endpoint",
        params=[],
        body_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        responses=["200"]
    )
    cases = engine.build_cases(endpoint, dimensions=["injection_payloads"], cases_per_endpoint=4)
    assert any("SQL Injection" in c.name or "XSS" in c.name for c in cases)
