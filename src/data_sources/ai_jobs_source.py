"""AIJobsSource: loads the AI Jobs Market 2025-2026 Salaries dataset."""

import pandas as pd

from src.config import PROJECT_PATHS
from src.data_sources.base_source import BaseDataSource


class AIJobsSource(BaseDataSource):
    def load(self) -> pd.DataFrame:
        raise NotImplementedError

    def describe_columns(self) -> dict:
        raise NotImplementedError
