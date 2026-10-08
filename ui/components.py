import pandas as pd
import streamlit as st

from ui.visualizations import baseline_chart, contribution_chart

VERDICT_STYLE = {
    "SUPPORTED":  ("✅", "#10b981", "rgba(16,185,129,0.12)"),
    "WEAKENED":   ("⚠️", "#f59e0b", "rgba(245,158,11,0.12)"),
    "REJECTED":   ("❌", "#ef4444", "rgba(239,68,68,0.12)"),
    "UNTESTABLE": ("❓", "#6b7280", "rgba(107,114,128,0.12)"),
    "PENDING":    ("⏳", "#6b7280", "rgba(107,114,128,0.12)"),
}

TEST_LABELS = {
    "contribution": "📊 Contribution analysis",
    "mix": "🔀 Mix analysis",
    "data_quality": "🔍 Data quality check",
    "trend": "📈 Trend analysis",
}


def render_profile(info: dict):
    """Render a compact dataset profile in the sidebar."""
    st.markdown("##### 📋 Dataset overview")
    col1, col2 = st.columns(2)
    col1.metric("Rows", f"{info['row_count']:,}")
    col2.metric("Columns", len(info["columns"]))

    if info["date_ranges"]:
        for column, date_range in info["date_ranges"].items():
            st.caption(f"📅 **{column}:** {date_range['min'][:10]} → {date_range['max'][:10]}")

    if info["likely_metrics"]:
        st.caption("📐 **Metrics:** " + ", ".join(f"`{m}`" for m in info["likely_metrics"]))
    if info["likely_dimensions"]:
        st.caption("📂 **Dimensions:** " + ", ".join(f"`{d}`" for d in info["likely_dimensions"]))

    # Show missingness only if there are any issues
    missing_cols = {k: v for k, v in info.get("missingness", {}).items() if v > 0}
    if missing_cols:
        st.caption("⚠️ **Missing data:** " + ", ".join(f"`{k}` {v:.0%}" for k, v in missing_cols.items()))
    else:
        st.caption("✅ **No missing values detected**")


