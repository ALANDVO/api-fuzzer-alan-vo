"""Tests covering AI/ML benchmark dataset evaluation and metrics calculation."""
from backend.app.services.evaluation import BENCHMARK_DATASET, run_evaluation_benchmark


def test_benchmark_dataset_integrity():
    assert len(BENCHMARK_DATASET) == 24
    dimensions = {item["dimension"] for item in BENCHMARK_DATASET}
    assert len(dimensions) == 6
    assert "injection_payloads" in dimensions
    assert "auth_bypass" in dimensions
    assert "boundary_values" in dimensions
    assert "type_coercion" in dimensions
    assert "idempotency_race" in dimensions
    assert "unicode_locale" in dimensions

    for item in BENCHMARK_DATASET:
        assert item["ground_truth"] in ("critical", "moderate", "minor", "pass")
        assert item["status"] >= 100


def test_run_evaluation_benchmark_metrics():
    results = run_evaluation_benchmark()
    assert results["benchmark_cases"] == 24
    assert 0.0 <= results["baseline_accuracy"] <= 1.0
    assert 0.0 <= results["heuristic_accuracy"] <= 1.0
    # The heuristic classifier should outperform or match the naive baseline
    assert results["heuristic_accuracy"] >= results["baseline_accuracy"]
    assert 0.0 <= results["precision_critical"] <= 1.0
    assert 0.0 <= results["recall_critical"] <= 1.0
    assert 0.0 <= results["f1_score"] <= 1.0
    assert "injection_payloads" in results["dimension_metrics"]
