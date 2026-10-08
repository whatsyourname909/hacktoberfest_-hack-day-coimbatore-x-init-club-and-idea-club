from typing import Any, TypedDict


class InvestigationState(TypedDict, total=False):
    question: str
    question_validated: bool
    dataset: Any
    dataset_info: dict[str, Any]
    metric: str
    date_column: str | None
    period_a: str
    period_b: str
    question_type: str
    candidate_dimensions: list[str]
    overall_change: dict[str, Any]
    hypotheses: list[dict[str, Any]]
    test_plans: list[dict[str, Any]]
    test_results: list[dict[str, Any]]
    verification: dict[str, Any]
    verdicts: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    iteration: int
    needs_more_tests: bool
    final_report: str | None
    error: str | None
    gemma_used_parse: bool
    gemma_used_hypotheses: bool
    gemma_used_plan: bool
    gemma_used_critic: bool
    gemma_used_synthesis: bool
    warning: str | None
