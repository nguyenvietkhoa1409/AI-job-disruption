"""Abstract base class for all dataset sources."""

from abc import ABC, abstractmethod

import pandas as pd


class BaseDataSource(ABC):
    """Common contract every dataset source (layoffs, AI jobs, survey) must implement."""

    @abstractmethod
    def load(self) -> pd.DataFrame:
        """Load the raw dataset into a DataFrame with no transformation applied."""

    @abstractmethod
    def describe_columns(self) -> dict[str, str]:
        """Return a mapping of column name to its expected dtype/description."""

    def validate(self, df: pd.DataFrame) -> None:
        """Raise ValueError if df is missing any column declared by describe_columns()."""
        missing = set(self.describe_columns()) - set(df.columns)
        if missing:
            raise ValueError(
                f"{type(self).__name__}: missing expected columns: {sorted(missing)}"
            )
