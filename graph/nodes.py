from __future__ import annotations

import json
import os
import re

import numpy as np
import pandas as pd

from agents.llm import structured_call
from analysis.comparisons import compare_periods
from analysis.profiling import profile_data as run_profile
from graph.state import InvestigationState
from models.schemas import (CriticReview, Hypothesis, HypothesisSet, QuestionPlan,
                            SynthesisChoice, TestContract, TestPlanSet)
from tools.registry import ANALYSIS_TOOLS

MONTHS = {name.lower(): index for index, name in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1
)}
ALLOWED_TESTS = {"contribution", "mix", "data_quality", "trend"}


def profile_data(state: InvestigationState) -> dict:
    try:
        data, info = run_profile(state["dataset"])
        return {"dataset": data, "dataset_info": info, "error": None, "warning": None}
    except Exception as exc:
        return {"error": str(exc)}


def _period_defaults(question: str, info: dict) -> tuple[str, str]:
    date_col = info["date_columns"][0] if info["date_columns"] else None
    if not date_col:
        return "", ""
    periods = [pd.Period(value, freq="M") for value in info.get("date_periods", {}).get(date_col, [])]
    if len(periods) < 2:
        return "", ""
    month_match = re.search(r"\b(" + "|".join(MONTHS) + r")\b(?:\s+(20\d{2}))?", question, re.I)
    if month_match:
        month = MONTHS[month_match.group(1).lower()]
        if month_match.group(2):
            requested = pd.Period(year=int(month_match.group(2)), month=month, freq="M")
        else:
            matching_months = [period for period in periods if period.month == month]
            if not matching_months:
                raise ValueError(f"The requested month {month_match.group(1)} is not present in the dataset.")
            requested = max(matching_months)
        earlier = requested - 1
        if requested in periods and earlier in periods:
            return str(earlier), str(requested)
        raise ValueError(f"The requested month {requested} and its previous month are not both present in the dataset.")
    return str(periods[-2]), str(periods[-1])


def _fallback_plan(question: str, info: dict) -> QuestionPlan:
    columns = info.get("likely_metrics") or info["numeric_columns"]
    if not columns:
        raise ValueError("No numeric metric columns were detected. Add a numeric measure such as revenue or units.")
    question_lower = question.lower()
    metric = next((column for column in info["numeric_columns"] if str(column).lower() in question_lower), columns[0])
    date_column = info["date_columns"][0] if info["date_columns"] else None
    period_a, period_b = _period_defaults(question, info)
    return QuestionPlan(metric=metric, date_column=date_column, period_a=period_a, period_b=period_b,
                        question_type="root_cause", candidate_dimensions=info["likely_dimensions"])


def parse_question(state: InvestigationState) -> dict:
    info = state["dataset_info"]
    warning = None
    try:
        prompt = (
            "Interpret the business question as a dated comparison. Use only exact column names in the schema. "
            "Choose the named month and its previous calendar month when both are available; otherwise choose the latest two available months. "
            "Never invent columns. Return candidate dimensions only from categorical_columns.\n"
            f"Question: {state['question']}\nSchema: {json.dumps(info, default=str)}"
        )
        plan = structured_call(QuestionPlan, prompt)
        gemma_used_parse = True
        if plan is None:
            gemma_used_parse = False
            plan = _fallback_plan(state["question"], info)
            if os.getenv("GEMMA_API_KEY"):
                warning = "Gemma response could not be validated; used the local parser instead."
        else:
            if plan.metric not in info["numeric_columns"]:
                raise ValueError(f"Gemma selected unknown metric: {plan.metric}")
            if plan.date_column not in info["date_columns"]:
                raise ValueError(f"Gemma selected unknown date column: {plan.date_column}")
            plan.period_a = str(pd.Period(plan.period_a, freq="M"))
            plan.period_b = str(pd.Period(plan.period_b, freq="M"))
            available_periods = set(info.get("date_periods", {}).get(plan.date_column, []))
            if plan.period_a not in available_periods or plan.period_b not in available_periods:
                raise ValueError("Gemma selected a period that is not present in the dataset.")
            allowed_dimensions = set(info["likely_dimensions"])
            plan.candidate_dimensions = [d for d in plan.candidate_dimensions if d in allowed_dimensions]
    except Exception as exc:
        try:
            plan = _fallback_plan(state["question"], info)
        except Exception as fallback_exc:
            return {"error": str(fallback_exc)}
        if os.getenv("GEMMA_API_KEY"):
            warning = f"Gemma parsing encountered an issue; used the local parser instead."
        gemma_used_parse = False
    return {
        "metric": plan.metric, "date_column": plan.date_column,
        "period_a": plan.period_a, "period_b": plan.period_b,
        "question_type": plan.question_type,
        "candidate_dimensions": plan.candidate_dimensions,
        "warning": warning, "error": None,
        "gemma_used_parse": gemma_used_parse,
    }


