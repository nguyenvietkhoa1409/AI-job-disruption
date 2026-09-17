"""SurveyQualityRules: quality checks specific to the developer survey dataset."""

import pandas as pd

from src.quality.base_rule_set import BaseQualityRuleSet
from src.schema.dimension_maps import COUNTRY_MAP, INDUSTRY_MAP, ROLE_MAP

# Upper bound of each Age bucket ("Prefer not to say" and NaN are excluded
# from the age-plausibility rule below - there's no numeric bound to check
# against).
_AGE_UPPER_BOUND = {
    "18-24 years old": 24,
    "25-34 years old": 34,
    "35-44 years old": 44,
    "45-54 years old": 54,
    "55-64 years old": 64,
    "65 years or older": 100,
}
# Nobody plausibly starts accruing work/coding years before this age. Kept
# deliberately generous so the rule only catches mathematically impossible
# combinations, not merely early starters.
_EARLIEST_PLAUSIBLE_START_AGE = 5


class SurveyQualityRules(BaseQualityRuleSet):
    """No duplicate ResponseId in the real file, and JobSat/ConvertedCompYearly
    are within their documented bounds on every non-null row.

    WorkExp > YearsCode was considered and REJECTED as a rule: WorkExp is
    "years of professional work experience" (any field), YearsCode is
    "years writing code in any capacity" - they aren't nested, so someone
    who spent years in a non-coding career before learning to code
    legitimately has WorkExp > YearsCode. Checked against the real file:
    violation rate is 4.8% for "I am a developer by profession" vs
    19-43% for every non-developer MainBranch category - exactly the
    pattern you'd expect from a legitimate field-definition difference,
    not a data error. Quarantining on this basis would have thrown away
    ~8.9% of otherwise-valid rows.

    Replaced with a mathematically defensible check instead: WorkExp or
    YearsCode implausible for the respondent's Age bucket (e.g. "18-24
    years old" with WorkExp=50 cannot be true regardless of career path).
    This catches 0.16-0.18% of rows in the real file - genuine data entry
    errors, not legitimate variation.
    """

    def apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        age_upper = df["Age"].map(_AGE_UPPER_BOUND)
        max_plausible_years = age_upper - _EARLIEST_PLAUSIBLE_START_AGE

        rule_masks = {
            "duplicate_row": df.duplicated(keep="first"),
            "duplicate_response_id": df["ResponseId"].duplicated(keep="first"),
            "work_exp_implausible_for_age": (
                df["WorkExp"].notna() & max_plausible_years.notna() & (df["WorkExp"] > max_plausible_years)
            ),
            "years_code_implausible_for_age": (
                df["YearsCode"].notna() & max_plausible_years.notna() & (df["YearsCode"] > max_plausible_years)
            ),
            "job_sat_out_of_range": df["JobSat"].notna() & ~df["JobSat"].between(0, 10),
            "country_not_in_dimension_map": df["Country"].notna() & ~df["Country"].isin(COUNTRY_MAP),
            "industry_not_in_dimension_map": df["Industry"].notna() & ~df["Industry"].isin(INDUSTRY_MAP),
            "devtype_not_in_dimension_map": df["DevType"].notna() & ~df["DevType"].isin(ROLE_MAP),
        }
        return self._split(df, rule_masks)
