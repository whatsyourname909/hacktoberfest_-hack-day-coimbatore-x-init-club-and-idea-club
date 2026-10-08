from typing import Literal

from pydantic import BaseModel, Field


class QuestionPlan(BaseModel):
    """A constrained description of the comparison requested by the user."""

    metric: str = Field(description="Exact numeric column to analyze")
    date_column: str | None = Field(description="Exact date column, or null")
    period_a: str = Field(description="Earlier period in ISO date/month form")
    period_b: str = Field(description="Later period in ISO date/month form")
    question_type: str = Field(description="Short label, such as root_cause")
    candidate_dimensions: list[str] = Field(default_factory=list, description="Exact categorical columns that may explain the change")


class Hypothesis(BaseModel):
    id: str
    statement: str
    test: Literal["contribution", "mix", "data_quality", "trend"]
    dimension: str | None = None


class HypothesisSet(BaseModel):
    hypotheses: list[Hypothesis] = Field(min_length=3, max_length=5)


class TestContract(BaseModel):
    hypothesis_id: str
    test: Literal["contribution", "mix", "data_quality", "trend"]
    metric: str | None = None
    dimension: str | None = None
    support_threshold: float | None = Field(default=None, ge=0, le=1)
    weaken_threshold: float | None = Field(default=None, ge=0, le=1)
    required_evidence: list[str]
    decision_rules: list[str] = Field(default_factory=list)


class TestPlanSet(BaseModel):
    contracts: list[TestContract]


class HypothesisVerdict(BaseModel):
    hypothesis_id: str
    verdict: Literal["SUPPORTED", "WEAKENED", "REJECTED", "UNTESTABLE"]
    rationale: str
    alternative_explanation: str | None = None


class CriticReview(BaseModel):
    verdicts: list[HypothesisVerdict]


class SynthesisChoice(BaseModel):
    strongest_supported_hypothesis_id: str | None


class QuestionValidation(BaseModel):
    is_valid: bool
    reason: str | None = None
    rephrased_question: str | None = None

