"""Abstract base class for per-dataset data quality rule sets."""

from abc import ABC, abstractmethod

import pandas as pd


class BaseQualityRuleSet(ABC):
    @abstractmethod
    def apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Split df into (clean, quarantine) according to the dataset's quality rules."""

    @staticmethod
    def _split(df: pd.DataFrame, rule_masks: dict[str, pd.Series]) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Combine named boolean masks (True = row fails that rule) into one
        clean/quarantine split. Quarantined rows get a quarantine_reason
        column listing every rule they failed, for the future DQ report."""
        violations = pd.DataFrame(rule_masks, index=df.index).fillna(False)
        is_quarantined = violations.any(axis=1)

        quarantine = df.loc[is_quarantined].copy()
        quarantine["quarantine_reason"] = [
            ", ".join(row.index[row]) for _, row in violations.loc[is_quarantined].iterrows()
        ]
        clean = df.loc[~is_quarantined].copy()
        return clean, quarantine
