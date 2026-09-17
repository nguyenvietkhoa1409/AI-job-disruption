"""AIJobsQualityRules: quality checks specific to the AI jobs dataset."""

import pandas as pd

from src.quality.base_rule_set import BaseQualityRuleSet
from src.schema.dimension_maps import COUNTRY_MAP, EXPERIENCE_MAP, INDUSTRY_MAP, ROLE_MAP


class AIJobsQualityRules(BaseQualityRuleSet):
    """The real file has no duplicate job_id, salary_min_usd <= salary_max_usd
    holds on every row, and every spec-documented range (demand_score 68-98,
    ai_salary_premium_pct 3-18, benefits_score_10 6.0-9.8) holds on every
    row. Rules below are defensive structural bounds, not fixes for
    observed problems.

    annual_salary_usd exceeding salary_max_usd (19.2% of the real file,
    always above never below, capped around +20%, uncorrelated with
    ai_salary_premium_pct) is deliberately NOT a rule here: it matches the
    dataset's own framing in Layoff Project.md as "a curated illustration
    of directional market trends rather than a live job board scrape" -
    i.e. synthetic generation noise, not a data error worth quarantining.
    """

    def apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        rule_masks = {
            "duplicate_row": df.duplicated(keep="first"),
            "duplicate_job_id": df["job_id"].duplicated(keep="first"),
            "salary_min_exceeds_max": df["salary_min_usd"] > df["salary_max_usd"],
            "salary_min_not_positive": df["salary_min_usd"] <= 0,
            "years_of_experience_negative": df["years_of_experience"] < 0,
            "country_not_in_dimension_map": df["country"].notna() & ~df["country"].isin(COUNTRY_MAP),
            "industry_not_in_dimension_map": df["industry"].notna() & ~df["industry"].isin(INDUSTRY_MAP),
            "job_title_not_in_dimension_map": df["job_title"].notna() & ~df["job_title"].isin(ROLE_MAP),
            "experience_level_not_in_dimension_map": df["experience_level"].notna() & ~df["experience_level"].isin(EXPERIENCE_MAP),
        }
        return self._split(df, rule_masks)
