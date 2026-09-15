"""AIJobsQualityRules: quality checks specific to the AI jobs dataset."""

import pandas as pd

from src.quality.base_rule_set import BaseQualityRuleSet


class AIJobsQualityRules(BaseQualityRuleSet):
    def apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        raise NotImplementedError