def calculate_baseline(state: InvestigationState) -> dict:
    try:
        if not state.get("date_column"):
            return {"error": "No date column was detected; a dated comparison is required for this question."}
        if state.get("metric") not in state.get("dataset_info", {}).get("numeric_columns", []):
            return {"error": "The selected metric is not a detected numeric column."}
        baseline = compare_periods(state["dataset"], state["metric"], state["date_column"],
                                   state["period_a"], state["period_b"])
        return {"overall_change": baseline, "error": None}
    except Exception as exc:
        return {"error": str(exc)}


def _fallback_hypotheses(state: InvestigationState) -> list[Hypothesis]:
    dimensions = state.get("candidate_dimensions", [])
    hypotheses: list[Hypothesis] = []
    for dimension in dimensions[:3]:
        name = str(dimension).lower()
        test = "mix" if any(term in name for term in ("product", "item", "category", "sku")) else "contribution"
        hypotheses.append(Hypothesis(id=f"h{len(hypotheses) + 1}",
                                     statement=(f"A shift in the {dimension} mix explains a measurable part of the change." if test == "mix"
                                                else f"Changes by {dimension} explain a measurable part of the change."),
                                     test=test, dimension=dimension))
    hypotheses.append(Hypothesis(id=f"h{len(hypotheses) + 1}",
                                 statement="Missing, duplicated, or incomplete records explain a material part of the change.",
                                 test="data_quality"))
    if len(hypotheses) < 5:
        hypotheses.append(Hypothesis(id=f"h{len(hypotheses) + 1}",
                                     statement="The observed change may be part of a recurring seasonal pattern.",
                                     test="trend"))
    if len(hypotheses) < 3:
        hypotheses.insert(0, Hypothesis(id="h1", statement="A longer-term trend, rather than a one-off shift, may explain the comparison.",
                                        test="trend"))
        hypotheses = [item.model_copy(update={"id": f"h{i}"}) for i, item in enumerate(hypotheses, 1)]
    return hypotheses[:5]


