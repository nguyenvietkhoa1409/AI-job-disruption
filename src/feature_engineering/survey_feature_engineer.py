"""SurveyFeatureEngineer: derives AIOpen topic features via NMF topic modeling.

Runs after SurveyTransformer, on its ai_open_clean output. Topic count,
label wording, and hyperparameters are locked to the run documented in
reports/eda/text_mining_exploration.md (TF-IDF unigram+bigram, min_df=5,
max_df=0.6, NMF n_components=10, random_state=42). TOPIC_LABELS is a
hand-interpreted mapping from component index -> theme, valid only for that
exact fit - NMF component ordering is not guaranteed stable across refits,
so if the input row count or vocabulary changes meaningfully, re-run and
re-verify TOPIC_LABELS against the printed top terms before trusting them.

Short answers (<= SHORT_MAX_WORDS words) are left without a topic: a topic
model cannot meaningfully place a one-word answer (see text mining report
section 1.2).
"""

import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer

from src.feature_engineering.base_feature_engineer import BaseFeatureEngineer

SHORT_MAX_WORDS = 4
N_TOPICS = 10
RANDOM_STATE = 42

# component index -> theme, hand-interpreted from top terms - see
# reports/eda/text_mining_exploration.md section 2.1
TOPIC_LABELS = {
    0: "AI capability skepticism",
    1: "Problem solving",
    2: "Critical thinking",
    3: "Software architecture / system design",
    4: "Skills will remain valuable (generic)",
    5: "Soft skills / communication",
    6: "Business/domain understanding",
    7: "Code reading & writing",
    8: "Complex-problem-solving ability",
    9: "High-level vs. low-level design",
}


class SurveyFeatureEngineer(BaseFeatureEngineer):
    def engineer(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["ai_open_topic_id"] = None
        df["ai_open_topic_label"] = None

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

        df.loc[sentence_mask, "ai_open_topic_id"] = dominant_topic
        df.loc[sentence_mask, "ai_open_topic_label"] = [TOPIC_LABELS[t] for t in dominant_topic]
        return df
