"""Tests for SurveyFeatureEngineer's content-based topic labelling.

Fitting NMF on the real survey is too slow and data-dependent for CI, so
these tests exercise match_topic_labels() directly with top-term lists shaped
like real fits (see reports/eda/text_mining_exploration.md section 2.1).
"""

import pandas as pd
import pytest

from src.feature_engineering.survey_feature_engineer import (
    MODEL_VERSION,
    TOPIC_ANCHORS,
    SurveyFeatureEngineer,
    match_topic_labels,
)

# Top terms of the documented fit, in its component order (0..9).
DOCUMENTED_FIT = [
    ["ai", "tools", "ai tools", "developers", "don", "think", "use", "need", "capable", "work"],
    ["problem", "problem solving", "solving", "solving skills", "complex problem", "creativity"],
    ["thinking", "critical", "critical thinking", "thinking problem", "analytical", "box"],
    ["architecture", "design", "software", "software architecture", "software design", "systems"],
    ["valuable", "remain", "remain valuable", "skills remain", "skills", "think"],
    ["skills", "soft", "soft skills", "communication", "communication skills", "people"],
    ["understanding", "business", "requirements", "understanding business", "needs", "domain"],
    ["code", "writing", "understanding code", "debugging", "understand", "writing code"],
    ["problems", "ability", "complex", "solutions", "understand", "complex problems"],
    ["level", "high", "high level", "low", "low level", "level design"],
]


def test_documented_fit_maps_to_the_documented_labels():
    labels = match_topic_labels(DOCUMENTED_FIT)
    assert labels == dict(enumerate(TOPIC_ANCHORS))


def test_reordered_topics_keep_their_true_labels():
    # A refit that only reorders components: index-based labels would be
    # wrong for every moved topic; content-based labels must follow the topic.
    order = [7, 1, 2, 0, 3, 5, 6, 4, 8, 9]
    reordered = [DOCUMENTED_FIT[i] for i in order]
    labels = match_topic_labels(reordered)
    assert labels[0] == "Code reading & writing"
    assert labels[3] == "AI capability skepticism"
    assert labels[7] == "Skills will remain valuable (generic)"


def test_merged_topic_stops_the_pipeline():
    # Observed on real refits: "remain valuable" merges into soft skills and a
    # new "ability to understand code" topic appears. Labels no longer fit.
    drifted = list(DOCUMENTED_FIT)
    drifted[4] = ["ability", "understand", "ability understand", "understand code", "read"]
    drifted[5] = ["skills", "soft", "soft skills", "valuable", "remain", "remain valuable"]
    with pytest.raises(ValueError, match="no longer match TOPIC_ANCHORS"):
        match_topic_labels(drifted)


def test_anchor_sets_are_distinct():
    anchors = list(TOPIC_ANCHORS.values())
    assert len(set(anchors)) == len(anchors)


def test_short_answers_get_no_topic_and_no_artifact():
    df = pd.DataFrame({"ai_open_clean": ["ai", None, "only four words here"]})
    engineer = SurveyFeatureEngineer()
    out = engineer.engineer(df)
    assert out["ai_open_topic_id"].isna().all()
    assert out["ai_open_topic_label"].isna().all()
    assert engineer.artifacts()["topics"].empty


def test_model_version_is_set():
    assert MODEL_VERSION
