"""Tests for the controlled vocabulary maps in src/schema/dimension_maps.py.

These check internal consistency of the maps themselves (not against the
real data files, which are gitignored and not present in CI). Coverage
against the real files is verified manually; see reports/data_dictionary/
dimension_maps.md.
"""

from src.schema.dimension_maps import (
    COUNTRY_MAP,
    INDUSTRY_MAP,
    INDUSTRY_SECTORS,
    ROLE_CATEGORIES,
    ROLE_MAP,
)


def test_country_map_has_no_unresolved_values():
    assert all(v for v in COUNTRY_MAP.values())


def test_country_map_normalizes_known_variants_to_one_value():
    assert COUNTRY_MAP["USA"] == COUNTRY_MAP["United States"] == COUNTRY_MAP["United States of America"]
    assert COUNTRY_MAP["UK"] == COUNTRY_MAP["United Kingdom"]
    assert COUNTRY_MAP["Russia"] == COUNTRY_MAP["Russian Federation"]


def test_country_map_distinguishes_the_two_congos_and_koreas():
    assert COUNTRY_MAP["Congo, Republic of the..."] != COUNTRY_MAP["Democratic Republic of the Congo"]
    assert COUNTRY_MAP["Republic of Korea"] != COUNTRY_MAP["Democratic People's Republic of Korea"]


def test_country_map_treats_non_country_values_as_one_bucket():
    assert COUNTRY_MAP["Global"] == COUNTRY_MAP["Nomadic"] == "Multi-region / Remote"


def test_industry_map_values_are_all_declared_sectors():
    assert set(INDUSTRY_MAP.values()) == set(INDUSTRY_SECTORS)


def test_industry_map_merges_known_synonyms():
    assert INDUSTRY_MAP["Fintech"] == INDUSTRY_MAP["Banking/Financial Services"] == INDUSTRY_MAP["Finance"]
    assert INDUSTRY_MAP["Software Development"] == INDUSTRY_MAP["Technology"] == INDUSTRY_MAP["AI"]


def test_role_map_values_are_only_the_two_categories():
    assert set(ROLE_MAP.values()) <= set(ROLE_CATEGORIES)


def test_role_map_ai_jobs_titles_are_all_emerging():
    ai_jobs_titles = [
        "Computer Vision Engineer", "Data Scientist", "Deep Learning Engineer",
        "MLOps Engineer", "NLP Engineer", "RAG Engineer", "Senior Data Scientist",
    ]
    assert all(ROLE_MAP[title] == "Emerging" for title in ai_jobs_titles)


def test_role_map_survey_ai_devtypes_are_emerging_rest_traditional():
    assert ROLE_MAP["AI/ML engineer"] == "Emerging"
    assert ROLE_MAP["Developer, AI apps or physical AI"] == "Emerging"
    assert ROLE_MAP["Applied scientist"] == "Traditional"
    assert ROLE_MAP["Developer, back-end"] == "Traditional"