def generate_hypotheses(state: InvestigationState) -> dict:
    allowed = set(state.get("candidate_dimensions", []))
    prompt = (
        "Propose 3–5 competing, measurable explanations for this comparison. Every explanation must be testable with the supplied "
        "categorical dimensions or data quality/trend checks. Use only the allowed dimension names. Do not state causation.\n"
        f"Question: {state['question']}\nBaseline: {json.dumps(state['overall_change'])}\n"
        f"Dimensions: {json.dumps(sorted(allowed))}\nAvailable test types: {sorted(ALLOWED_TESTS)}"
    )
    try:
        result = structured_call(HypothesisSet, prompt)
        gemma_used_hypotheses = result is not None
        hypotheses = result.hypotheses if result else _fallback_hypotheses(state)
        if not 3 <= len(hypotheses) <= 5:
            raise ValueError("Hypothesis count must be between 3 and 5.")
        for item in hypotheses:
            if item.test not in ALLOWED_TESTS or (item.dimension is not None and item.dimension not in allowed):
                raise ValueError("Hypothesis refers to an unsupported test or dimension.")
            if item.test in {"contribution", "mix"} and item.dimension is None:
                raise ValueError("Dimension hypotheses must select an available dimension.")
        hypotheses = [item.model_copy(update={"id": f"h{i}"}) for i, item in enumerate(hypotheses, 1)]
        return {"hypotheses": [item.model_dump() for item in hypotheses], "gemma_used_hypotheses": gemma_used_hypotheses, "error": None}
    except Exception as exc:
        return {"hypotheses": [item.model_dump() for item in _fallback_hypotheses(state)],
                "warning": "Used locally generated hypotheses." if os.getenv("GEMMA_API_KEY") else None,
                "gemma_used_hypotheses": False,
                "error": None}


def _decision_rules(test: str) -> list[str]:
    if test in {"contribution", "mix"}:
        return ["SUPPORTED at >=50% of net change; WEAKENED at >=5% and <50%; REJECTED below 5%."]
    if test == "data_quality":
        return ["REJECTED if max missingness <5%, duplicate rate <2%, and there are no missing months.",
                "SUPPORTED if missingness >=20% or duplicate rate >=10%; otherwise material flags are WEAKENED."]
    return ["UNTESTABLE with fewer than 24 observed months; a seasonal claim needs repeated yearly history."]


def _decision_thresholds(test: str) -> tuple[float | None, float | None]:
    if test in {"contribution", "mix"}:
        return 0.50, 0.05
    if test == "data_quality":
        return 0.20, 0.05
    return None, None


def plan_tests(state: InvestigationState) -> dict:
    hypotheses = state.get("hypotheses", [])
    prompt = (
        "Create one falsification contract for each supplied hypothesis. Use only these tools: contribution, mix, data_quality, trend. "
        "Use only exact metric/dimension names from the dataset. For contribution/mix thresholds are fractions: support 0.50, weaken 0.05. "
        "Data quality is rejected below 5% missingness and 2% duplicates when no months are missing; it is supported at 20% missingness or 10% duplicates. "
        "For data quality use threshold fields 0.20 and 0.05. For trend use null threshold fields. A seasonal explanation is untestable with fewer than 24 observed months. "
        "Each contract must name required evidence.\n"
        f"Hypotheses: {json.dumps(hypotheses)}\nMetric: {state.get('metric')}\nDimensions: {json.dumps(state.get('candidate_dimensions', []))}"
    )
    try:
        result = structured_call(TestPlanSet, prompt)
        gemma_used_plan = True
        if result is None:
            raise ValueError("Gemma is not configured.")
        ids = {h["id"] for h in hypotheses}
        dimensions = set(state.get("candidate_dimensions", []))
        hypotheses_by_id = {h["id"]: h for h in hypotheses}
        contracts = result.contracts
        if {contract.hypothesis_id for contract in contracts} != ids or len(contracts) != len(ids):
            raise ValueError("Test plan must cover every hypothesis exactly once.")
        for contract in contracts:
            if contract.test not in ALLOWED_TESTS or (contract.dimension and contract.dimension not in dimensions):
                raise ValueError("Test plan used an unsupported tool or dimension.")
            hypothesis = hypotheses_by_id[contract.hypothesis_id]
            if contract.test != hypothesis["test"] or contract.dimension != hypothesis.get("dimension"):
                raise ValueError("Test plan must execute the test and dimension attached to its hypothesis.")
            if contract.metric and contract.metric != state["metric"]:
                raise ValueError("Test plan used an unsupported metric.")
            if contract.test in {"contribution", "mix"} and not contract.dimension:
                raise ValueError("Dimension tests must select an existing dimension.")
            if contract.support_threshold is not None and contract.weaken_threshold is not None and contract.support_threshold <= contract.weaken_threshold:
                raise ValueError("Support threshold must exceed weaken threshold.")
            expected_support, expected_weaken = _decision_thresholds(contract.test)
            if (contract.support_threshold, contract.weaken_threshold) != (expected_support, expected_weaken):
                raise ValueError("Use the visible, test-specific MVP decision thresholds.")
    except Exception:
        contracts = [TestContract(
            hypothesis_id=h["id"], test=h["test"], metric=state["metric"], dimension=h.get("dimension"),
            support_threshold=_decision_thresholds(h["test"])[0],
            weaken_threshold=_decision_thresholds(h["test"])[1],
            required_evidence=(
                ["period A and period B values by dimension", "contribution to overall change"]
                if h["test"] in {"contribution", "mix"} else
                ["missing-value rate", "duplicate records", "date gaps"] if h["test"] == "data_quality" else
                ["monthly totals", "number of observed months"]
            ),
            decision_rules=(
                ["SUPPORTED at >=50% of net change; WEAKENED at >=5% and <50%; REJECTED below 5%."]
                if h["test"] in {"contribution", "mix"} else
                ["REJECTED if max missingness <5%, duplicate rate <2%, and there are no missing months.",
                 "SUPPORTED if missingness >=20% or duplicate rate >=10%; otherwise material flags are WEAKENED."]
                if h["test"] == "data_quality" else
                ["UNTESTABLE with fewer than 24 observed months; a seasonal claim needs repeated yearly history."]
            ),
        ) for h in hypotheses]
        gemma_used_plan = False
    contracts = [contract.model_copy(update={
        "decision_rules": _decision_rules(contract.test),
        "support_threshold": _decision_thresholds(contract.test)[0],
        "weaken_threshold": _decision_thresholds(contract.test)[1],
    }) for contract in contracts]
    plans = [contract.model_dump() for contract in contracts]
    return {"test_plans": plans, "iteration": state.get("iteration", 0) + 1, "gemma_used_plan": gemma_used_plan, "error": None}


