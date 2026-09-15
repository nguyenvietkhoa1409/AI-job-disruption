"""LayoffsSource: loads the Layoffs.fyi tech layoffs dataset."""

import pandas as pd

from src.config import PROJECT_PATHS
from src.data_sources.base_source import BaseDataSource


class LayoffsSource(BaseDataSource):
    def load(self) -> pd.DataFrame:
        raise NotImplementedError

    def describe_columns(self) -> dict:
        raise NotImplementedError
