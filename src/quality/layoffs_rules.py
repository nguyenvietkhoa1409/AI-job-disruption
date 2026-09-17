"""LayoffsQualityRules: quality checks specific to the layoffs dataset."""

import pandas as pd

from src.quality.base_rule_set import BaseQualityRuleSet
from src.schema.dimension_maps import COUNTRY_MAP, INDUSTRY_MAP


class LayoffsQualityRules(BaseQualityRuleSet):
    """The real file has no duplicates, no negative/out-of-range values, and
    every date parses. Rules below are defensive bounds tied to field
    semantics (percentages, counts can't be negative), not fixes for
    observed problems - a future data refresh that violates them should
    fail loud instead of silently corrupting downstream analysis.

    Rows missing both total_laid_off and percentage_laid_off (16.2% of the
    real file) are deliberately NOT quarantined: company/date/industry/
    country are still usable for a layoff-event timeline without a
    magnitude figure, and missingness itself is not invalidity.
    """

    def apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        rule_masks = {
            "percentage_laid_off_out_of_range": (
                df["percentage_laid_off"].notna() & ~df["percentage_laid_off"].between(0, 1)
            ),
            "total_laid_off_negative": df["total_laid_off"] < 0,
            "funds_raised_negative": df["funds_raised"] < 0,
            "duplicate_row": df.duplicated(keep="first"),
            "country_not_in_dimension_map": df["country"].notna() & ~df["country"].isin(COUNTRY_MAP),
            "industry_not_in_dimension_map": df["industry"].notna() & ~df["industry"].isin(INDUSTRY_MAP),
        }
        return self._split(df, rule_masks)
