"""DatasetPipeline: chains source -> quality -> preprocessing -> eda for one dataset."""

from dataclasses import dataclass

from src.data_sources.base_source import BaseDataSource
from src.eda.profiler import DatasetProfiler
from src.preprocessing.base_transformer import BaseTransformer
from src.quality.base_rule_set import BaseQualityRuleSet


@dataclass
class DatasetPipeline:
    source: BaseDataSource
    quality_rules: BaseQualityRuleSet
    transformer: BaseTransformer
    profiler: DatasetProfiler

    def run(self):
        raise NotImplementedError
