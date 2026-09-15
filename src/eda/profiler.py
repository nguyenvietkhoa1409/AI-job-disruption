"""DatasetProfiler: auto-generates a data dictionary table from a DataFrame."""

import pandas as pd


class DatasetProfiler:
    def profile(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError
