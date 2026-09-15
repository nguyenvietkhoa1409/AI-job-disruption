"""SurveyQualityRules: quality checks specific to the developer survey dataset."""

import pandas as pd

from src.quality.base_rule_set import BaseQualityRuleSet


class SurveyQualityRules(BaseQualityRuleSet):
    def apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        raise NotImplementedError
