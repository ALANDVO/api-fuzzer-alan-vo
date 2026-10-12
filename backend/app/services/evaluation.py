"""AI/ML evaluation framework with labeled ground-truth benchmark and metrics calculation."""
import json
import os
import pathlib
import time
from typing import Any, Dict, List
from backend.app.services.severity_classifier import SeverityClassifier

_DATASET_FILE = pathlib.Path(__file__).parent.parent / "data" / "benchmark_dataset.json"


def load_benchmark_dataset() -> List[Dict[str, Any]]:
    """Load curated benchmark dataset of 24 labeled API scenarios across 6 attack dimensions."""
    if _DATASET_FILE.exists():
        return json.loads(_DATASET_FILE.read_text())
    return []


BENCHMARK_DATASET = load_benchmark_dataset()


def run_evaluation_benchmark() -> Dict[str, Any]:
    """Execute evaluation benchmark comparing naive status baseline vs heuristic classifier."""
    classifier = SeverityClassifier()
    start_time = time.perf_counter()
    dataset = BENCHMARK_DATASET or load_benchmark_dataset()

    naive_correct = 0
    heuristic_correct = 0
    total = len(dataset)

    tp = 0
    fp = 0
    fn = 0
    tn = 0

    dimension_breakdown: Dict[str, Dict[str, int]] = {}

    for item in dataset:
        dim = item["dimension"]
        gt = item["ground_truth"]
        if dim not in dimension_breakdown:
            dimension_breakdown[dim] = {"total": 0, "correct": 0}
        dimension_breakdown[dim]["total"] += 1

        # Naive status code baseline: only checks status >= 500 -> critical, 4xx -> pass, 200 -> pass
        status = item["status"]
        if status >= 500:
            naive_pred = "critical"
        elif status in (400, 401, 403, 404, 412, 413, 422):
            naive_pred = "pass"
        else:
            naive_pred = "pass"

        if naive_pred == gt:
            naive_correct += 1

        pred_sev, _, _ = classifier.classify(
            test_name=item["test_name"],
            dimension=item["dimension"],
            method=item["method"],
            url=item["url"],
            headers={},
            body=None,
            expected_status=400,
            actual_status=item["status"],
            response_body=item["response"],
            latency_ms=item["latency_ms"]
        )

        if pred_sev == gt:
            heuristic_correct += 1
            dimension_breakdown[dim]["correct"] += 1

        if pred_sev == "critical" and gt == "critical":
            tp += 1
        elif pred_sev == "critical" and gt != "critical":
            fp += 1
        elif pred_sev != "critical" and gt == "critical":
            fn += 1
        else:
            tn += 1

    elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
    baseline_acc = round(naive_correct / total, 4) if total > 0 else 0.0
    heuristic_acc = round(heuristic_correct / total, 4) if total > 0 else 0.0

    precision_crit = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall_crit = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * (precision_crit * recall_crit) / (precision_crit + recall_crit), 4) if (precision_crit + recall_crit) > 0 else 0.0

    dim_metrics: Dict[str, Dict[str, float]] = {}
    for d, stats in dimension_breakdown.items():
        dim_metrics[d] = {
            "cases": stats["total"],
            "accuracy": round(stats["correct"] / stats["total"], 4)
        }

    return {
        "benchmark_cases": total,
        "baseline_accuracy": baseline_acc,
        "heuristic_accuracy": heuristic_acc,
        "precision_critical": precision_crit,
        "recall_critical": recall_crit,
        "f1_score": f1,
        "dimension_metrics": dim_metrics,
        "execution_latency_ms": elapsed_ms
    }


if __name__ == "__main__":
    results = run_evaluation_benchmark()
    print("=== AI/ML Evaluation Benchmark Results ===")
    print(json.dumps(results, indent=2))
