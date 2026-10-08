import os
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from analysis.comparisons import breakdown_by_dimension, compare_periods, contribution_to_change, mix_analysis
from analysis.data_quality import data_quality_check
from analysis.trends import trend_analysis
from graph.nodes import (calculate_baseline, critic, execute_test, final_synthesis,
                         generate_hypotheses, parse_question, plan_tests,
                         profile_data, route_next, verify_result)
from agents.llm import structured_call
from models.schemas import QuestionPlan

ROOT = os.path.dirname(os.path.dirname(__file__))


class AnalysisToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame = pd.read_csv(os.path.join(ROOT, "data", "demo_sales.csv"))
        cls.frame["date"] = pd.to_datetime(cls.frame["date"])

    def test_period_baseline(self):
        result = compare_periods(self.frame, "revenue", "date", "2026-02", "2026-03")
        self.assertEqual(result["value_a"], 10_000_000)
        self.assertEqual(result["value_b"], 7_940_000)
        self.assertAlmostEqual(result["percent_change"], -20.6)

    def test_dimension_breakdown_and_contribution(self):
        for tool in (breakdown_by_dimension, contribution_to_change):
            result = tool(self.frame, "revenue", "date", "2026-02", "2026-03", "region")
            self.assertAlmostEqual(sum(row["contribution_pct"] for row in result["results"]), 100)
            self.assertAlmostEqual(max(abs(row["contribution_pct"]) for row in result["results"]), 14)
        customer = contribution_to_change(self.frame, "revenue", "date", "2026-02", "2026-03", "customer")
        churned = next(row for row in customer["results"] if row["customer"] == "Churned account")
        self.assertAlmostEqual(abs(churned["contribution_pct"]), 8)

    def test_mix_trend_and_quality(self):
        mix = mix_analysis(self.frame, "revenue", "date", "2026-02", "2026-03", "product")
        self.assertAlmostEqual(mix["mix_effect_contribution_pct"], 67, places=1)
        trend = trend_analysis(self.frame, "revenue", "date")
        self.assertEqual(trend["period_count"], 2)
        quality = data_quality_check(self.frame, "date")
        self.assertEqual(quality["duplicate_rows"], 0)
        self.assertEqual(quality["missing"], {})
        self.assertEqual(quality["missing_months"], [])