def execute_test(state: InvestigationState) -> dict:
    frame = state["dataset"]
    results = []
    for contract in state.get("test_plans", []):
        try:
            test = contract["test"]
            if test == "contribution":
                result = ANALYSIS_TOOLS["contribution"](frame, state["metric"], state["date_column"],
                                                         state["period_a"], state["period_b"], contract["dimension"])
            elif test == "mix":
                result = ANALYSIS_TOOLS["mix"](frame, state["metric"], state["date_column"],
                                                state["period_a"], state["period_b"], contract["dimension"])
            elif test == "data_quality":
                result = ANALYSIS_TOOLS["data_quality"](frame, state.get("date_column"))
            elif test == "trend":
                result = ANALYSIS_TOOLS["trend"](frame, state["metric"], state["date_column"])
            else:
                raise ValueError(f"Unregistered analysis tool: {test}")
            results.append({"hypothesis_id": contract["hypothesis_id"], "test": test,
                            "contract": contract, "result": result, "error": None})
        except Exception as exc:
            results.append({"hypothesis_id": contract["hypothesis_id"], "test": contract["test"],
                            "contract": contract, "result": None, "error": str(exc)})
    return {"test_results": results, "error": None}


def verify_result(state: InvestigationState) -> dict:
    checks = []
    try:
        recomputed = compare_periods(state["dataset"], state["metric"], state["date_column"],
                                     state["period_a"], state["period_b"])
        shown = state["overall_change"]
        baseline_ok = all(np.isclose(recomputed[key], shown[key], rtol=1e-9, atol=1e-8)
                          for key in ("value_a", "value_b", "absolute_change"))
        checks.append({"check": "baseline_recomputed", "passed": baseline_ok})
    except Exception as exc:
        checks.append({"check": "baseline_recomputed", "passed": False, "detail": str(exc)})
    for item in state.get("test_results", []):
        check = {"check": f"evidence_{item['hypothesis_id']}", "passed": False}
        try:
            if item.get("error"):
                raise ValueError(item["error"])
            test = item["test"]
            frame = state["dataset"]
            contract = item["contract"]
            if test in {"contribution", "mix"}:
                expected = ANALYSIS_TOOLS[test](
                    frame, state["metric"], state["date_column"],
                    state["period_a"], state["period_b"], contract["dimension"],
                )
            elif test == "data_quality":
                expected = ANALYSIS_TOOLS[test](frame, state.get("date_column"))
            elif test == "trend":
                expected = ANALYSIS_TOOLS[test](frame, state["metric"], state["date_column"])
            else:
                raise ValueError(f"Unregistered analysis tool: {test}")
            actual = item.get("result")
            if actual is None:
                raise ValueError("The analysis tool returned no result.")
            passed = _results_match(expected, actual)
            check["passed"] = passed
            if not passed:
                check["detail"] = "Recomputed analysis output does not match the recorded result."
        except Exception as exc:
            check["detail"] = str(exc)
        checks.append(check)
    verification = {"passed": all(check["passed"] for check in checks), "checks": checks}
    return {"verification": verification, "error": None}


