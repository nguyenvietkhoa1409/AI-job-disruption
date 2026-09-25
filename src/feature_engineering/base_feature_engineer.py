"""Abstract base class for per-dataset feature engineering steps."""

from abc import ABC, abstractmethod

import pandas as pd


class BaseFeatureEngineer(ABC):
    @abstractmethod
    def engineer(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a copy of df with the engineered feature columns added."""

    def artifacts(self) -> dict[str, pd.DataFrame]:
        """Side tables produced by the last engineer() call, keyed by name.

        DatasetPipeline writes each one to data/processed/<dataset>_<name>.csv
        next to the main processed file, so the loader can fill the matching
        warehouse dimension. Default: none.
        """
        return {}
