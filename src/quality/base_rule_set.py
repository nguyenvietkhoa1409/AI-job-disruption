"""Abstract base class for per-dataset data quality rule sets."""

from abc import ABC, abstractmethod

import pandas as pd


class BaseQualityRuleSet(ABC):
    @abstractmethod
    def apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Split df into (clean, quarantine) according to the dataset's quality rules."""
