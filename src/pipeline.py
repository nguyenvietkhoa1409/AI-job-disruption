"""DatasetPipeline: chains source -> quality -> preprocessing -> feature engineering -> eda for one dataset."""

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.config import PROJECT_PATHS
from src.data_sources.base_source import BaseDataSource
from src.eda.profiler import DatasetProfiler
from src.feature_engineering.base_feature_engineer import BaseFeatureEngineer
from src.preprocessing.base_transformer import BaseTransformer
from src.quality.base_rule_set import BaseQualityRuleSet
from src.quality.quarantine_writer import QuarantineWriter


@dataclass
class PipelineResult:
    """Everything a caller gets back from one DatasetPipeline.run() call, so
    it doesn't need to re-read the CSVs run() just wrote to inspect them."""

    name: str
    processed: pd.DataFrame
    quarantine: pd.DataFrame
    quarantine_summary: dict[str, int]
    data_dictionary: pd.DataFrame
    processed_path: Path
    quarantine_path: Path
    artifact_paths: dict[str, Path] = field(default_factory=dict)

    @property
    def clean_rows(self) -> int:
        return len(self.processed)

    @property
    def quarantine_rows(self) -> int:
        return len(self.quarantine)


@dataclass
class DatasetPipeline:
    name: str
    source: BaseDataSource
    quality_rules: BaseQualityRuleSet
    transformer: BaseTransformer
    profiler: DatasetProfiler
    # Optional: only datasets with a model-based step need one (today: survey).
    # Deterministic features (lookups, buckets) live in the transformer.
    feature_engineer: BaseFeatureEngineer | None = None

    def run(self) -> PipelineResult:
        """source.load() -> quality_rules.apply() -> QuarantineWriter.write()
        -> transformer.transform() -> feature_engineer.engineer() (if set)
        -> write data/processed/<name>.csv (+ <name>_<artifact>.csv for each
        feature-engineer side table) -> profiler.profile(). All outputs are
        overwritten (not appended) each run, matching QuarantineWriter's own
        contract."""
        raw = self.source.load()
        clean, quarantine = self.quality_rules.apply(raw)

        quarantine_path = QuarantineWriter().write(self.name, quarantine)

        processed = self.transformer.transform(clean)
        if self.feature_engineer is not None:
            processed = self.feature_engineer.engineer(processed)

        PROJECT_PATHS.data_processed.mkdir(parents=True, exist_ok=True)
        processed_path = PROJECT_PATHS.data_processed / f"{self.name}.csv"
        processed.to_csv(processed_path, index=False)

        artifact_paths = {}
        if self.feature_engineer is not None:
            for key, table in self.feature_engineer.artifacts().items():
                artifact_paths[key] = PROJECT_PATHS.data_processed / f"{self.name}_{key}.csv"
                table.to_csv(artifact_paths[key], index=False)

        data_dictionary = self.profiler.profile(processed)

        return PipelineResult(
            name=self.name,
            processed=processed,
            quarantine=quarantine,
            quarantine_summary=QuarantineWriter.summarize(quarantine),
            data_dictionary=data_dictionary,
            processed_path=processed_path,
            quarantine_path=quarantine_path,
            artifact_paths=artifact_paths,
        )