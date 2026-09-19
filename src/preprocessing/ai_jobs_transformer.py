"""AIJobsTransformer: cleaning/transform logic specific to the AI jobs dataset.

Runs on the CLEAN half of AIJobsQualityRules.apply() output. Produces the
canonical columns the schema needs; job_category and is_llm_role are left
untouched (already clean, no map needed) - see pipeline_design_spec.md
section 4.3, they carry forward as dim_role attributes rather than being
collapsed into role_category.
"""

import pandas as pd

from src.preprocessing.base_transformer import BaseTransformer
from src.schema.dimension_maps import COUNTRY_MAP, EXPERIENCE_MAP, INDUSTRY_MAP, ROLE_MAP, SKILL_MAP


class AIJobsTransformer(BaseTransformer):
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["country_canonical"] = df["country"].map(COUNTRY_MAP)
        df["industry_sector"] = df["industry"].map(INDUSTRY_MAP)
        df["role_category"] = df["job_title"].map(ROLE_MAP)
        df["experience_level_canonical"] = df["experience_level"].map(EXPERIENCE_MAP)
        df["required_skills_normalized"] = df["required_skills"].apply(self._normalize_skills)
        # job_category, is_llm_role: kept as-is, no transform needed
        return df

    @staticmethod
    def _normalize_skills(tags: str) -> str:
        normalized = {SKILL_MAP.get(t.strip(), t.strip()) for t in tags.split("|")}
        return "|".join(sorted(normalized))