def _results_match(expected, actual) -> bool:
    """Compare nested deterministic tool outputs, allowing only tiny float drift."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        return (expected.keys() == actual.keys() and
                all(_results_match(expected[key], actual[key]) for key in expected))
    if isinstance(expected, list) and isinstance(actual, list):
        return len(expected) == len(actual) and all(
            _results_match(left, right) for left, right in zip(expected, actual)
        )
    if isinstance(expected, (int, float, np.number)) and not isinstance(expected, (bool, np.bool_)):
        if not isinstance(actual, (int, float, np.number)) or isinstance(actual, (bool, np.bool_)):
            return False
        return bool(np.isclose(expected, actual, rtol=1e-9, atol=1e-8, equal_nan=True))
    return expected == actual


def _fallback_verdict(hypothesis: dict, test_result: dict | None, contract: dict) -> dict:
    if not test_result or test_result.get("error") or not test_result.get("result"):
        return {"hypothesis_id": hypothesis["id"], "verdict": "UNTESTABLE",
                "rationale": "The required evidence could not be calculated from the available columns."}
    result, test = test_result["result"], hypothesis["test"]
    if test == "trend":
        periods = result["period_count"]
        verdict = "UNTESTABLE" if periods < 24 else "WEAKENED"
        rationale = (f"Only {periods} monthly periods are available; at least 24 are required to compare recurring seasonality."
                     if verdict == "UNTESTABLE" else "Historical months are available, but a seasonal pattern needs comparison across years.")
        return {"hypothesis_id": hypothesis["id"], "verdict": verdict, "rationale": rationale}
    if test == "data_quality":
        missing_pct = max((col["pct"] for col in result["missing"].values()), default=0.0)
        duplicate_pct = result["duplicate_rows"] / max(result["row_count"], 1) * 100
        flags = missing_pct >= 5 or duplicate_pct >= 2 or bool(result["missing_months"])
        verdict = "SUPPORTED" if missing_pct >= 20 or duplicate_pct >= 10 else "WEAKENED" if flags else "REJECTED"
        rationale = (f"Data quality check found a maximum missingness of {missing_pct:.1f}%, duplicate rate of {duplicate_pct:.1f}%, "
                     f"and {len(result['missing_months'])} missing months.")
        return {"hypothesis_id": hypothesis["id"], "verdict": verdict, "rationale": rationale}
    if test == "mix":
        mix_effect_pct = result.get("mix_effect_contribution_pct")
        if mix_effect_pct is None:
            return {"hypothesis_id": hypothesis["id"], "verdict": "UNTESTABLE",
                    "rationale": "A true mix effect needs a units/quantity column; only metric shares were available."}
        threshold = contract["support_threshold"] * 100
        weaken = contract["weaken_threshold"] * 100
        verdict = "SUPPORTED" if mix_effect_pct >= threshold else "WEAKENED" if mix_effect_pct >= weaken else "REJECTED"
        return {"hypothesis_id": hypothesis["id"], "verdict": verdict,
                "rationale": f"The unit-share shift accounts for {mix_effect_pct:.1f}% of the net change when valued at period A prices.",
                "contribution_pct": mix_effect_pct, "alternative_explanation": "Volume and price effects can also contribute to the total change."}
    rows = result.get("results", [])
    if not rows:
        return {"hypothesis_id": hypothesis["id"], "verdict": "UNTESTABLE", "rationale": "No dimension groups were available."}
    total_change = result.get("total_change", 0)
    if not total_change:
        return {"hypothesis_id": hypothesis["id"], "verdict": "REJECTED", "rationale": "The selected dimension has no net contribution to the overall change."}
    contributions = [abs(row.get("contribution_pct", 0)) for row in rows]
    customer_dimension = str(contract.get("dimension", "")).lower() in {"customer", "client", "account"}
    lost_rows = [row for row in rows if row.get("value_a", 0) > 0 and row.get("value_b", 0) == 0]
    if customer_dimension and lost_rows:
        contribution = sum(abs(row.get("contribution_pct", 0)) for row in lost_rows) / 100
        top = max(lost_rows, key=lambda row: abs(row.get("contribution_pct", 0)))
        evidence_subject = "lost customers"
    else:
        contribution = max(contributions, default=0) / 100
        top = max(rows, key=lambda row: abs(row.get("contribution_pct", 0)))
        evidence_subject = "the largest group"
    threshold = contract["support_threshold"]
    weaken = contract["weaken_threshold"]
    verdict = "SUPPORTED" if contribution >= threshold else "WEAKENED" if contribution >= weaken else "REJECTED"
    measured = contribution * 100 if customer_dimension and lost_rows else abs(top.get("contribution_pct", 0))
    if customer_dimension and lost_rows:
        rationale = f"Lost customers account for {measured:.1f}% of the net change."
    else:
        rationale = (f"The largest {contract.get('dimension')} group, {top.get(contract.get('dimension'))}, "
                     f"accounts for {measured:.1f}% of the net change across this dimension.")
    return {"hypothesis_id": hypothesis["id"], "verdict": verdict, "rationale": rationale,
            "contribution_pct": measured,
            "top_group": top.get(contract.get("dimension")),
            "alternative_explanation": "Other dimensions may also contribute; these grouped changes are not causal proof."}


def critic(state: InvestigationState) -> dict:
    results = {item["hypothesis_id"]: item for item in state.get("test_results", [])}
    contracts = {item["hypothesis_id"]: item for item in state.get("test_plans", [])}
    verdicts = [_fallback_verdict(h, results.get(h["id"]), contracts.get(h["id"], {}))
                for h in state.get("hypotheses", [])]
    verification = state.get("verification", {})
    checks = {item["check"]: item["passed"] for item in verification.get("checks", [])}
    baseline_verified = checks.get("baseline_recomputed", False)
    for item in verdicts:
        evidence_verified = checks.get(f"evidence_{item['hypothesis_id']}", False)
        if not baseline_verified or not evidence_verified:
            item["verdict"] = "UNTESTABLE"
            item["rationale"] = "The associated calculation did not pass verification, so this explanation is not reported as evidence-backed."
    # Let Gemma challenge the deterministic evidence, but only accept schema-valid verdicts for known IDs.
    prompt = (
        "Act as an adversarial data critic. Review the hypothesis, contract, deterministic evidence, and verification. "
        "Choose SUPPORTED, WEAKENED, REJECTED, or UNTESTABLE for each known hypothesis. Consider alternative explanations. "
        "Do not invent data or claim causation.\n"
        f"Question: {state['question']}\nBaseline: {json.dumps(state['overall_change'])}\n"
        f"Evidence: {json.dumps(state.get('test_results', []), default=str)}\nVerification: {json.dumps(state.get('verification', {}))}"
    )
    gemma_used_critic = False
    try:
        review = structured_call(CriticReview, prompt)
        if review:
            gemma_used_critic = True
            known = {item["hypothesis_id"] for item in verdicts}
            llm_by_id = {item.hypothesis_id: item for item in review.verdicts if item.hypothesis_id in known}
            # Keep numeric verdicts evidence-grounded; retain the critic's challenge as a note.
            for item in verdicts:
                if item["hypothesis_id"] in llm_by_id:
                    note = llm_by_id[item["hypothesis_id"]].rationale
                    alternative = llm_by_id[item["hypothesis_id"]].alternative_explanation
                    unsafe_claim = lambda value: value and (re.search(r"\d", value) or re.search(r"\b(cause|caused|causing|prove|proves|proven)\b", value, re.I))
                    if not unsafe_claim(note):
                        item["critic_note"] = note
                    if alternative and not unsafe_claim(alternative):
                        item["alternative_explanation"] = alternative
    except Exception:
        pass
    return {"verdicts": verdicts, "evidence": state.get("test_results", []),
            "gemma_used_critic": gemma_used_critic,
            "needs_more_tests": any(not results.get(h["id"]) for h in state.get("hypotheses", [])), "error": None}


def route_next(state: InvestigationState) -> str:
    if state.get("needs_more_tests") and state.get("iteration", 0) < 2:
        return "more_tests"
    return "synthesize"


def final_synthesis(state: InvestigationState) -> dict:
    change = state["overall_change"]
    verdicts = {item["hypothesis_id"]: item for item in state.get("verdicts", [])}
    hypotheses = {item["id"]: item for item in state.get("hypotheses", [])}
    winner = next((hypotheses[item["hypothesis_id"]] for item in state.get("verdicts", [])
                   if item["verdict"] == "SUPPORTED"), None)
    gemma_used_synthesis = False
    try:
        choice = structured_call(SynthesisChoice, (
            "Select the strongest supported hypothesis from this verified investigation. Choose only an existing hypothesis ID "
            "with verdict SUPPORTED, or null when none is supported. Return only the selected ID; do not add metrics or claim causation.\n"
            f"Question: {state['question']}\nHypotheses: {json.dumps(state.get('hypotheses', []))}\n"
            f"Verified verdicts: {json.dumps(state.get('verdicts', []))}\nBaseline: {json.dumps(state['overall_change'])}"
        ))
        if choice:
            gemma_used_synthesis = True
        if choice and choice.strongest_supported_hypothesis_id:
            chosen_id = choice.strongest_supported_hypothesis_id
            if verdicts.get(chosen_id, {}).get("verdict") == "SUPPORTED":
                winner = hypotheses[chosen_id]
    except Exception:
        pass
    pct = change.get("percent_change")
    delta_text = f"{pct:+.1f}%" if pct is not None else "percentage change unavailable because the earlier period totals zero"
    lines = [f"{change['metric']} changed from {change['period_a']} to {change['period_b']} by {change['absolute_change']:,.2f} ({delta_text})."]
    if winner:
        verdict = verdicts[winner["id"]]
        lines.append(f"The strongest supported explanation is: {winner['statement']} {verdict['rationale']}")
    else:
        lines.append("No explanation was strongly supported by the available evidence.")
    for item in state.get("verdicts", []):
        hypothesis = hypotheses[item["hypothesis_id"]]
        lines.append(f"{item['verdict']}: {hypothesis['statement']} {item['rationale']}")
    lines.append("These results describe contribution and association; they do not establish causation.")
    return {"final_report": "\n\n".join(lines), "gemma_used_synthesis": gemma_used_synthesis, "error": None}
