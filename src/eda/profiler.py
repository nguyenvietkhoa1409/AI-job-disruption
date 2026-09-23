"""DatasetProfiler: auto-generates a data dictionary table from a DataFrame."""

import pandas as pd


class DatasetProfiler:
    def profile(self, df: pd.DataFrame) -> pd.DataFrame:
        """One row per column of df: dtype, missing count/percent, unique
        count (dropping NaN), and min/max for numeric columns (NA for
        non-numeric columns, so the table stays one dtype per field)."""
        n_rows = len(df)
        rows = []
        for column in df.columns:
            series = df[column]
            is_numeric = pd.api.types.is_numeric_dtype(series)
            missing_count = int(series.isna().sum())
            rows.append(
                {
                    "column": column,
                    "dtype": str(series.dtype),
                    "missing_count": missing_count,
                    "missing_pct": round(missing_count / n_rows * 100, 1) if n_rows else 0.0,
                    "unique_count": int(series.nunique(dropna=True)),
                    "min": series.min() if is_numeric else pd.NA,
                    "max": series.max() if is_numeric else pd.NA,
                }
            )
        return pd.DataFrame(
            rows,
            columns=["column", "dtype", "missing_count", "missing_pct", "unique_count", "min", "max"],
        )