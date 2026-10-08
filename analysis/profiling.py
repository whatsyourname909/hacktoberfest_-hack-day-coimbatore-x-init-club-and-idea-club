from __future__ import annotations

import pandas as pd


def profile_data(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if frame.empty:
        raise ValueError("The uploaded CSV has no rows.")

    data = frame.copy()
    date_columns: list[str] = []
    for column in data.columns:
        if pd.api.types.is_datetime64_any_dtype(data[column]):
            date_columns.append(column)
            continue
        if data[column].dtype == "object" or pd.api.types.is_string_dtype(data[column]):
            numeric_text = data[column].astype("string").str.replace(",", "", regex=False).str.replace(r"[$₹£€%]", "", regex=True)
            numeric = pd.to_numeric(numeric_text, errors="coerce")
            numeric_ratio = numeric.notna().mean()
            metric_like = any(token in str(column).lower() for token in ("revenue", "sales", "amount", "price", "profit", "cost", "quantity", "units", "count"))
            unique_ratio = data[column].nunique(dropna=True) / max(data[column].notna().sum(), 1)
            if numeric_ratio >= 0.9 and (metric_like or unique_ratio < 0.8):
                data[column] = numeric
                continue
            parsed = pd.to_datetime(data[column], errors="coerce", format="mixed")
            valid_ratio = parsed.notna().mean()
            if valid_ratio >= 0.8:
                data[column] = parsed
                date_columns.append(column)

    numeric_columns = [
        column for column in data.columns
        if pd.api.types.is_numeric_dtype(data[column]) and not pd.api.types.is_bool_dtype(data[column])
    ]
    categorical_columns = [
        column for column in data.columns
        if column not in date_columns and column not in numeric_columns
    ]
    date_ranges = {
        column: {
            "min": data[column].min().isoformat(),
            "max": data[column].max().isoformat(),
        }
        for column in date_columns if data[column].notna().any()
    }
    date_periods = {
        column: sorted(data[column].dropna().dt.to_period("M").astype(str).unique().tolist())
        for column in date_columns
    }
    info = {
        "row_count": int(len(data)),
        "columns": list(map(str, data.columns)),
        "data_types": {str(col): str(dtype) for col, dtype in data.dtypes.items()},
        "date_columns": date_columns,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "likely_metrics": [col for col in numeric_columns if any(token in col.lower() for token in ("revenue", "sales", "amount", "price", "profit", "cost", "quantity", "units", "count"))] or numeric_columns,
        "likely_dimensions": [col for col in categorical_columns if data[col].nunique(dropna=True) <= min(100, max(2, int(len(data) * 0.5)))],
        "missingness": {str(k): float(v) for k, v in data.isna().mean().items()},
        "date_ranges": date_ranges,
        "date_periods": date_periods,
    }
    return data, info
