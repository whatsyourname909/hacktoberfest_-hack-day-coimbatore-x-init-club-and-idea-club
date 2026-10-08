import plotly.graph_objects as go


def baseline_chart(change: dict) -> go.Figure:
    periods = [change["period_a"], change["period_b"]]
    values = [change["value_a"], change["value_b"]]
    colors = ["#6366f1", "#f43f5e"] if change.get("absolute_change", 0) < 0 else ["#6366f1", "#10b981"]
    figure = go.Figure(go.Bar(
        x=periods, y=values, marker_color=colors,
        marker_line_width=0,
        text=[f"{value:,.0f}" for value in values],
        textposition="outside",
        textfont=dict(size=13, color="#e2e8f0"),
        hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>",
    ))
    figure.update_layout(
        height=260,
        margin={"l": 0, "r": 0, "t": 16, "b": 0},
        yaxis_title=change["metric"],
        yaxis=dict(
            color="#94a3b8", gridcolor="rgba(148,163,184,0.1)",
            showgrid=True, zeroline=False,
        ),
        xaxis=dict(color="#94a3b8"),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
    )
    return figure


def contribution_chart(rows: list[dict], dimension: str, metric: str) -> go.Figure:
    """Horizontal bar chart showing contribution % by dimension group."""
    if not rows:
        return None
    sorted_rows = sorted(rows, key=lambda r: r.get("contribution_pct", 0))
    labels = [str(r.get(dimension, "")) for r in sorted_rows]
    values = [r.get("contribution_pct", 0) for r in sorted_rows]
    colors = ["#f43f5e" if v < 0 else "#10b981" for v in values]
    figure = go.Figure(go.Bar(
        y=labels, x=values, orientation="h",
        marker_color=colors, marker_line_width=0,
        text=[f"{v:+.1f}%" for v in values],
        textposition="outside",
        textfont=dict(size=11, color="#e2e8f0"),
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ))
    figure.update_layout(
        height=max(180, len(labels) * 32 + 40),
        margin={"l": 0, "r": 40, "t": 8, "b": 0},
        xaxis=dict(title="Contribution to change (%)", color="#94a3b8",
                   gridcolor="rgba(148,163,184,0.1)", zeroline=True,
                   zerolinecolor="rgba(148,163,184,0.3)"),
        yaxis=dict(color="#94a3b8"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
        showlegend=False,
    )
    return figure
