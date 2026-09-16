"""SurveySource: loads the Stack Overflow Developer Survey 2025 dataset."""

from pathlib import Path

import pandas as pd

from src.config import PROJECT_PATHS
from src.data_sources.base_source import BaseDataSource


class SurveySource(BaseDataSource):
    """Loads the raw developer survey CSV, scoped to the 18 fields documented
    for this project (the raw file has 172 columns; the rest are out of scope)."""

    FILENAME = "survey_results_public.csv"

    def __init__(self, path: Path | None = None):
        self.path = path or (PROJECT_PATHS.data_raw / self.FILENAME)

    def load(self) -> pd.DataFrame:
        df = pd.read_csv(self.path)
        self.validate(df)
        return df[list(self.describe_columns())]

    def describe_columns(self) -> dict[str, str]:
        return {
            "ResponseId": "int64",
            "MainBranch": "object",
            "Age": "object",
            "EdLevel": "object",
            "Employment": "object",
            "WorkExp": "float64",
            "YearsCode": "float64",
            "DevType": "object",
            "RemoteWork": "object",
            "Country": "object",
            "Industry": "object",
            "ConvertedCompYearly": "float64",
            "AIThreat": "object",
            "AISelect": "object",
            "AISent": "object",
            "AIAcc": "object",
            "JobSat": "float64",
            "AIOpen": "object",
        }
