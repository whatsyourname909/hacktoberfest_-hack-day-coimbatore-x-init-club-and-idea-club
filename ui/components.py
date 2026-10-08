import pandas as pd
import streamlit as st

from ui.visualizations import baseline_chart


def render_progress():
    stages = ["Data profiled", "Question parsed", "Baseline calculated", "Hypotheses generated",
              "Tests executed", "Verified", "Critic reviewed", "Final synthesis"]
    columns = st.columns(4)
    for index, stage in enumerate(stages):
        columns[index % 4].success(f"✓ {stage}")


def render_profile(info: dict):
    st.markdown("#### Dataset profile")
    first, second = st.columns(2)
    first.metric("Rows", f"{info['row_count']:,}")
    second.metric("Columns", len(info["columns"]))
    if info["date_ranges"]:
        for column, date_range in info["date_ranges"].items():
            st.caption(f"**{column} range:** {date_range['min'][:10]} to {date_range['max'][:10]}")
    st.caption("**Likely metrics:** " + (", ".join(info["likely_metrics"]) or "None detected"))
    st.caption("**Likely dimensions:** " + (", ".join(info["likely_dimensions"]) or "None detected"))


def render_investigation(result: dict):
    render_progress()
    st.divider()
    change = result["overall_change"]
    st.markdown("### Baseline")
    left, right = st.columns([1, 1.2])
    with left:
        delta = change.get("percent_change")
        st.metric("Absolute change", f"{change['absolute_change']:,.2f}",
                  delta=f"{delta:+.1f}%" if delta is not None else None)
        st.caption(f"{change['metric']}: {change['period_a']} → {change['period_b']}")
    with right:
        st.plotly_chart(baseline_chart(change), use_container_width=True)

    st.markdown("### Hypothesis evidence")
    hypotheses = {item["id"]: item for item in result.get("hypotheses", [])}
    verdicts = {item["hypothesis_id"]: item for item in result.get("verdicts", [])}
    rows = []
    for hypothesis_id, hypothesis in hypotheses.items():
        verdict = verdicts.get(hypothesis_id, {})
        contribution = verdict.get("contribution_pct")
        rows.append({"Hypothesis": hypothesis["statement"], "Evidence": verdict.get("rationale", "No result"),
                     "Contribution": f"{contribution:.1f}%" if contribution is not None else "—",
                     "Verdict": verdict.get("verdict", "PENDING")})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    st.markdown("### Evidence trace")
    results = {item["hypothesis_id"]: item for item in result.get("test_results", [])}
    for hypothesis_id, hypothesis in hypotheses.items():
        with st.expander(hypothesis["statement"]):
            test_result = results.get(hypothesis_id, {})
            verdict = verdicts.get(hypothesis_id, {})
            st.markdown(f"**Claim**  \n{hypothesis['statement']}")
            st.markdown(f"**Test**  \n{test_result.get('test', 'Not run')}")
            contract = test_result.get("contract", {})
            st.markdown("**Falsification thresholds**")
            st.write({"support_at_or_above": contract.get("support_threshold"),
                      "weaken_at_or_above": contract.get("weaken_threshold"),
                      "rules": contract.get("decision_rules", [])})
            st.markdown("**Calculation and result**")
            if test_result.get("error"):
                st.error(test_result["error"])
            else:
                evidence = test_result.get("result", {})
                if test_result.get("test") in {"contribution", "mix"}:
                    st.json(evidence)
                else:
                    st.json(evidence)
            st.markdown(f"**Critic verdict: {verdict.get('verdict', 'PENDING')}**")
            st.write(verdict.get("critic_note") or verdict.get("rationale", ""))
            if verdict.get("alternative_explanation"):
                st.caption("Alternative considered: " + verdict["alternative_explanation"])

    st.markdown("### Final answer")
    st.markdown(result.get("final_report", "No synthesis was produced."))
    verification = result.get("verification", {})
    if verification:
        st.caption("Calculation verification: " + ("passed" if verification.get("passed") else "issues found"))
