"""AIJobsTransformer: cleaning/transform logic specific to the AI jobs dataset."""

import pandas as pd

from src.preprocessing.base_transformer import BaseTransformer


class AIJobsTransformer(BaseTransformer):
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError
