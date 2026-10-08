from __future__ import annotations

import pandas as pd
import duckdb


def _periods(frame: pd.DataFrame, date_column: str) -> pd.Series:
    return pd.to_datetime(frame[date_column], errors="coerce").dt.to_period("M").astype("string")


def compare_periods(frame: pd.DataFrame, metric: str, date_column: str, period_a: str, period_b: str) -> dict:
    # Identifiers come from validated dataset metadata and are SQL-quoted; values are parameters.
    quote = lambda name: '"' + str(name).replace('"', '""') + '"'
    query = f"""
        SELECT
          SUM(TRY_CAST({quote(metric)} AS DOUBLE)) FILTER (WHERE strftime(TRY_CAST({quote(date_column)} AS DATE), '%Y-%m') = ?) AS value_a,
          SUM(TRY_CAST({quote(metric)} AS DOUBLE)) FILTER (WHERE strftime(TRY_CAST({quote(date_column)} AS DATE), '%Y-%m') = ?) AS value_b,
          COUNT(*) FILTER (WHERE strftime(TRY_CAST({quote(date_column)} AS DATE), '%Y-%m') = ?) AS rows_a,
          COUNT(*) FILTER (WHERE strftime(TRY_CAST({quote(date_column)} AS DATE), '%Y-%m') = ?) AS rows_b
        FROM frame
    """
    with duckdb.connect(database=":memory:") as connection:
        connection.register("frame", frame)
        row = connection.execute(query, [period_a, period_b, period_a, period_b]).fetchone()
    a, b, rows_a, rows_b = row
    if not rows_a or not rows_b:
        raise ValueError("Both comparison periods must contain rows.")
    a, b = float(a or 0), float(b or 0)
    change = b - a
    return {
        "metric": metric, "period_a": period_a, "value_a": a,
        "period_b": period_b, "value_b": b, "absolute_change": change,
        "percent_change": (change / abs(a) * 100) if a else None,
        "rows_a": int(rows_a), "rows_b": int(rows_b),
    }


def breakdown_by_dimension(frame: pd.DataFrame, metric: str, date_column: str,
                           period_a: str, period_b: str, dimension: str) -> dict:
    periods = _periods(frame, date_column)
    values = pd.to_numeric(frame[metric], errors="coerce")
    work = pd.DataFrame({dimension: frame[dimension].fillna("(missing)"), "period": periods, "value": values})
    grouped = work[work["period"].isin([period_a, period_b])].pivot_table(
        index=dimension, columns="period", values="value", aggfunc="sum", fill_value=0
    )
    for p in (period_a, period_b):
        if p not in grouped.columns:
            grouped[p] = 0.0
    grouped["change"] = grouped[period_b] - grouped[period_a]
    total_change = float(grouped["change"].sum())
    grouped["contribution_pct"] = grouped["change"].div(total_change).mul(100) if total_change else 0.0
    results = [
        {dimension: str(index), "value_a": float(row[period_a]), "value_b": float(row[period_b]),
         "change": float(row["change"]), "contribution_pct": float(row["contribution_pct"])}
        for index, row in grouped.sort_values("change").iterrows()
    ]
    return {"dimension": dimension, "metric": metric, "period_a": period_a, "period_b": period_b,
            "total_change": total_change, "results": results}


def contribution_to_change(frame: pd.DataFrame, metric: str, date_column: str,
                           period_a: str, period_b: str, dimension: str) -> dict:
    result = breakdown_by_dimension(frame, metric, date_column, period_a, period_b, dimension)
    result["tool"] = "contribution_to_change"
    return result


def mix_analysis(frame: pd.DataFrame, metric: str, date_column: str,
                 period_a: str, period_b: str, dimension: str) -> dict:
    breakdown = breakdown_by_dimension(frame, metric, date_column, period_a, period_b, dimension)
    a_total = sum(row["value_a"] for row in breakdown["results"])
    b_total = sum(row["value_b"] for row in breakdown["results"])
    for row in breakdown["results"]:
        row["share_a_pct"] = row["value_a"] / a_total * 100 if a_total else 0.0
        row["share_b_pct"] = row["value_b"] / b_total * 100 if b_total else 0.0
        row["share_shift_pp"] = row["share_b_pct"] - row["share_a_pct"]
    breakdown["tool"] = "mix_analysis"
    unit_col = next((col for col in frame.columns if str(col).lower() in {"units", "unit", "quantity", "qty"}), None)
    if unit_col:
        periods = _periods(frame, date_column)
        units = pd.to_numeric(frame[unit_col], errors="coerce").fillna(0)
        work = pd.DataFrame({dimension: frame[dimension].fillna("(missing)"), "period": periods,
                             "units": units, "value": pd.to_numeric(frame[metric], errors="coerce").fillna(0)})
        grouped = work[work["period"].isin([period_a, period_b])].pivot_table(
            index=dimension, columns="period", values=["units", "value"], aggfunc="sum", fill_value=0
        )
        for p in (period_a, period_b):
            for field in ("units", "value"):
                if (field, p) not in grouped.columns:
                    grouped[(field, p)] = 0.0
        unit_a, unit_b = grouped[("units", period_a)], grouped[("units", period_b)]
        value_a = grouped[("value", period_a)]
        price_a = value_a.div(unit_a.where(unit_a.ne(0)))
        total_units_b = float(unit_b.sum())
        share_a = unit_a.div(unit_a.sum()) if unit_a.sum() else unit_a * 0
        actual_at_period_a_prices = float((unit_b * price_a.fillna(0)).sum())
        counterfactual = float(total_units_b * (share_a * price_a.fillna(0)).sum())
        mix_effect = counterfactual - actual_at_period_a_prices
        total_change = float(breakdown["total_change"])
        breakdown["mix_effect_total"] = mix_effect
        breakdown["mix_effect_contribution_pct"] = abs(mix_effect / total_change * 100) if total_change else None
        breakdown["mix_method"] = f"Unit-share shift valued at {period_a} category revenue per unit."
    else:
        breakdown["mix_effect_total"] = None
        breakdown["mix_effect_contribution_pct"] = None
        breakdown["mix_method"] = "Share shifts only; a volume-weighted mix effect needs a units/quantity column."
    breakdown["definition"] = "Category shares are calculated from the selected metric; mix effect is separate from total contribution."
    return breakdown
