"""Abstract base class for per-dataset preprocessing transformers."""

from abc import ABC, abstractmethod

import pandas as pd


class BaseTransformer(ABC):
    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a cleaned/transformed copy of df."""
