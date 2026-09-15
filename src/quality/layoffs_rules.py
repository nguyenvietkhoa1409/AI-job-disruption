"""LayoffsQualityRules: quality checks specific to the layoffs dataset."""

import pandas as pd

from src.quality.base_rule_set import BaseQualityRuleSet


class LayoffsQualityRules(BaseQualityRuleSet):
    def apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        raise NotImplementedError
