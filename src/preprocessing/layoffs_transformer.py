"""LayoffsTransformer: cleaning/transform logic specific to the layoffs dataset."""

import pandas as pd

from src.preprocessing.base_transformer import BaseTransformer


class LayoffsTransformer(BaseTransformer):
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError
