"""SurveyTransformer: cleaning/transform logic specific to the developer survey dataset."""

import pandas as pd

from src.preprocessing.base_transformer import BaseTransformer


class SurveyTransformer(BaseTransformer):
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError
