"""Abstract base class for per-dataset feature engineering steps."""

from abc import ABC, abstractmethod

import pandas as pd


class BaseFeatureEngineer(ABC):
    @abstractmethod
    def engineer(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return df with derived/engineered features added."""