class InvestigationNodesTests(unittest.TestCase):
    def test_gemma_json_is_pydantic_validated(self):
        import agents.llm as llm_module

        class Response:
            content = '{"metric":"revenue","date_column":"date","period_a":"2026-02","period_b":"2026-03","question_type":"root_cause","candidate_dimensions":["region"]}'

        class FakeModel:
            def invoke(self, prompt):
                self.prompt = prompt
                return Response()

        with patch("agents.llm.gemma", return_value=FakeModel()):
            parsed = structured_call(QuestionPlan, "parse the question")
        self.assertEqual(parsed.metric, "revenue")
        self.assertEqual(parsed.candidate_dimensions, ["region"])

        class MalformedModel:
            def invoke(self, prompt):
                return type("Response", (), {"content": "not JSON"})()

        with patch("agents.llm.gemma", return_value=MalformedModel()):
            result = structured_call(QuestionPlan, "parse the question")
            self.assertIsNone(result, "structured_call should return None for malformed responses")

    @patch.dict(os.environ, {"GEMMA_API_KEY": ""})
    def test_demo_investigation_nodes_end_to_end(self):
        state = {"dataset": pd.read_csv(os.path.join(ROOT, "data", "demo_sales.csv")),
                 "question": "Why did revenue fall in March?"}
        for node in (profile_data, parse_question, calculate_baseline, generate_hypotheses,
                     plan_tests, execute_test, verify_result, critic, final_synthesis):
            state.update(node(state))
            self.assertIsNone(state.get("error"), f"{node.__name__}: {state.get('error')}")
        self.assertTrue(state["verification"]["passed"])
        verdicts = {item["hypothesis_id"]: item["verdict"] for item in state["verdicts"]}
        self.assertEqual(verdicts, {"h1": "WEAKENED", "h2": "SUPPORTED", "h3": "WEAKENED",
                                    "h4": "REJECTED", "h5": "UNTESTABLE"})
        self.assertIn("do not establish causation", state["final_report"])

        # Verification must catch a changed tool result, even when contribution totals still sum to 100%.
        state["test_results"][0]["result"]["results"][0]["change"] += 1
        tampered = verify_result(state)["verification"]
        self.assertFalse(tampered["passed"])
        self.assertFalse(next(check for check in tampered["checks"]
                              if check["check"] == "evidence_h1")["passed"])

    def test_router_has_a_hard_iteration_limit(self):
        self.assertEqual(route_next({"needs_more_tests": True, "iteration": 1}), "more_tests")
        self.assertEqual(route_next({"needs_more_tests": True, "iteration": 2}), "synthesize")

    def test_unsupported_data_returns_a_clear_error(self):
        state = {"dataset": pd.DataFrame({"label": ["a", "b"]}), "question": "Why did revenue fall?"}
        state.update(profile_data(state))
        state.update(parse_question(state))
        self.assertIn("numeric measure", state["error"])

    @patch.dict(os.environ, {"GEMMA_API_KEY": ""})
    def test_missing_requested_month_is_not_silently_replaced(self):
        state = {"dataset": pd.read_csv(os.path.join(ROOT, "data", "demo_sales.csv")),
                 "question": "Why did revenue fall in April?"}
        state.update(profile_data(state))
        state.update(parse_question(state))
        self.assertIn("requested month", state["error"])

    def test_graph_compiles_and_runs_when_langgraph_runtime_is_available(self):
        try:
            from graph.graph import investigation_graph
        except Exception as exc:
            self.skipTest(f"LangGraph runtime unavailable in this environment: {exc}")
        frame = pd.read_csv(os.path.join(ROOT, "data", "demo_sales.csv"))
        result = investigation_graph.invoke({"dataset": frame, "question": "Why did revenue fall in March?"})
        self.assertEqual(result["overall_change"]["value_b"], 7_940_000)
        self.assertTrue(result["verification"]["passed"])



class QuestionHandlingTests(unittest.TestCase):
    def setUp(self):
        from analysis.profiling import profile_data
        _, self.info = profile_data(pd.read_csv(Path(__file__).resolve().parents[1] / "data" / "demo_sales.csv"))

    def test_two_named_months_are_compared_directly(self):
        from graph.nodes import _period_defaults
        self.assertEqual(_period_defaults("What changed between February and March?", self.info), ("2026-02", "2026-03"))
        self.assertEqual(_period_defaults("Compare March and February revenue", self.info), ("2026-02", "2026-03"))

    def test_validator_accepts_short_real_questions(self):
        from analysis.question_validator import validate_question_local
        for question in ["Was this decline seasonal?", "Which departments had the highest attrition?"]:
            self.assertTrue(validate_question_local(question, self.info)["valid"], question)

    def test_validator_rejects_unusable_input(self):
        from analysis.question_validator import validate_question_local
        for question in ["", "revenue", "123 456 789"]:
            self.assertFalse(validate_question_local(question, self.info)["valid"], question)

    def test_every_suggested_demo_question_runs(self):
        import json
        from analysis.profiling import profile_data
        from graph.graph import investigation_graph
        root = Path(__file__).resolve().parents[1] / "data"
        with patch.dict(os.environ, {"GEMMA_API_KEY": ""}):
            for meta in json.loads((root / "datasets.json").read_text(encoding="utf-8"))["datasets"]:
                frame = pd.read_csv(root / meta["file"])
                _, info = profile_data(frame)
                for question in meta["suggested_questions"]:
                    result = investigation_graph.invoke({"dataset": frame, "question": question, "dataset_info": info},
                                                        config={"recursion_limit": 20})
                    self.assertIsNone(result.get("error"), f"{meta['id']}: {question}")
                    self.assertTrue(result["verification"]["passed"], f"{meta['id']}: {question}")


if __name__ == "__main__":
    unittest.main()
