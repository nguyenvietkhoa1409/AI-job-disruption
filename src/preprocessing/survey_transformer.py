"""SurveyTransformer: cleaning/transform logic specific to the developer survey dataset.

Runs on the CLEAN half of SurveyQualityRules.apply() output.

Two things beyond plain map-and-fill, both carried over from decisions made
early in this project (see reports/data_dictionary/PROJECT_CONTEXT.md):
- ConvertedCompYearly is winsorized at the 1st/99th percentile, computed
  and applied only on the non-null 48.7% - nulls stay null, never imputed.
- AIThreat/AISelect/AISent/AIAcc get an explicit "Not answered" label
  instead of mode-imputation, since these are the sentiment fields the
  project's analysis is actually about - imputing the mode would inflate
  the most common answer and bias that exact conclusion.
"""

import pandas as pd

from src.preprocessing.base_transformer import BaseTransformer
from src.schema.dimension_maps import COUNTRY_MAP, INDUSTRY_MAP, ROLE_MAP

AI_SENTIMENT_COLS = ("AIThreat", "AISelect", "AISent", "AIAcc")
NOT_ANSWERED = "Not answered"


class SurveyTransformer(BaseTransformer):
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["country_canonical"] = df["Country"].map(COUNTRY_MAP)
        df["industry_sector"] = df["Industry"].map(INDUSTRY_MAP)
        df["role_category"] = df["DevType"].map(ROLE_MAP)

        df["converted_comp_yearly_winsorized"] = self._winsorize(df["ConvertedCompYearly"])

        for col in AI_SENTIMENT_COLS:
            df[col] = df[col].fillna(NOT_ANSWERED)

        return df

    @staticmethod
    def _winsorize(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
        observed = series.dropna()
        lo, hi = observed.quantile([lower, upper])
        return series.clip(lower=lo, upper=hi)