"""LayoffsTransformer: cleaning/transform logic specific to the layoffs dataset.

Runs on the CLEAN half of LayoffsQualityRules.apply() output. Rules only
validate membership (country_not_in_dimension_map etc.) - this is where the
actual raw -> canonical mapping happens, and where the remaining light
cleanup (fillna on low-stakes descriptive columns) lives.
"""

import pandas as pd

from src.preprocessing.base_transformer import BaseTransformer
from src.schema.dimension_maps import COUNTRY_MAP, INDUSTRY_MAP

FILL_UNKNOWN_COLS = ("location", "industry", "stage")


class LayoffsTransformer(BaseTransformer):
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["country_canonical"] = df["country"].map(COUNTRY_MAP)
        df["industry_sector"] = df["industry"].map(INDUSTRY_MAP)

        # low-stakes descriptive columns (<0.2% missing) - explicit label
        # keeps the row usable for analyses that don't group by this field
        for col in FILL_UNKNOWN_COLS:
            df[col] = df[col].fillna("Unknown")

        return df