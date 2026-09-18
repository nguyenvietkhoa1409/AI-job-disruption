"""LayoffsQualityRules: quality checks specific to the layoffs dataset."""

import pandas as pd

from src.quality.base_rule_set import BaseQualityRuleSet
from src.schema.dimension_maps import COUNTRY_MAP, INDUSTRY_MAP


class LayoffsQualityRules(BaseQualityRuleSet):
    """The real file has no exact-duplicate rows and no negative/out-of-range
    values, and every date parses. It does have (company, date, location)
    groups that disagree on other columns (17 groups / 35 rows) - for those,
    all but the row with the latest date_added are quarantined rather than
    silently dropped. Remaining rules below are defensive bounds tied to
    field semantics (percentages, counts can't be negative), not fixes for
    observed problems - a future data refresh that violates them should
    fail loud instead of silently corrupting downstream analysis.

    Rows missing both total_laid_off and percentage_laid_off (16.2% of the
    real file) are deliberately NOT quarantined: company/date/industry/
    country are still usable for a layoff-event timeline without a
    magnitude figure, and missingness itself is not invalidity.
    """

    def apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        key = ["company", "date", "location"]
        dup_key = df.duplicated(subset=key, keep=False)
        dup_full = df.duplicated(keep=False)
        conflicting = dup_key & ~dup_full
        date_added = pd.to_datetime(df["date_added"], errors="coerce")
        latest_in_group = date_added.groupby([df[c] for c in key]).transform("max")
        duplicate_key_conflicting_values = conflicting & (date_added != latest_in_group)

        rule_masks = {
            "percentage_laid_off_out_of_range": (
                df["percentage_laid_off"].notna() & ~df["percentage_laid_off"].between(0, 1)
            ),
            "total_laid_off_negative": df["total_laid_off"] < 0,
            "funds_raised_negative": df["funds_raised"] < 0,
            "duplicate_row": df.duplicated(keep="first"),
            "duplicate_key_conflicting_values": duplicate_key_conflicting_values,
            "country_not_in_dimension_map": df["country"].notna() & ~df["country"].isin(COUNTRY_MAP),
            "industry_not_in_dimension_map": df["industry"].notna() & ~df["industry"].isin(INDUSTRY_MAP),
        }
        return self._split(df, rule_masks)
