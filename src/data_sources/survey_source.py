"""SurveySource: loads the Stack Overflow Developer Survey 2025 dataset."""

import pandas as pd

from src.config import PROJECT_PATHS
from src.data_sources.base_source import BaseDataSource


class SurveySource(BaseDataSource):
    def load(self) -> pd.DataFrame:
        raise NotImplementedError

    def describe_columns(self) -> dict:
        raise NotImplementedError
