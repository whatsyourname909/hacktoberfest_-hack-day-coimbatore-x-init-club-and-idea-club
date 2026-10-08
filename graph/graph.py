from langgraph.graph import END, START, StateGraph

from graph.nodes import (calculate_baseline, critic, execute_test, final_synthesis,
                         generate_hypotheses, parse_question, plan_tests, profile_data,
                         route_next, verify_result, validate_question)
from graph.state import InvestigationState


def _stop_on_error(state: InvestigationState) -> str:
    return "stop" if state.get("error") else "continue"


def build_graph():
    builder = StateGraph(InvestigationState)
    nodes = {
        "validate_question": validate_question,
        "profile_data": profile_data,
        "parse_question": parse_question,
        "calculate_baseline": calculate_baseline,
        "generate_hypotheses": generate_hypotheses,
        "plan_tests": plan_tests,
        "execute_test": execute_test,
        "verify_result": verify_result,
        "critic": critic,
        "final_synthesis": final_synthesis,
    }
    for name, node in nodes.items():
        builder.add_node(name, node)
    builder.add_edge(START, "validate_question")
    builder.add_conditional_edges("validate_question", _stop_on_error, {"stop": END, "continue": "profile_data"})
    for current, following in [
        ("profile_data", "parse_question"),
        ("parse_question", "calculate_baseline"),
        ("calculate_baseline", "generate_hypotheses"),
        ("generate_hypotheses", "plan_tests"),
        ("plan_tests", "execute_test"),
        ("execute_test", "verify_result"),
        ("verify_result", "critic"),
    ]:
        builder.add_conditional_edges(current, _stop_on_error, {"stop": END, "continue": following})
    builder.add_conditional_edges("critic", route_next, {"more_tests": "plan_tests", "synthesize": "final_synthesis"})
    builder.add_edge("final_synthesis", END)
    return builder.compile()


investigation_graph = build_graph()
