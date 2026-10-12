"""AI/ML evaluation benchmark endpoints."""
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends
from backend.app.core.auth import TokenUser, require_role
from backend.app.models.schemas import EvaluationRunResponse
from backend.app.services.evaluation import run_evaluation_benchmark

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])


@router.get("/benchmark", response_model=EvaluationRunResponse)
def get_evaluation_benchmark(user: TokenUser = Depends(require_role("viewer"))) -> EvaluationRunResponse:
    """Execute the reproducible 24-case ground-truth evaluation benchmark and return precision/recall/F1 metrics."""
    results = run_evaluation_benchmark()
    return EvaluationRunResponse(
        benchmark_cases=results["benchmark_cases"],
        baseline_accuracy=results["baseline_accuracy"],
        heuristic_accuracy=results["heuristic_accuracy"],
        precision_critical=results["precision_critical"],
        recall_critical=results["recall_critical"],
        f1_score=results["f1_score"],
        dimension_metrics=results["dimension_metrics"],
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        execution_latency_ms=results["execution_latency_ms"]
    )
