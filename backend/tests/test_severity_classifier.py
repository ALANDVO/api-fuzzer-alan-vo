"""Tests covering severity evaluation logic and curl reproduction command synthesis."""
from backend.app.services.severity_classifier import SeverityClassifier


def test_classify_sql_injection_leak_critical():
    classifier = SeverityClassifier()
    sev, reasoning, curl = classifier.classify(
        test_name="SQLi test",
        dimension="injection_payloads",
        method="POST",
        url="http://127.0.0.1:8000/api/login",
        headers={"Content-Type": "application/json"},
        body={"username": "' OR 1=1 --"},
        expected_status=400,
        actual_status=500,
        response_body="sqlite3.OperationalError: near 'OR': syntax error",
        latency_ms=15.0
    )
    assert sev == "critical"
    assert "SQL" in reasoning
    assert "curl" in curl


def test_classify_path_traversal_critical():
    classifier = SeverityClassifier()
    sev, reasoning, _ = classifier.classify(
        test_name="Traversal test",
        dimension="injection_payloads",
        method="GET",
        url="http://127.0.0.1:8000/file",
        headers={},
        body=None,
        expected_status=404,
        actual_status=200,
        response_body="root:x:0:0:root:/root:/bin/bash",
        latency_ms=10.0
    )
    assert sev == "critical"
    assert "traversal" in reasoning.lower()


def test_classify_auth_bypass_critical():
    classifier = SeverityClassifier()
    sev, reasoning, _ = classifier.classify(
        test_name="Auth bypass test",
        dimension="auth_bypass",
        method="GET",
        url="http://127.0.0.1:8000/admin/secrets",
        headers={},
        body=None,
        expected_status=401,
        actual_status=200,
        response_body="{\"secret\": \"vault-key\"}",
        latency_ms=12.0
    )
    assert sev == "critical"
    assert "security violation" in reasoning.lower()


def test_classify_unhandled_500_critical():
    classifier = SeverityClassifier()
    sev, reasoning, _ = classifier.classify(
        test_name="Crash test",
        dimension="boundary_values",
        method="POST",
        url="http://127.0.0.1:8000/calc",
        headers={},
        body={"val": 999999999999},
        expected_status=400,
        actual_status=500,
        response_body="Internal Server Error",
        latency_ms=20.0
    )
    assert sev == "critical"


def test_classify_validation_mismatch_moderate():
    classifier = SeverityClassifier()
    sev, reasoning, _ = classifier.classify(
        test_name="Type coercion test",
        dimension="type_coercion",
        method="POST",
        url="http://127.0.0.1:8000/items",
        headers={},
        body={"price": "not-a-number"},
        expected_status=422,
        actual_status=200,
        response_body="{\"status\": \"saved\"}",
        latency_ms=10.0
    )
    assert sev == "moderate"


def test_classify_high_latency_minor():
    classifier = SeverityClassifier()
    sev, reasoning, _ = classifier.classify(
        test_name="Slow request",
        dimension="idempotency_race",
        method="GET",
        url="http://127.0.0.1:8000/items",
        headers={},
        body=None,
        expected_status=200,
        actual_status=200,
        response_body="{\"items\": []}",
        latency_ms=3100.0
    )
    assert sev == "minor"


def test_classify_normal_pass():
    classifier = SeverityClassifier()
    sev, _, _ = classifier.classify(
        test_name="Normal rejection",
        dimension="boundary_values",
        method="GET",
        url="http://127.0.0.1:8000/items?limit=-1",
        headers={},
        body=None,
        expected_status=400,
        actual_status=400,
        response_body="{\"detail\": \"Limit must be positive\"}",
        latency_ms=15.0
    )
    assert sev == "pass"
