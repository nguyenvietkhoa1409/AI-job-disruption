"""SurveyFeatureEngineer: derives AIOpen topic features via NMF topic modeling.

Runs after SurveyTransformer, on its ai_open_clean output. Topic count and
hyperparameters are locked to the run documented in
reports/eda/text_mining_exploration.md (TF-IDF unigram+bigram, min_df=5,
max_df=0.6, NMF n_components=10, random_state=42).

Labels are assigned by CONTENT, not by component index. NMF gives no stable
component order: refitting on slightly changed input (5-10% of rows removed)
reordered topics, and in 7 of 10 trials also merged one topic and created a
new one. Index-based labels (TOPIC_LABELS[id]) would then attach the wrong
label to thousands of answers without any error. Instead, each label
declares anchor terms; after fitting, a label is given to the one topic
whose top terms contain all of its anchors. If any label matches zero or
several topics, the topics no longer mean what the labels say, and
engineer() raises ValueError: a person must re-read the printed top terms,
update TOPIC_ANCHORS, and bump MODEL_VERSION.

Short answers (<= SHORT_MAX_WORDS words) are left without a topic: a topic
model cannot meaningfully place a one-word answer (see text mining report
section 1.2).

Outputs: ai_open_topic_id / ai_open_topic_label on each row, plus
artifacts()["topics"], one row per topic (model_version, component_id,
topic_label, top_terms) for the warehouse's dim_ai_open_topic.
"""

import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

from src.feature_engineering.base_feature_engineer import BaseFeatureEngineer

SHORT_MAX_WORDS = 4
N_TOPICS = 10
RANDOM_STATE = 42
TOP_N_TERMS = 10

# Bump whenever TOPIC_ANCHORS or the hyperparameters above change: topics
# from different versions must not be compared as if they were the same.
MODEL_VERSION = "nmf-2025-v1"

# label -> terms that must ALL appear among the topic's TOP_N_TERMS top terms.
# Chosen from the documented fit's top terms (text mining report section 2.1):
# each set is present in exactly one of the 10 topics.
TOPIC_ANCHORS: dict[str, frozenset[str]] = {
    "AI capability skepticism": frozenset({"ai tools"}),
    "Problem solving": frozenset({"problem solving"}),
    "Critical thinking": frozenset({"critical thinking"}),
    "Software architecture / system design": frozenset({"software architecture"}),
    "Skills will remain valuable (generic)": frozenset({"remain valuable"}),
    "Soft skills / communication": frozenset({"soft skills"}),
    "Business/domain understanding": frozenset({"understanding business"}),
    "Code reading & writing": frozenset({"code", "writing"}),
    "Complex-problem-solving ability": frozenset({"complex problems"}),
    "High-level vs. low-level design": frozenset({"high level", "low level"}),
}


def match_topic_labels(top_terms: list[list[str]]) -> dict[int, str]:
    """Map component index -> label by anchor terms; raise if not one-to-one.

    top_terms[i] is component i's top terms, most important first.
    """
    component_to_label: dict[int, str] = {}
    problems = []
    for label, anchors in TOPIC_ANCHORS.items():
        hits = [i for i, terms in enumerate(top_terms) if anchors <= set(terms)]
        if len(hits) != 1:
            problems.append(f"'{label}' (anchors {sorted(anchors)}) matched {len(hits)} topics")
            continue
        if hits[0] in component_to_label:
            problems.append(f"'{label}' and '{component_to_label[hits[0]]}' both matched topic {hits[0]}")
            continue
        component_to_label[hits[0]] = label

    if problems or len(component_to_label) != len(top_terms):
        listing = "\n".join(f"  topic {i}: {', '.join(t)}" for i, t in enumerate(top_terms))
        raise ValueError(
            "SurveyFeatureEngineer: fitted topics no longer match TOPIC_ANCHORS "
            f"({MODEL_VERSION}):\n  " + "\n  ".join(problems)
            + f"\nTop terms of this fit:\n{listing}\n"
            "Re-read the topics, update TOPIC_ANCHORS and bump MODEL_VERSION."
        )
    return component_to_label


class SurveyFeatureEngineer(BaseFeatureEngineer):
    def __init__(self) -> None:
        self._topics = pd.DataFrame(columns=["model_version", "component_id", "topic_label", "top_terms"])

    def engineer(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["ai_open_topic_id"] = pd.Series(pd.NA, index=df.index, dtype="Int64")
        df["ai_open_topic_label"] = pd.Series(pd.NA, index=df.index, dtype="object")

        word_count = df["ai_open_clean"].str.split().str.len()
        sentence_mask = df["ai_open_clean"].notna() & (word_count > SHORT_MAX_WORDS)
        sentence_answers = df.loc[sentence_mask, "ai_open_clean"]
        if sentence_answers.empty:
            return df

        tfidf = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", min_df=5, max_df=0.6)
        term_matrix = tfidf.fit_transform(sentence_answers)

        nmf = NMF(n_components=N_TOPICS, random_state=RANDOM_STATE, init="nndsvda", max_iter=500)
        topic_weights = nmf.fit_transform(term_matrix)
        dominant_topic = topic_weights.argmax(axis=1)

        vocabulary = tfidf.get_feature_names_out()
        top_terms = [
            [vocabulary[i] for i in component.argsort()[::-1][:TOP_N_TERMS]] for component in nmf.components_
        ]
        labels = match_topic_labels(top_terms)  # raises if the fit drifted

        df.loc[sentence_mask, "ai_open_topic_id"] = dominant_topic
        df.loc[sentence_mask, "ai_open_topic_label"] = [labels[t] for t in dominant_topic]

        self._topics = pd.DataFrame(
            {
                "model_version": MODEL_VERSION,
                "component_id": list(range(N_TOPICS)),
                "topic_label": [labels[i] for i in range(N_TOPICS)],
                "top_terms": [", ".join(terms) for terms in top_terms],
            }
        )
        return df

    def artifacts(self) -> dict[str, pd.DataFrame]:
        return {"topics": self._topics}
