import pandas as pd


def trend_analysis(frame: pd.DataFrame, metric: str, date_column: str) -> dict:
    dates = pd.to_datetime(frame[date_column], errors="coerce")
    values = pd.to_numeric(frame[metric], errors="coerce")
    monthly = pd.DataFrame({"period": dates.dt.to_period("M").astype("string"), "value": values})
    series = monthly.dropna().groupby("period", as_index=False)["value"].sum().sort_values("period")
    return {"tool": "trend_analysis", "metric": metric,
            "periods": [{"period": str(row.period), "value": float(row.value)} for row in series.itertuples()],
            "period_count": int(len(series))}
