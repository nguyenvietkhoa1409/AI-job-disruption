"""Abstract base class for all dataset sources."""

from abc import ABC, abstractmethod

import pandas as pd


class BaseDataSource(ABC):
    @abstractmethod
    def load(self) -> pd.DataFrame:
        """Load the raw dataset into a DataFrame with no transformation applied."""

    @abstractmethod
    def describe_columns(self) -> dict:
        """Return a mapping of column name to expected dtype/description."""
