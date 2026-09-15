"""LayoffsSource: loads the Layoffs.fyi tech layoffs dataset."""

from pathlib import Path

import pandas as pd

from src.config import PROJECT_PATHS
from src.data_sources.base_source import BaseDataSource


class LayoffsSource(BaseDataSource):
    """Loads the raw layoffs CSV with no transformation applied."""

    FILENAME = "layoffs.csv"

    def __init__(self, path: Path | None = None):
        self.path = path or (PROJECT_PATHS.data_raw / self.FILENAME)

    def load(self) -> pd.DataFrame:
        df = pd.read_csv(self.path)
        self.validate(df)
        return df

    def describe_columns(self) -> dict[str, str]:
        return {
            "company": "object",
            "location": "object",
            "total_laid_off": "float64",
            "date": "object",
            "percentage_laid_off": "float64",
            "industry": "object",
            "source": "object",
            "stage": "object",
            "funds_raised": "float64",
            "country": "object",
            "date_added": "object",
        }
