"""QuarantineWriter: persists the quarantine half of a BaseQualityRuleSet.apply() split."""

from pathlib import Path

import pandas as pd

from src.config import PROJECT_PATHS


class QuarantineWriter:
    """Writes a dataset's quarantined rows to data/quarantine/<dataset_name>.csv."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or PROJECT_PATHS.data_quarantine

    def write(self, dataset_name: str, quarantine_df: pd.DataFrame) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"{dataset_name}.csv"
        quarantine_df.to_csv(path, index=False)
        return path

    @staticmethod
    def summarize(quarantine_df: pd.DataFrame) -> dict[str, int]:
        """Count violations per rule name (a row failing 2 rules counts under both)."""
        counts: dict[str, int] = {}
        for reasons in quarantine_df.get("quarantine_reason", []):
            for rule in reasons.split(", "):
                counts[rule] = counts.get(rule, 0) + 1
        return counts
