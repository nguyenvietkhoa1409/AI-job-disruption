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

experience_level_canonical is bucketed from WorkExp (professional
experience) via EXPERIENCE_BUCKET_BINS, using the same Entry/Mid/Senior/Lead
boundaries as AI Jobs' EXPERIENCE_MAP - not YearsCode, which includes
hobbyist coding and would overstate a respondent's professional bucket. See
fact_survey_response's docstring in star_schema.py.
"""

import pandas as pd

from src.preprocessing.base_transformer import BaseTransformer
from src.schema.dimension_maps import (
    COUNTRY_MAP,
    EXPERIENCE_BUCKET_BINS,
    EXPERIENCE_LEVELS,
    INDUSTRY_MAP,
    ROLE_MAP,
)

AI_SENTIMENT_COLS = ("AIThreat", "AISelect", "AISent", "AIAcc")
NOT_ANSWERED = "Not answered"

# AIOpen spam/troll filter: a genuine one-word answer ("debugging") also has
# repeated-token ratio 1.0, so ratio alone is not a signal - it only becomes
# spam once the answer is also long. Tuned against the real file, where the
# only true troll response is a 175K-char answer repeating "no" thousands of
# times - see reports/eda/text_mining_exploration.md section 1.2.
AIOPEN_SPAM_MIN_WORDS = 15
AIOPEN_SPAM_RATIO = 0.8


class SurveyTransformer(BaseTransformer):
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["country_canonical"] = df["Country"].map(COUNTRY_MAP)
        df["industry_sector"] = df["Industry"].map(INDUSTRY_MAP)
        df["role_category"] = df["DevType"].map(ROLE_MAP)
        df["experience_level_canonical"] = pd.cut(
            df["WorkExp"], bins=EXPERIENCE_BUCKET_BINS, labels=EXPERIENCE_LEVELS
        ).astype(object)

        df["converted_comp_yearly_winsorized"] = self._winsorize(df["ConvertedCompYearly"])

        for col in AI_SENTIMENT_COLS:
            df[col] = df[col].fillna(NOT_ANSWERED)

        df["ai_open_clean"] = df["AIOpen"].mask(df["AIOpen"].apply(self._is_aiopen_spam))

        return df

    @staticmethod
    def _winsorize(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
        observed = series.dropna()
        lo, hi = observed.quantile([lower, upper])
        return series.clip(lower=lo, upper=hi)

    @staticmethod
    def _is_aiopen_spam(text) -> bool:
        if pd.isna(text):
            return False
        tokens = str(text).lower().split()
        if len(tokens) <= AIOPEN_SPAM_MIN_WORDS:
            return False
        most_common_count = pd.Series(tokens).value_counts().iloc[0]
        return (most_common_count / len(tokens)) > AIOPEN_SPAM_RATIO