def render_investigation(result: dict):
    """Render the full investigation results with a polished layout."""

    # --- Baseline section ---
    change = result["overall_change"]
    pct = change.get("percent_change")
    abs_change = change["absolute_change"]

    st.markdown("### 📊 Baseline comparison")
    col_metric, col_chart = st.columns([1, 1.4])

    with col_metric:
        delta_str = f"{pct:+.1f}%" if pct is not None else "N/A"
        delta_color = "inverse" if abs_change < 0 else "normal"
        st.metric(
            label=f"{change['metric']}",
            value=f"{change['value_b']:,.0f}",
            delta=delta_str,
            delta_color=delta_color,
        )
        st.caption(f"{change['period_a']} → {change['period_b']}")
        st.caption(f"Absolute change: **{abs_change:+,.0f}**")

    with col_chart:
        st.plotly_chart(baseline_chart(change), use_container_width=True, config={"displayModeBar": False})

    st.divider()

    # --- Verdict summary ---
    hypotheses = {item["id"]: item for item in result.get("hypotheses", [])}
    verdicts = {item["hypothesis_id"]: item for item in result.get("verdicts", [])}

    st.markdown("### 🔬 Hypothesis verdicts")

    for h_id, hypothesis in hypotheses.items():
        verdict_data = verdicts.get(h_id, {})
        verdict = verdict_data.get("verdict", "PENDING")
        icon, color, bg_color = VERDICT_STYLE.get(verdict, VERDICT_STYLE["PENDING"])
        contribution = verdict_data.get("contribution_pct")
        contribution_text = f" · {contribution:.1f}% contribution" if contribution is not None else ""
        rationale = verdict_data.get("rationale", "")

        st.markdown(
            f'<div style="background:{bg_color}; border-left:3px solid {color}; '
            f'padding:12px 16px; border-radius:8px; margin-bottom:8px;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center;">'
            f'<span style="font-weight:600; color:#e2e8f0;">{icon} {hypothesis["statement"]}</span>'
            f'<span style="background:{color}; color:white; padding:2px 10px; border-radius:12px; '
            f'font-size:0.78em; font-weight:600;">{verdict}{contribution_text}</span>'
            f'</div>'
            f'<div style="color:#94a3b8; font-size:0.88em; margin-top:4px;">{rationale}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # --- Evidence trace (expandable) ---
    st.markdown("### 🔎 Evidence trace")
    results_by_id = {item["hypothesis_id"]: item for item in result.get("test_results", [])}

    for h_id, hypothesis in hypotheses.items():
        test_result = results_by_id.get(h_id, {})
        verdict_data = verdicts.get(h_id, {})
        verdict = verdict_data.get("verdict", "PENDING")
        icon = VERDICT_STYLE.get(verdict, VERDICT_STYLE["PENDING"])[0]
        test_label = TEST_LABELS.get(test_result.get("test", ""), test_result.get("test", "Not run"))

        with st.expander(f"{icon} {hypothesis['statement']}", expanded=False):
            # Test info
            col1, col2 = st.columns(2)
            col1.markdown(f"**Test:** {test_label}")
            col2.markdown(f"**Verdict:** {verdict}")

            # Contract thresholds
            contract = test_result.get("contract", {})
            if contract.get("support_threshold") is not None:
                st.markdown(
                    f"**Thresholds:** Support ≥ {contract['support_threshold']:.0%} · "
                    f"Weaken ≥ {contract.get('weaken_threshold', 0):.0%}"
                )
            if contract.get("decision_rules"):
                for rule in contract["decision_rules"]:
                    st.caption(f"📏 {rule}")

            # Results
            if test_result.get("error"):
                st.error(f"Test error: {test_result['error']}")
            elif test_result.get("result"):
                evidence = test_result["result"]

                # Contribution/mix: show chart + data
                if test_result.get("test") in {"contribution", "mix"} and evidence.get("results"):
                    dimension = contract.get("dimension", "group")
                    chart = contribution_chart(evidence["results"], dimension, evidence.get("metric", ""))
                    if chart:
                        st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})

                    # Compact table
                    rows = []
                    for r in evidence["results"]:
                        rows.append({
                            dimension: r.get(dimension, ""),
                            f"{evidence.get('period_a', 'A')}": f"{r.get('value_a', 0):,.0f}",
                            f"{evidence.get('period_b', 'B')}": f"{r.get('value_b', 0):,.0f}",
                            "Change": f"{r.get('change', 0):+,.0f}",
                            "Contribution": f"{r.get('contribution_pct', 0):+.1f}%",
                        })
                    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

                    if test_result.get("test") == "mix" and evidence.get("mix_effect_contribution_pct") is not None:
                        st.info(f"Mix effect accounts for **{evidence['mix_effect_contribution_pct']:.1f}%** "
                                f"of the net change. {evidence.get('mix_method', '')}")
                elif test_result.get("test") == "data_quality":
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Rows", f"{evidence.get('row_count', 0):,}")
                    col2.metric("Duplicates", evidence.get("duplicate_rows", 0))
                    col3.metric("Missing months", len(evidence.get("missing_months", [])))
                    if evidence.get("missing"):
                        st.caption("Missing values: " + ", ".join(
                            f"`{k}` {v['pct']:.1f}%" for k, v in evidence["missing"].items()
                        ))
                elif test_result.get("test") == "trend":
                    st.metric("Observed periods", evidence.get("period_count", 0))
                    if evidence.get("periods"):
                        st.caption("Monthly totals: " + ", ".join(
                            f"{p['period']}: {p['value']:,.0f}" for p in evidence["periods"]
                        ))
                else:
                    st.json(evidence)

            # Critic note
            if verdict_data.get("critic_note"):
                st.markdown(f"💬 **Critic:** {verdict_data['critic_note']}")
            if verdict_data.get("alternative_explanation"):
                st.caption(f"🔄 Alternative: {verdict_data['alternative_explanation']}")

    st.divider()

    # --- Final answer ---
    st.markdown("### 💡 Final answer")
    report = result.get("final_report", "No synthesis was produced.")

    # Parse the report into structured display
    lines = report.split("\n\n")
    if lines:
        # First line is the summary — highlight it
        st.markdown(
            f'<div style="background:rgba(99,102,241,0.1); border-left:3px solid #6366f1; '
            f'padding:16px; border-radius:8px; margin-bottom:16px;">'
            f'<span style="color:#e2e8f0; font-size:1.05em;">{lines[0]}</span></div>',
            unsafe_allow_html=True,
        )
        # Remaining lines
        for line in lines[1:]:
            if line.startswith("SUPPORTED") or line.startswith("WEAKENED") or line.startswith("REJECTED") or line.startswith("UNTESTABLE"):
                verdict_word = line.split(":")[0].strip()
                icon = VERDICT_STYLE.get(verdict_word, VERDICT_STYLE["PENDING"])[0]
                st.markdown(f"{icon} {line}")
            elif "do not establish causation" in line.lower():
                st.caption(f"⚖️ {line}")
            else:
                st.markdown(line)

    # Verification badge
    verification = result.get("verification", {})
    if verification:
        if verification.get("passed"):
            st.success("✅ All calculations independently verified")
        else:
            st.warning("⚠️ Some calculations could not be fully verified")
