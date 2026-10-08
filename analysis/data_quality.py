import pandas as pd


def data_quality_check(frame: pd.DataFrame, date_column: str | None = None) -> dict:
    missing = {str(col): {"count": int(frame[col].isna().sum()), "pct": float(frame[col].isna().mean() * 100)}
               for col in frame.columns if frame[col].isna().any()}
    duplicate_rows = int(frame.duplicated().sum())
    missing_months = []
    if date_column and date_column in frame.columns:
        dates = pd.to_datetime(frame[date_column], errors="coerce").dropna()
        if not dates.empty:
            observed = set(dates.dt.to_period("M"))
            full = pd.period_range(min(observed), max(observed), freq="M")
            missing_months = [str(period) for period in full if period not in observed]
    return {"tool": "data_quality_check", "row_count": int(len(frame)), "missing": missing,
            "duplicate_rows": duplicate_rows, "missing_months": missing_months}
