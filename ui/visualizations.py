import plotly.graph_objects as go


def baseline_chart(change: dict) -> go.Figure:
    periods = [change["period_a"], change["period_b"]]
    values = [change["value_a"], change["value_b"]]
    colors = ["#53c7a5", "#f08a68"]
    figure = go.Figure(go.Bar(x=periods, y=values, marker_color=colors, text=[f"{value:,.0f}" for value in values],
                              textposition="outside", hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>"))
    figure.update_layout(height=280, margin={"l": 8, "r": 8, "t": 20, "b": 8},
                         yaxis_title=change["metric"], showlegend=False, template="plotly_white")
    return figure
