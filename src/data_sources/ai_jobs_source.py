"""AIJobsSource: loads the AI Jobs Market 2025-2026 Salaries dataset."""

from pathlib import Path

import pandas as pd

from src.config import PROJECT_PATHS
from src.data_sources.base_source import BaseDataSource


class AIJobsSource(BaseDataSource):
    """Loads the raw AI jobs market CSV with no transformation applied."""

    FILENAME = "ai_jobs_market_2025_2026.csv"

    def __init__(self, path: Path | None = None):
        self.path = path or (PROJECT_PATHS.data_raw / self.FILENAME)

    def load(self) -> pd.DataFrame:
        df = pd.read_csv(self.path)
        self.validate(df)
        return df

    def describe_columns(self) -> dict[str, str]:
        return {
            "job_id": "object",
            "job_title": "object",
            "job_category": "object",
            "experience_level": "object",
            "years_of_experience": "int64",
            "education_required": "object",
            "annual_salary_usd": "float64",
            "salary_min_usd": "int64",
            "salary_max_usd": "int64",
            "city": "object",
            "country": "object",
            "remote_work": "object",
            "company_size": "object",
            "industry": "object",
            "required_skills": "object",
            "ai_salary_premium_pct": "float64",
            "demand_score": "int64",
            "demand_growth_yoy_pct": "float64",
            "benefits_score_10": "float64",
            "posting_year": "int64",
            "posting_month": "int64",
            "is_senior": "int64",
            "is_remote_friendly": "int64",
            "is_llm_role": "int64",
            "salary_tier": "object",
        }
